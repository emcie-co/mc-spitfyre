#!python

import git
import os
from pathlib import Path
import sys


from data import BranchName, Config
from states import RepoState


CONFIG_TOML_PATH = "ziggurat.toml"


DEFAULT_CONFIG_TOML = """\
git_path = "git" # Overwrite with full path or remove if just `git` is accessible.
root_path = "." # 

[orgs.emcie-co.include]
parlant = "develop"
parlant-client-python = "main"
parlant-client-typescript = "main"

[orgs.emcie-co.paths]
parlant-client-python = "parlant-sdks/parlant-client-python"
parlant-client-typescript = "parlant-sdks/parlant-client-typescript"

[orgs.parlant-io.include]
website = "main"
"""


class Ziggurat:
    def __init__(self, config: Config) -> None:
        self.config = config

    def initial_states(self) -> list[RepoState]:
        result: list[RepoState] = []
        for org_name, org_data in self.config.orgs.items():
            for repo_name, branch in org_data.include.items():
                local_path = org_data.paths.get(repo_name, repo_name)
                result.append(
                    RepoState(
                        repo_name,
                        org_name,
                        branch,
                        Path(self.config.root_path) / local_path,
                    ),
                )

            for repo_name in org_data.paths:
                if repo_name not in org_data.include:
                    raise Exception(
                        f"`{org_name}/{repo_name}` found in `paths` but no branch entry found in `include`"
                    )

        return result

    def run_state(self, state: RepoState) -> bool:
        flag_need_clone = False
        if not os.path.isdir(state.path / ".git"):
            print(f"  `{state.full_name}` does not exist at `{state.path}`, needs clone.")
            flag_need_clone = True

        try:
            if flag_need_clone:
                print(f"  cloning repo `{state.url_https}` into `{state.path}` ... ", end="")
                state_repo = git.Repo.clone_from(state.url_https, state.path)
                print("Success!")
            else:
                state_repo = git.Repo(state.path)
                print(f"  repo `{state.full_name}` detected, fetching ... ", end="")
                _fetch_infos = state_repo.remote().fetch()
                # for fetch_info in _fetch_infos:
                # print("  + Updated %s to %s" % (fetch_info.ref, fetch_info.commit))
                print("Success!")

        except Exception as ex:
            print(f"  Failed: {ex}")
            return False

        if state_repo.active_branch.name != state.branch:
            branch = state.branch
            origin_branch = BranchName(f"origin/{branch}")

            if origin_branch not in state_repo.refs:
                print(f"  Desired branch {branch} does not found in the origin.")
                return False
            origin_commit = state_repo.refs[f"origin/{branch}"].commit

            if branch not in state_repo.refs:
                state_repo.create_head(branch, state_repo.refs[origin_branch].commit)
                print(f"  Created local branch '{branch}' from origin.")
            else:
                branch_commit = state_repo.refs[branch].commit
                # Check if a fast-forward is possible
                if state_repo.git.merge_base(branch, origin_branch) == str(branch_commit):
                    # Perform the fast-forward by updating the reference
                    state_repo.refs[branch].set_commit(origin_commit)
                    print(f"  Fast-forwarded '{branch}' to 'origin/{branch}'.")
                else:
                    print(
                        f"  Fast-forward not possible. {branch} has diverged from 'origin/{branch}'."
                    )
        else:
            if state_repo.is_dirty(untracked_files=True):
                print(
                    "  !! You are on the target branch with uncommitted changes, please proceed manually !! "
                )
                return True

            branch = state.branch
            origin_branch = BranchName(f"origin/{branch}")

            branch_commit = state_repo.refs[branch].commit
            origin_commit = state_repo.refs[f"origin/{branch}"].commit

            # Check if a fast-forward is possible
            if state_repo.git.merge_base(branch, origin_branch) == str(branch_commit):
                # Perform the fast-forward by updating the reference
                state_repo.refs[branch].set_commit(origin_commit)
                print(f"  Fast-forwarded your '{branch}' to 'origin/{branch}'.")
            else:
                print(f"  Fast-forward not possible. {branch} has diverged from 'origin/{branch}'.")

        return True


if __name__ == "__main__":
    config: Config | None = None
    try:
        print(f"[1] Reading config `./{CONFIG_TOML_PATH }` ... ", end="")
        config = Config.from_toml(CONFIG_TOML_PATH)  # type: ignore #TODO(pylance)
        git.refresh(config.git_path)

    except FileNotFoundError:
        print("config file not found, ", end="")
        if "generate" in sys.argv:
            print("generating default ...", end="")
            with open(CONFIG_TOML_PATH, "w") as conf:
                conf.write(DEFAULT_CONFIG_TOML)
            config = Config.from_toml(CONFIG_TOML_PATH)  # type: ignore #TODO(pylance)
            print(
                "a default `ziggurat.toml` config was generated. Please review it before rerunning the tool."
            )
            exit(1)

        else:
            print("Run `zgrt generate` to generate a default `ziggurat.toml` config.")
            exit(1)

    assert config is not None
    zgy = Ziggurat(config)
    print("Success!")  # Z created.

    print("[2] Verifying config ...", end="")  # check no unexpected paths
    repo_states = zgy.initial_states()
    print("Success!")

    flag_any_failed = False
    for state in repo_states:
        print(f"Running on: `{state.full_name}` with path: `{state.path}` ... ")
        if not zgy.run_state(state):
            print("Failed (check log above).")
            flag_any_failed = True
            continue

        print(f"! Repo `{state.full_name}` ready at `{state.path}`.\n")

    if flag_any_failed:
        print("Some repos failed, see logs")
        exit(1)

    print("All repos ready!")

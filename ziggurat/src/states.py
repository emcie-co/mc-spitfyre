from pathlib import Path

from data import BranchName, OrgName, RepoName


class RepoState:
    def __init__(
        self,
        repo: RepoName,
        org: OrgName,
        branch: BranchName,
        path: Path,
    ) -> None:
        self.repo = repo
        self.org = org
        self.branch = branch
        self.path = path

    @property
    def full_name(self) -> str:
        return f"{self.org}/{self.repo}"

    @property
    def url_https(self) -> str:
        return f"https://github.com/{self.full_name}.git"

    def __str__(self) -> str:
        return f"{self.full_name}#{self.branch} @ `./{self.path}`"

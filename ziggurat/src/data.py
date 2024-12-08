from pathlib import Path
from typing import NewType, Self

from pydantic import BaseModel, Field

RepoName = NewType("RepoName", str)
OrgName = NewType("OrgName", str)
BranchName = NewType("BranchName", str)


class ConfigOrg(BaseModel):
    include: dict[RepoName, BranchName] = Field(default_factory=dict)
    paths: dict[RepoName, Path] = Field(default_factory=dict)


class Config(BaseModel):
    git_path: str = Field(default_factory=lambda: "git")
    root_path: str = Field(default_factory=lambda: ".")

    orgs: dict[OrgName, ConfigOrg] = Field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: str) -> Self:
        import toml

        data = toml.load(path)
        return cls(**data)

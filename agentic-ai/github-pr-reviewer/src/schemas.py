from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class PRRequest(BaseModel):
    owner: str | None = Field(
        default=None,
        description="GitHub repository owner"
    )

    repo: str | None = Field(
        default=None,
        description="GitHub repository name"
    )

    pr_number: int | None = Field(
        default=None,
        gt=0,
        description="Pull request number, if supplied"
    )

    review_instructions: list[str] = Field(
        default_factory=list,
        description="Additional code review instructions"
    )

class SelectedPR(BaseModel):
    """Validated details of the GitHub pull request selected for review."""

    model_config = ConfigDict(frozen=True)

    owner: str = Field(description="GitHub username or organization that owns the repository.")

    repo: str = Field(description="Name of the GitHub repository containing the PR.")

    pr_number: int = Field(gt=0,description="Positive integer identifying the pull request.")

    review_instructions: list[str] = Field(default_factory=list, description="Additional user-provided instructions for reviewing the PR.")

    pr: dict[str, Any] = Field(description="GitHub API response containing PR metadata, including its number, title, description, and head commit SHA.")
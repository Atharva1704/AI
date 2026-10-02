from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field

from github_client import GitHubClient

github = GitHubClient()

class ListPRInput(BaseModel):
    owner: str = Field(
        description="GitHub repository owner or username"
    )

    repo: str = Field(
        description="GitHub repository name"
    )

    state: Literal["open", "closed", "all"] = Field(
        default="open",
        description="Pull request state"
    )

    head: str | None = Field(
        default=None,
        description=(
            "Source branch to filter PRs. "
            "Example: feature/user-profile-route. "
            "For forked PRs, use owner:branch."
        )
    )

    base: str | None = Field(
        default=None,
        description=(
            "Target branch to filter PRs. Example: main"
        )
    )


class PRInput(BaseModel):
    owner: str = Field(
        description="GitHub repository owner"
    )

    repo: str = Field(
        description="GitHub repository name"
    )

    pr_number: int = Field(
        gt=0,
        description="GitHub pull request number"
    )

# @tool(
#     "list_pull_requests",
#     args_schema=ListPRInput
# )
# def list_prs_tool(
#     owner: str,
#     repo: str,
#     state: str = "open",
#     head: str | None = None,
#     base: str | None = None
# ) -> list[dict]:
#     """
#     Find pull requests in a GitHub repository.

#     Use when the user provides repository or branch
#     information but does not specify a PR number.

#     Returns matching PRs with their numbers,
#     titles, branches, authors and URLs.
#     """

#     return github.list_pull_requests(
#         owner=owner,
#         repo=repo,
#         state=state,
#         head=head,
#         base=base
#     )


@tool(
    "get_pull_request",
    args_schema=PRInput
)
def get_pr_tool(
    owner: str,
    repo: str,
    pr_number: int
) -> dict:
    """
    Retrieve information about a specific GitHub PR.

    Use when the PR number is known.

    Returns PR metadata, source and target branches,
    commit SHAs and change statistics.
    """

    return github.get_pull_request(
        owner=owner,
        repo=repo,
        pr_number=pr_number
    )


@tool(
    "get_pr_changed_files",
    args_schema=PRInput
)
def get_changed_files_tool(
    owner: str,
    repo: str,
    pr_number: int
) -> list[dict]:
    """
    Retrieve changed files and their code patches.

    Use this as the primary source of code changes
    when reviewing a GitHub pull request.

    Returns filenames, change statuses, additions,
    deletions and available patches.
    """

    return github.get_pr_changed_files(
        owner=owner,
        repo=repo,
        pr_number=pr_number
    )

@tool(
    "get_pr_diff",
    args_schema=PRInput
)
def get_diff_tool(
    owner: str,
    repo: str,
    pr_number: int
) -> str:
    """
    Retrieve the complete unified diff of a GitHub PR.

    Use when additional unified diff context is
    required beyond individual changed-file patches.

    Returns the complete available diff as text.
    """

    return github.get_pr_diff(
        owner=owner,
        repo=repo,
        pr_number=pr_number
    )


@tool(
    "post_pr_review",
)
def post_pr_review_tool(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    commit_id: str
) -> dict:
    """
    Publish a review to a GitHub pull request.

    Invoke only after explicit user confirmation.
    """
    return github.post_pr_review(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        body=body,
        commit_id=commit_id
    )

github_tools = [
    # list_prs_tool,
    get_pr_tool,
    get_changed_files_tool,
    get_diff_tool,
    post_pr_review_tool
]

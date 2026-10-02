from typing import Any

from config import PROJECT_ROOT, DEFAULT_OWNER, DEFAULT_REPO, MAX_CHARS
from schemas import PRRequest


def load_code_standards() -> str:
    """
        Include a limited excerpt to avoid bloating every LLM request.
        Currently the code standards has roughly 86 tokens
    """
    path = PROJECT_ROOT / "CODE_STANDARDS.md"
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8")
    if len(content) == 0:
        raise ValueError(
            f"CODE_STANDARDS.md is empty! Please check the file "
            f"Actual: {len(content)} characters."
        )
    # print("Code standard: ", content)
    print("Coding Standards are loaded")
    return content

# Here we are just checking if PR number is correctly found and if owner and repo are correctly taken from env
def validate_request(request: PRRequest) -> dict[str, Any]:
    """
        PR number is required
        For now I am adding the Owner and Repo on my own as the GITHUB Token is self generated
        Future Scope: Add authentication mechanism to allow access to github repos so this can be publically usable
    """
    owner = DEFAULT_OWNER #(request.owner or DEFAULT_OWNER).strip()
    repo = DEFAULT_REPO #(request.repo or DEFAULT_REPO).strip()
    print(f"owner:{owner}")
    missing = []

    if not owner:
        missing.append("repository owner")
    if not repo:
        missing.append("repository name")

    pr_number = request.pr_number

    # Added just to ensure that the model doesnt hallucinate for number
    if pr_number is None or not str(pr_number).isascii() or not str(pr_number).isdigit() or int(pr_number) <= 0:
        missing.append("valid PR number (positive integer)")
    else:
        pr_number = int(pr_number)

    return {
        "valid": not missing,
        "missing": missing,
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
    }

def split_patch(patch: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Small POC splitter: preserve whole lines, not exact diff hunk boundaries.

    Note: a single line can still exceed the limit. Do not use these chunks to
    calculate precise GitHub inline-comment positions.
    """
    print("Spitting the patch: ", patch, max_chars)
    chunks: list[str] = []
    current: list[str] = []
    size = 0

    for line in patch.splitlines(keepends=True):
        if current and size + len(line) > max_chars:
            chunks.append("".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line)

    if current:
        chunks.append("".join(current))
    return chunks



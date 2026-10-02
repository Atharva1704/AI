from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from prompts import CODE_REVIEW_PROMPT, EXTRACTION_PROMPT, SUMMARY_PROMPT
from schemas import PRRequest, SelectedPR
from tools import get_changed_files_tool, get_pr_tool, post_pr_review_tool
from utils import load_code_standards, validate_request, split_patch
from config import EXTRACTION_MODEL, REVIEW_MODEL, DELAY_SECONDS


def build_review_body(review: dict[str, Any]) -> str:
    """Creating a readable, reviewable Markdown summary."""
    pr = review["pr"]
    parts = [
        "# Automated PR Review",
        f"PR #{pr['number']} · reviewed commit `{pr['head_sha']}`",
        "",
    ]
    found_issues = False

    for file_review in review["files"]:
        findings = [
            chunk["review"].strip()
            for chunk in file_review["findings"]
            if chunk["review"].strip().lower().rstrip(".")
            not in {"no issues found", "no actionable issues found"}
        ]
        if not findings:
            continue
        found_issues = True
        parts.append(f"## `{file_review['filename']}`")
        for finding in findings:
            parts.extend([finding, ""])

    if not found_issues:
        parts.extend(["No issues reported in the patches that were reviewed.", ""])

    if review["skipped_files"]:
        parts.extend([
            "## Files not fully reviewed",
            *[f"- `{name}` (GitHub did not provide a patch)"
              for name in review["skipped_files"]],
            "",
        ])

    parts.append(
        "_AI-generated feedback; verify findings. Static diff review only: "
        "no tests were executed and cross-file interactions were not exhaustively checked._"
    )
    return "\n".join(parts).strip() + "\n"


class PRReviewAgent:
    def __init__(self) -> None:
        # Because I dont want to preserve my best model for a better task 
        # and for identification the 20b will do

        extraction_model = ChatGroq(model=EXTRACTION_MODEL, temperature=0)
        # print(f"Input Token Limit for 20b: {extraction_model.profile.get("max_input_tokens")}")
        # print(f"Output Token Limit for 20b: {extraction_model.profile.get("max_output_tokens")}")
        
        self.review_model = ChatGroq(model=REVIEW_MODEL, temperature=0)
        # print(f"Input Token Limit for 120b: {self.review_model.profile.get("max_input_tokens")}")
        # print(f"Output Token Limit for 120b: {self.review_model.profile.get("max_output_tokens")}")

        self.extractor = extraction_model.with_structured_output(PRRequest, method="function_calling")
        
        self.conversation = [SystemMessage(content=EXTRACTION_PROMPT)]
        self._last_review_call_started: float | None = None
        self.code_standards = load_code_standards()

    def identify_pr(self, user_message: str) -> dict[str, Any]:
        """Extract owner/repo/PR number across clarification turns."""
        self.conversation.append(HumanMessage(content=user_message))
        request: PRRequest = self.extractor.invoke(self.conversation)
        validation = validate_request(request)
        print(validation)
        if not validation["valid"]:
            missing = ", ".join(validation["missing"])
            question = f"Please provide the following information: {missing}."
            self.conversation.append(AIMessage(content=question))
            return {
                "status": "clarification_required",
                "question": question,
                "extracted": request.model_dump(),
            }

        owner, repo = validation["owner"], validation["repo"]
        pr_number = validation["pr_number"]
        assert pr_number is not None  # Guaranteed by validate_request.
        pr = get_pr_tool.invoke({
            "owner": owner, "repo": repo, "pr_number": pr_number
        })

        selected = SelectedPR(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            review_instructions=request.review_instructions,
            pr=pr,
        )
        self.conversation.append(AIMessage(
            content=f"Identified PR #{pr['number']} in {owner}/{repo}."
        ))
        return {"status": "success", "selection": selected}

    def _call_review_model(self, system_prompt: str, context: dict) -> str:
        """Enforce a minimum interval between review/summarization calls."""
        if self._last_review_call_started is not None:
            elapsed = time.monotonic() - self._last_review_call_started
            remaining = DELAY_SECONDS - elapsed
            if remaining > 0:
                print(f"Waiting {remaining:.1f}s before the next LLM call...")
                time.sleep(remaining)

        self._last_review_call_started = time.monotonic()
        response = self.review_model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(context, ensure_ascii=False)),
        ])
        return response.content

    def review_pr(self, selected: SelectedPR) -> dict[str, Any]:
        """Fetch changes and review every available patch, chunk by chunk."""
        args = {
            "owner": selected.owner,
            "repo": selected.repo,
            "pr_number": selected.pr_number,
        }
        # Fail instead of silently reviewing a newer, different commit.
        current_pr = get_pr_tool.invoke(args)
        if current_pr["head_sha"] != selected.pr["head_sha"]:
            raise RuntimeError("PR changed after identification; identify it again.")

        changed_files = get_changed_files_tool.invoke(args)
        reviewable_files = [f for f in changed_files if f.get("patch")]
        skipped_files = [f["filename"] for f in changed_files if not f.get("patch")]
        reviewed_files: list[dict[str, Any]] = []

        pr_context = {
            "number": current_pr["number"],
            "title": current_pr["title"],
            "description": (current_pr.get("description") or ""), # Note that the description can get very large
            "head_sha": current_pr["head_sha"],
        }

        for file in reviewable_files:
            filename = file["filename"]
            chunks = split_patch(file["patch"])
            rolling_summary = ""
            file_reviews = []
            print(f"\nFILE: {filename} ({len(chunks)} chunk(s))")

            for index, chunk in enumerate(chunks):
                print(f"Reviewing chunk {index + 1}/{len(chunks)}")
                context = {
                    "pull_request": pr_context,
                    "filename": filename,
                    "chunk_number": index + 1,
                    "total_chunks": len(chunks),
                    "previous_context": rolling_summary,
                    "current_patch": chunk,
                    "review_instructions": selected.review_instructions,
                    "code_standards": self.code_standards,
                }

                finding_text = self._call_review_model(CODE_REVIEW_PROMPT, context)
                
                file_reviews.append({
                    "chunk": index + 1,
                    "review": finding_text,
                })
                print(finding_text)

                if index < len(chunks) - 1:
                    rolling_summary = self._call_review_model(
                        SUMMARY_PROMPT,
                        {
                            "filename": filename,
                            "previous_summary": rolling_summary,
                            "current_patch": chunk,
                        },
                    )

            reviewed_files.append({
                "filename": filename,
                "chunks": len(chunks),
                "findings": file_reviews,
            })

        review = {
            "owner": selected.owner,
            "repo": selected.repo,
            "pr": current_pr,
            "files": reviewed_files,
            "skipped_files": skipped_files,
        }
        review["body"] = build_review_body(review)
        return review

    @staticmethod
    def publish_review(review: dict[str, Any], *, confirmed: bool = False) -> dict:
        """Publish ONLY after the caller has explicitly approved the preview."""
        if not confirmed:
            raise ValueError("Publication requires explicit confirmation.")
        if not review["files"]:
            raise ValueError("No patches were reviewed; nothing to publish.")

        args = {
            "owner": review["owner"],
            "repo": review["repo"],
            "pr_number": review["pr"]["number"],
        }
        latest_pr = get_pr_tool.invoke(args)
        if latest_pr["head_sha"] != review["pr"]["head_sha"]:
            raise RuntimeError(
                "PR has changed since review; regenerate findings before publishing."
            )

        # COMMENT creates a *new* review; rerunning does not replace old ones.
        return post_pr_review_tool.invoke({
            **args,
            "body": review["body"],
            "commit_id": review["pr"]["head_sha"],
        })


def main() -> None:
    agent = PRReviewAgent()
    print("GitHub PR Reviewer — enter a PR request (or 'quit').")

    while True:
        message = input("\nRequest: ").strip()
        
        if message.lower() in {'quit', 'q'}:
            return
        if not message:
            continue

        identification = agent.identify_pr(message)
        if identification["status"] == "clarification_required":
            print(identification["question"])
            continue
        selected = identification["selection"]
        print(f"Identified: {selected.owner}/{selected.repo} PR #{selected.pr_number}")
        break

    review = agent.review_pr(selected)
    print("\n=== REVIEW PREVIEW ===\n")
    print(review["body"])
    if review["skipped_files"]:
        print("WARNING: Some files had no patch and were not reviewed.")

    if not review["files"]:
        print("No patches available. Nothing will be posted.")
        return

    answer = input("Type PUBLISH to post this NEW GitHub review: ").strip()
    if answer != "PUBLISH":
        print("Review not published.")
        return

    result = agent.publish_review(review, confirmed=True)
    print("Published:", result)


if __name__ == "__main__":
    main()

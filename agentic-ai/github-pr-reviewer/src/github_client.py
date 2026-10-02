
import os
import requests
from dotenv import load_dotenv


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token=None):
        load_dotenv()

        self.token = token or os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError("GITHUB_TOKEN is missing")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })

    def _get(self, endpoint, params=None, accept=None):
        headers = {"Accept": accept} if accept else None

        response = self.session.get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        return response

    # def list_pull_requests(
    #     self,
    #     owner,
    #     repo,
    #     state="open",
    #     head=None,
    #     base=None
    # ):
    #     """List PRs, optionally filtering by source/target branch."""

    #     endpoint = f"/repos/{owner}/{repo}/pulls"

    #     params = {
    #         "state": state,
    #         "per_page": 100
    #     }

    #     if head:
    #         # GitHub expects owner:branch for this filter.
    #         params["head"] = head if ":" in head else f"{owner}:{head}"

    #     if base:
    #         params["base"] = base

    #     results = []
    #     url = f"{self.BASE_URL}{endpoint}"

    #     while url:
    #         response = self.session.get(
    #             url,
    #             params=params,
    #             timeout=30
    #         )
    #         response.raise_for_status()

    #         for pr in response.json():
    #             results.append({
    #                 "number": pr["number"],
    #                 "title": pr["title"],
    #                 "state": pr["state"],
    #                 "source_branch": pr["head"]["ref"],
    #                 "target_branch": pr["base"]["ref"],
    #                 "author": pr["user"]["login"],
    #                 "url": pr["html_url"]
    #             })

    #         url = response.links.get("next", {}).get("url")
    #         params = None

    #     return results

    def get_pull_request(self, owner, repo, pr_number):
        """Fetch PR metadata and commit SHAs."""

        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        pr = self._get(endpoint).json()

        return {
            "number": pr["number"],
            "title": pr["title"],
            "description": pr["body"],
            "state": pr["state"],
            "author": pr["user"]["login"],
            "url": pr["html_url"],
            "source_branch": pr["head"]["ref"],
            "target_branch": pr["base"]["ref"],
            "head_sha": pr["head"]["sha"],
            "base_sha": pr["base"]["sha"],
            "head_repo": (
                pr["head"]["repo"]["full_name"]
                if pr["head"]["repo"] else None
            ),
            "changed_files": pr["changed_files"],
            "additions": pr["additions"],
            "deletions": pr["deletions"],
            "commits": pr["commits"]
        }

    def get_pr_changed_files(self, owner, repo, pr_number):
        """Fetch changed files and their available patches."""

        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"

        url = f"{self.BASE_URL}{endpoint}"
        params = {"per_page": 100}
        results = []

        while url:
            response = self.session.get(
                url,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            for file in response.json():
                results.append({
                    "filename": file["filename"],
                    "status": file["status"],
                    "sha": file["sha"],
                    "additions": file["additions"],
                    "deletions": file["deletions"],
                    "changes": file["changes"],
                    "patch": file.get("patch"),
                    "previous_filename": file.get("previous_filename")
                })

            url = response.links.get("next", {}).get("url")
            params = None

        return results

    def get_pr_diff(self, owner, repo, pr_number):
        """Fetch the complete unified PR diff as text."""

        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"

        response = self._get(
            endpoint,
            accept="application/vnd.github.diff"
        )

        return response.text
    
    def post_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        commit_id: str
    ):
        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/pulls/{pr_number}/reviews"
        )

        payload = {
            "body": body,
            "event": "COMMENT",
            "commit_id": commit_id
        }

        response = self.session.post(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        return {
            "review_id": data["id"],
            "url": data["html_url"],
            "state": data["state"]
        }


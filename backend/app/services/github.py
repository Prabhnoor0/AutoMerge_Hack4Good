"""
GitHub Integration Service

Per-request GitHub client that accepts token/owner/repo per call.
Supports: repo validation, file fetching, branch creation, commits, PRs, and merging.
Falls back to mock mode when token is "mock" or when operations fail.
"""

import re
import base64
import hashlib
import random
import structlog
from typing import Any

import httpx

logger = structlog.get_logger("automerge.github")

GITHUB_API = "https://api.github.com"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL or owner/repo string into (owner, repo).

    Accepts:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - github.com/owner/repo
        - owner/repo
    """
    url = url.strip().rstrip("/")

    # Strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Full URL
    match = re.match(r"(?:https?://)?github\.com/([^/]+)/([^/]+)", url)
    if match:
        return match.group(1), match.group(2)

    # owner/repo format
    parts = url.split("/")
    if len(parts) == 2 and all(p for p in parts):
        return parts[0], parts[1]

    raise ValueError(f"Invalid GitHub URL or owner/repo: {url}")


class GitHubClient:
    """Per-request GitHub API client. Does NOT use global config."""

    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.is_mock = token.lower() in ("mock", "demo", "test", "")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _repo_url(self, path: str = "") -> str:
        return f"{GITHUB_API}/repos/{self.owner}/{self.repo}{path}"

    # ─── Validation ───────────────────────────────────────

    async def validate_token(self) -> dict[str, Any]:
        """Validate the GitHub token and check scopes."""
        if self.is_mock:
            return self._mock_validate_token()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{GITHUB_API}/user",
                    headers=self._headers(),
                )
                if resp.status_code == 401:
                    return {"valid": False, "error": "Invalid token — check your personal access token"}
                resp.raise_for_status()
                user = resp.json()
                scopes = resp.headers.get("x-oauth-scopes", "")
                return {
                    "valid": True,
                    "username": user.get("login", ""),
                    "scopes": scopes,
                    "has_repo_scope": "repo" in scopes,
                }
        except httpx.TimeoutException:
            return {"valid": False, "error": "GitHub API timeout — try again"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def validate_repo(self) -> dict[str, Any]:
        """Validate repo exists and token has access."""
        if self.is_mock:
            return self._mock_validate_repo()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._repo_url(), headers=self._headers())
                if resp.status_code == 404:
                    return {"valid": False, "error": f"Repository {self.owner}/{self.repo} not found"}
                if resp.status_code == 403:
                    return {"valid": False, "error": "Access denied — token lacks permissions for this repo"}
                resp.raise_for_status()
                data = resp.json()
                return {
                    "valid": True,
                    "full_name": data.get("full_name", ""),
                    "default_branch": data.get("default_branch", "main"),
                    "private": data.get("private", False),
                    "permissions": data.get("permissions", {}),
                    "description": data.get("description", ""),
                }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ─── File Operations ──────────────────────────────────

    async def get_file_contents(self, file_path: str, ref: str = "main") -> dict[str, Any]:
        """Fetch file contents from the repository."""
        if self.is_mock:
            return self._mock_file_contents(file_path, ref)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self._repo_url(f"/contents/{file_path}"),
                    headers=self._headers(),
                    params={"ref": ref},
                )
                if resp.status_code == 404:
                    return {"success": False, "error": f"File not found: {file_path}"}
                resp.raise_for_status()
                data = resp.json()

                if data.get("type") != "file":
                    return {"success": False, "error": f"{file_path} is a directory, not a file"}

                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                return {
                    "success": True,
                    "content": content,
                    "sha": data.get("sha", ""),
                    "size": data.get("size", 0),
                    "path": data.get("path", file_path),
                    "encoding": data.get("encoding", "base64"),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def find_file_in_repo(self, filename: str, ref: str = "main") -> dict[str, Any]:
        """Search for a file in the repo by name."""
        if self.is_mock:
            return {"success": True, "path": filename, "mock": True}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Use search API
                resp = await client.get(
                    f"{GITHUB_API}/search/code",
                    headers=self._headers(),
                    params={"q": f"filename:{filename} repo:{self.owner}/{self.repo}"},
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        return {"success": True, "path": items[0].get("path", filename)}

                return {"success": False, "error": f"File '{filename}' not found in repo"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Branch Operations ────────────────────────────────

    async def create_branch(self, branch_name: str, base: str = "main") -> dict[str, Any]:
        """Create a new branch from base."""
        if self.is_mock:
            return self._mock_create_branch(branch_name, base)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get base branch SHA
                ref_resp = await client.get(
                    self._repo_url(f"/git/refs/heads/{base}"),
                    headers=self._headers(),
                )
                if ref_resp.status_code == 404:
                    return {"success": False, "error": f"Base branch '{base}' not found"}
                ref_resp.raise_for_status()
                sha = ref_resp.json()["object"]["sha"]

                # Create branch
                create_resp = await client.post(
                    self._repo_url("/git/refs"),
                    headers=self._headers(),
                    json={"ref": f"refs/heads/{branch_name}", "sha": sha},
                )
                if create_resp.status_code == 422:
                    return {"success": False, "error": f"Branch '{branch_name}' already exists"}
                create_resp.raise_for_status()

                logger.info("github.branch_created", branch=branch_name, sha=sha[:8])
                return {
                    "success": True,
                    "branch": branch_name,
                    "sha": sha,
                    "url": f"https://github.com/{self.owner}/{self.repo}/tree/{branch_name}",
                }
        except Exception as e:
            logger.error("github.branch_failed", error=str(e))
            return {"success": False, "error": str(e)}

    # ─── Commit Operations ────────────────────────────────

    async def commit_file(
        self, branch_name: str, file_path: str, content: str, message: str
    ) -> dict[str, Any]:
        """Commit a file change to a branch."""
        if self.is_mock:
            return self._mock_commit(branch_name, file_path, message)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Get existing file SHA if it exists
                file_sha = None
                try:
                    existing = await client.get(
                        self._repo_url(f"/contents/{file_path}"),
                        headers=self._headers(),
                        params={"ref": branch_name},
                    )
                    if existing.status_code == 200:
                        file_sha = existing.json()["sha"]
                except Exception:
                    pass

                payload: dict[str, Any] = {
                    "message": message,
                    "content": base64.b64encode(content.encode()).decode(),
                    "branch": branch_name,
                }
                if file_sha:
                    payload["sha"] = file_sha

                resp = await client.put(
                    self._repo_url(f"/contents/{file_path}"),
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                commit_sha = resp.json()["commit"]["sha"]

                logger.info("github.committed", branch=branch_name, sha=commit_sha[:8])
                return {
                    "success": True,
                    "commit_sha": commit_sha,
                    "file_path": file_path,
                }
        except Exception as e:
            logger.error("github.commit_failed", error=str(e))
            return {"success": False, "error": str(e)}

    # ─── PR Operations ────────────────────────────────────

    async def create_pr(
        self, branch_name: str, title: str, body: str, base: str = "main"
    ) -> dict[str, Any]:
        """Create a pull request."""
        if self.is_mock:
            return self._mock_create_pr(branch_name, title, body, base)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._repo_url("/pulls"),
                    headers=self._headers(),
                    json={
                        "title": title,
                        "body": body,
                        "head": branch_name,
                        "base": base,
                    },
                )
                resp.raise_for_status()
                pr_data = resp.json()

                logger.info("github.pr_created", pr_number=pr_data["number"])
                return {
                    "success": True,
                    "pr_number": pr_data["number"],
                    "pr_url": pr_data["html_url"],
                    "state": pr_data["state"],
                }
        except Exception as e:
            logger.error("github.pr_failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def merge_pr(self, pr_number: int, merge_method: str = "squash") -> dict[str, Any]:
        """Merge a pull request."""
        if self.is_mock:
            return self._mock_merge_pr(pr_number)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(
                    self._repo_url(f"/pulls/{pr_number}/merge"),
                    headers=self._headers(),
                    json={"merge_method": merge_method},
                )
                if resp.status_code == 405:
                    return {"success": False, "error": "PR is not mergeable — check for conflicts"}
                if resp.status_code == 409:
                    return {"success": False, "error": "Merge conflict — resolve manually"}
                resp.raise_for_status()
                data = resp.json()

                logger.info("github.pr_merged", pr_number=pr_number)
                return {
                    "success": True,
                    "merged": data.get("merged", True),
                    "sha": data.get("sha", ""),
                    "message": data.get("message", "PR merged"),
                }
        except Exception as e:
            logger.error("github.merge_failed", error=str(e))
            return {"success": False, "error": str(e)}

    # ─── Mock Responses ───────────────────────────────────

    def _mock_validate_token(self) -> dict[str, Any]:
        return {"valid": True, "username": "demo-user", "scopes": "repo", "has_repo_scope": True, "mock": True}

    def _mock_validate_repo(self) -> dict[str, Any]:
        return {
            "valid": True,
            "full_name": f"{self.owner}/{self.repo}",
            "default_branch": "main",
            "private": False,
            "permissions": {"push": True, "pull": True, "admin": False},
            "description": "Demo repository for AutoMerge",
            "mock": True,
        }

    def _mock_file_contents(self, file_path: str, ref: str) -> dict[str, Any]:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "py"
        mock_code = {
            "py": 'def calculate_total(items):\n    total = 0\n    for item in items:\n        total += item.price\n    return total\n\n\ndef process_order(order):\n    user_id = order["user"]["id"]\n    items = order["items"]\n    total = calculate_total(items)\n    discount = order["discount"]["percentage"]\n    final = total - (total * discount)\n    return {"user": user_id, "total": final}\n',
            "ts": 'async function fetchUser(id: string) {\n  const response = await fetch(`/api/users/${id}`);\n  const data = response.json();\n  return data.user.name;\n}\n',
            "js": 'function processItems(items) {\n  var result = [];\n  for (var i = 0; i < items.length; i++) {\n    result.push(items[i].name);\n  }\n  return result;\n}\n',
        }
        return {
            "success": True,
            "content": mock_code.get(ext, mock_code["py"]),
            "sha": hashlib.sha1(file_path.encode()).hexdigest()[:12],
            "size": 450,
            "path": file_path,
            "mock": True,
        }

    def _mock_create_branch(self, branch: str, base: str) -> dict[str, Any]:
        sha = hashlib.sha1(branch.encode()).hexdigest()[:8]
        return {
            "success": True,
            "branch": branch,
            "sha": sha + "a1b2c3d4",
            "url": f"https://github.com/{self.owner}/{self.repo}/tree/{branch}",
            "mock": True,
        }

    def _mock_commit(self, branch: str, file_path: str, message: str) -> dict[str, Any]:
        sha = hashlib.sha1(f"{branch}{file_path}".encode()).hexdigest()[:12]
        return {
            "success": True,
            "commit_sha": sha,
            "file_path": file_path,
            "mock": True,
        }

    def _mock_create_pr(self, branch: str, title: str, body: str, base: str) -> dict[str, Any]:
        pr_num = random.randint(10, 999)
        return {
            "success": True,
            "pr_number": pr_num,
            "pr_url": f"https://github.com/{self.owner}/{self.repo}/pull/{pr_num}",
            "state": "open",
            "mock": True,
        }

    def _mock_merge_pr(self, pr_number: int) -> dict[str, Any]:
        return {
            "success": True,
            "merged": True,
            "sha": hashlib.sha1(str(pr_number).encode()).hexdigest()[:12],
            "message": "PR merged successfully",
            "mock": True,
        }


def create_github_client(token: str, repo_url: str) -> GitHubClient:
    """Factory: create a GitHubClient from a repo URL and token."""
    owner, repo = parse_repo_url(repo_url)
    return GitHubClient(token, owner, repo)

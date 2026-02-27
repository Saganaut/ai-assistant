"""GitHub API integration - Projects, Repos, Issues."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """GitHub API client using personal access token."""

    BASE_URL = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self):
        self._token = settings.github_token

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise ValueError("GitHub token not configured. Set ASSISTANT_GITHUB_TOKEN.")
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # --- REST API methods ---

    async def list_repos(self, per_page: int = 20) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/user/repos",
                headers=self._headers(),
                params={"per_page": per_page, "sort": "updated"},
            )
            resp.raise_for_status()
            return resp.json()

    async def search_repos(self, query: str, per_page: int = 10) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/search/repositories",
                headers=self._headers(),
                params={"q": query, "per_page": per_page},
            )
            resp.raise_for_status()
            return resp.json().get("items", [])

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", per_page: int = 20
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                params={"state": state, "per_page": per_page},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_issue(
        self, owner: str, repo: str, number: int,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            issue = resp.json()

            # Fetch comments
            comments_resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}/comments",
                headers=self._headers(),
                params={"per_page": 30},
            )
            comments_resp.raise_for_status()
            issue["_comments"] = comments_resp.json()

            return issue

    async def read_file(self, owner: str, repo: str, path: str, ref: str = "main") -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(),
                params={"ref": ref},
            )
            resp.raise_for_status()
            return resp.json()

    # --- GraphQL methods for GitHub Projects ---

    async def _graphql(self, query: str, variables: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.GRAPHQL_URL,
                headers=self._headers(),
                json={"query": query, "variables": variables or {}},
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            return data["data"]

    async def list_projects(self, owner: str | None = None) -> list[dict[str, Any]]:
        """List GitHub Projects (v2) for the authenticated user, a user, or an org."""
        if owner:
            # Try as user first, fall back to organization
            query = """
            query($owner: String!) {
                user(login: $owner) {
                    projectsV2(first: 20) {
                        nodes { id number title shortDescription closed
                                viewerCanUpdate
                                owner { ... on User { login } ... on Organization { login } } }
                    }
                }
            }
            """
            try:
                data = await self._graphql(query, {"owner": owner})
                return data["user"]["projectsV2"]["nodes"]
            except Exception:
                pass

            # Fall back to organization query
            query = """
            query($owner: String!) {
                organization(login: $owner) {
                    projectsV2(first: 20) {
                        nodes { id number title shortDescription closed
                                viewerCanUpdate
                                owner { ... on User { login } ... on Organization { login } } }
                    }
                }
            }
            """
            data = await self._graphql(query, {"owner": owner})
            return data["organization"]["projectsV2"]["nodes"]
        else:
            query = """
            query {
                viewer {
                    projectsV2(first: 20) {
                        nodes { id number title shortDescription closed
                                owner { ... on User { login } ... on Organization { login } } }
                    }
                }
            }
            """
            data = await self._graphql(query)
            return data["viewer"]["projectsV2"]["nodes"]

    async def list_accessible_projects(
        self, extra_owners: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List all projects the viewer owns or collaborates on.

        Since GitHub has no 'projects I collaborate on' API, we query the
        viewer's own projects plus projects belonging to *extra_owners*.
        Only projects where the viewer has access are returned.
        """
        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        # Viewer's own projects
        try:
            own = await self.list_projects()
            for p in own:
                pid = p.get("id", "")
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    results.append(p)
        except Exception:
            pass

        # Projects from extra owners
        for owner in extra_owners or []:
            try:
                projects = await self.list_projects(owner=owner)
                for p in projects:
                    pid = p.get("id", "")
                    if pid not in seen_ids and p.get("viewerCanUpdate"):
                        seen_ids.add(pid)
                        results.append(p)
            except Exception:
                pass

        return results

    async def resolve_project_id(self, owner: str, number: int) -> str:
        """Resolve a project owner + number to a GraphQL node ID."""
        projects = await self.list_projects(owner=owner)
        for p in projects:
            if p.get("number") == number:
                return p["id"]
        raise ValueError(f"Project #{number} not found for {owner}")

    async def list_project_items(self, project_id: str, first: int = 50) -> list[dict[str, Any]]:
        query = """
        query($projectId: ID!, $first: Int!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: $first) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    title
                                    number
                                    state
                                    url
                                }
                                ... on PullRequest {
                                    title
                                    number
                                    state
                                    url
                                }
                                ... on DraftIssue {
                                    title
                                }
                            }
                            fieldValues(first: 10) {
                                nodes {
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                        field { ... on ProjectV2SingleSelectField { name } }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"projectId": project_id, "first": first})
        return data["node"]["items"]["nodes"]

    async def add_project_draft_issue(
        self, project_id: str, title: str, body: str = ""
    ) -> dict[str, Any]:
        query = """
        mutation($projectId: ID!, $title: String!, $body: String) {
            addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
                projectItem { id }
            }
        }
        """
        data = await self._graphql(query, {
            "projectId": project_id, "title": title, "body": body
        })
        return data["addProjectV2DraftIssue"]["projectItem"]

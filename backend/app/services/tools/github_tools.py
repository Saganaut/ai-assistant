"""GitHub integration tools - Projects, Repos, Issues."""

import base64
import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.integrations.github import GitHubService
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter

_github = GitHubService()

_SOURCES_FILE = settings.data_dir / "github_project_sources.json"


def _load_project_sources() -> list[str]:
    if _SOURCES_FILE.exists():
        try:
            return json.loads(_SOURCES_FILE.read_text())
        except Exception:
            pass
    return []


class GitHubListReposTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_repos_list",
            description="List the user's GitHub repositories, sorted by most recently updated.",
            parameters=[
                ToolParameter(
                    name="per_page", type="integer",
                    description="Number of repos to return (default 20).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            repos = await _github.list_repos(per_page=kwargs.get("per_page", 20))
        except Exception as e:
            return f"Error listing repos: {e}"

        if not repos:
            return "No repositories found."

        lines = []
        for r in repos:
            name = r.get("full_name", "?")
            desc = r.get("description", "") or ""
            private = " (private)" if r.get("private") else ""
            lines.append(f"- {name}{private}: {desc[:80]}")
        return "Repositories:\n" + "\n".join(lines)


class GitHubListIssuesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_issues_list",
            description="List issues for a GitHub repository.",
            parameters=[
                ToolParameter(name="owner", type="string", description="Repository owner"),
                ToolParameter(name="repo", type="string", description="Repository name"),
                ToolParameter(
                    name="state", type="string",
                    description="Issue state filter",
                    required=False,
                    enum=["open", "closed", "all"],
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            issues = await _github.list_issues(
                owner=kwargs["owner"],
                repo=kwargs["repo"],
                state=kwargs.get("state", "open"),
            )
        except Exception as e:
            return f"Error listing issues: {e}"

        if not issues:
            return "No issues found."

        lines = []
        for issue in issues:
            num = issue.get("number")
            title = issue.get("title", "?")
            state = issue.get("state", "?")
            labels = ", ".join(l["name"] for l in issue.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"- #{num} ({state}){label_str}: {title}")
        return "Issues:\n" + "\n".join(lines)


class GitHubCreateIssueTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_issues_create",
            description="Create a new issue in a GitHub repository.",
            parameters=[
                ToolParameter(name="owner", type="string", description="Repository owner"),
                ToolParameter(name="repo", type="string", description="Repository name"),
                ToolParameter(name="title", type="string", description="Issue title"),
                ToolParameter(name="body", type="string", description="Issue body/description", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            issue = await _github.create_issue(
                owner=kwargs["owner"],
                repo=kwargs["repo"],
                title=kwargs["title"],
                body=kwargs.get("body", ""),
            )
            return f"Issue created: #{issue['number']} - {issue['title']} ({issue['html_url']})"
        except Exception as e:
            return f"Error creating issue: {e}"


class GitHubReadFileTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_repos_read_file",
            description="Read a file from a GitHub repository.",
            parameters=[
                ToolParameter(name="owner", type="string", description="Repository owner"),
                ToolParameter(name="repo", type="string", description="Repository name"),
                ToolParameter(name="path", type="string", description="File path in the repository"),
                ToolParameter(name="ref", type="string", description="Branch or commit ref (default 'main')", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            data = await _github.read_file(
                owner=kwargs["owner"],
                repo=kwargs["repo"],
                path=kwargs["path"],
                ref=kwargs.get("ref", "main"),
            )
            if data.get("type") == "file" and data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8")
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (truncated)"
                return content
            return f"Not a file or empty: {data.get('type', '?')}"
        except Exception as e:
            return f"Error reading file: {e}"


class GitHubListProjectsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_projects_list",
            description=(
                "List GitHub Projects (v2) the user has access to, "
                "including projects from configured sources. "
                "Call this with no arguments to see all accessible projects."
            ),
            parameters=[
                ToolParameter(
                    name="owner", type="string",
                    description="Optional: a specific GitHub username or org to query. Leave empty to list all accessible projects.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            owner = kwargs.get("owner")
            if owner:
                projects = await _github.list_projects(owner=owner)
            else:
                sources = _load_project_sources()
                projects = await _github.list_accessible_projects(extra_owners=sources)
        except Exception as e:
            return f"Error listing projects: {e}"

        if not projects:
            return "No projects found."

        lines = []
        for p in projects:
            title = p.get("title", "?")
            num = p.get("number", "?")
            desc = p.get("shortDescription", "") or ""
            closed = " (closed)" if p.get("closed") else ""
            pid = p.get("id", "")
            owner_login = (p.get("owner") or {}).get("login", "")
            owner_str = f" (owner: {owner_login})" if owner_login else ""
            lines.append(f"- #{num}: {title}{closed}{owner_str} [node_id: {pid}]\n  {desc}")
        return "Projects:\n" + "\n".join(lines)


class GitHubListProjectItemsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_projects_items",
            description=(
                "List items (cards) in a GitHub Project. Shows status/column for each item. "
                "You can provide either the project node_id directly, or an owner + project_number to resolve it."
            ),
            parameters=[
                ToolParameter(
                    name="project_id", type="string",
                    description="The Project node ID (e.g. 'PVT_kwHO...'). Optional if owner and project_number are provided.",
                    required=False,
                ),
                ToolParameter(
                    name="owner", type="string",
                    description="GitHub username or org that owns the project. Use with project_number.",
                    required=False,
                ),
                ToolParameter(
                    name="project_number", type="integer",
                    description="The project number (e.g. 3). Use with owner.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            project_id = kwargs.get("project_id", "")
            owner = kwargs.get("owner", "")
            project_number = kwargs.get("project_number")

            # Resolve project_id from owner + number if not provided directly
            if not project_id or not project_id.startswith("PVT_"):
                if owner and project_number is not None:
                    project_id = await _github.resolve_project_id(owner, int(project_number))
                elif not project_id:
                    return "Error: provide either project_id, or owner + project_number."

            items = await _github.list_project_items(project_id)
        except Exception as e:
            return f"Error listing project items: {e}"

        if not items:
            return "No items in this project."

        lines = []
        for item in items:
            content = item.get("content", {}) or {}
            title = content.get("title", "(Draft)")
            number = content.get("number", "")
            state = content.get("state", "")
            url = content.get("url", "")

            # Get status field
            status = ""
            for fv in (item.get("fieldValues", {}).get("nodes", [])):
                if fv.get("field", {}).get("name") == "Status":
                    status = fv.get("name", "")

            num_str = f"#{number} " if number else ""
            state_str = f"({state}) " if state else ""
            status_str = f"[{status}] " if status else ""
            lines.append(f"- {status_str}{num_str}{state_str}{title}" + (f"\n  {url}" if url else ""))
        return "Project items:\n" + "\n".join(lines)


class GitHubAddProjectItemTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_projects_add_item",
            description=(
                "Add a draft issue/card to a GitHub Project. "
                "You can provide either the project node_id directly, or an owner + project_number to resolve it."
            ),
            parameters=[
                ToolParameter(
                    name="project_id", type="string",
                    description="The Project node ID (e.g. 'PVT_kwHO...'). Optional if owner and project_number are provided.",
                    required=False,
                ),
                ToolParameter(
                    name="owner", type="string",
                    description="GitHub username or org that owns the project. Use with project_number.",
                    required=False,
                ),
                ToolParameter(
                    name="project_number", type="integer",
                    description="The project number (e.g. 3). Use with owner.",
                    required=False,
                ),
                ToolParameter(name="title", type="string", description="Title for the new card"),
                ToolParameter(name="body", type="string", description="Description/body for the card", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            project_id = kwargs.get("project_id", "")
            owner = kwargs.get("owner", "")
            project_number = kwargs.get("project_number")

            if not project_id or not project_id.startswith("PVT_"):
                if owner and project_number is not None:
                    project_id = await _github.resolve_project_id(owner, int(project_number))
                elif not project_id:
                    return "Error: provide either project_id, or owner + project_number."

            item = await _github.add_project_draft_issue(
                project_id=project_id,
                title=kwargs["title"],
                body=kwargs.get("body", ""),
            )
            return f"Card added to project (item id: {item.get('id', '?')})"
        except Exception as e:
            return f"Error adding card: {e}"

"""GitHub integration tools - Projects, Repos, Issues."""

import base64
from typing import Any

from app.services.integrations.github import GitHubService
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter

_github = GitHubService()


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
            description="List GitHub Projects (v2) for the authenticated user or an organization.",
            parameters=[
                ToolParameter(
                    name="owner", type="string",
                    description="Organization login name. Leave empty for user's own projects.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            projects = await _github.list_projects(owner=kwargs.get("owner"))
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
            lines.append(f"- #{num}: {title}{closed} [id: {pid}]\n  {desc}")
        return "Projects:\n" + "\n".join(lines)


class GitHubListProjectItemsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_projects_items",
            description="List items (cards) in a GitHub Project. Shows status/column for each item.",
            parameters=[
                ToolParameter(name="project_id", type="string", description="The Project node ID"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            items = await _github.list_project_items(kwargs["project_id"])
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
            description="Add a draft issue/card to a GitHub Project.",
            parameters=[
                ToolParameter(name="project_id", type="string", description="The Project node ID"),
                ToolParameter(name="title", type="string", description="Title for the new card"),
                ToolParameter(name="body", type="string", description="Description/body for the card", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            item = await _github.add_project_draft_issue(
                project_id=kwargs["project_id"],
                title=kwargs["title"],
                body=kwargs.get("body", ""),
            )
            return f"Card added to project (item id: {item.get('id', '?')})"
        except Exception as e:
            return f"Error adding card: {e}"

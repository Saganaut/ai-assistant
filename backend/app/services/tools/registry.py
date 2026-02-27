"""Tool registry - central place to register and look up all available tools."""

from app.services.tools.base import BaseTool, ToolDefinition
from app.services.tools.file_tools import (
    ListFilesTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)
from app.services.tools.github_tools import (
    GitHubAddProjectItemTool,
    GitHubCreateIssueTool,
    GitHubListIssuesTool,
    GitHubListProjectItemsTool,
    GitHubListProjectsTool,
    GitHubListReposTool,
    GitHubReadFileTool,
)
from app.services.tools.google_tools import (
    CalendarCreateEventTool,
    CalendarDeleteEventTool,
    CalendarListEventsTool,
    DriveListFilesTool,
    DriveSearchTool,
    GmailListTool,
    GmailReadTool,
    GmailSendTool,
)
from app.services.tools.note_tools import HealthNoteTool, QuickNoteTool, ReadNotesTool
from app.services.tools.web_tools import SaveBookmarkTool, WebBrowseTool, WebSearchTool
from app.services.tools.wordpress_tools import (
    WordPressCreatePostTool,
    WordPressDeletePostTool,
    WordPressGetPostTool,
    WordPressListCategoriesTool,
    WordPressListPostsTool,
    WordPressListTagsTool,
    WordPressUpdatePostTool,
    WordPressUploadMediaTool,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        defn = tool.definition()
        self._tools[defn.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    def gemini_declarations(self) -> list[dict]:
        return [defn.to_gemini_schema() for defn in self.definitions()]


def create_default_registry() -> ToolRegistry:
    """Create a registry with all default tools."""
    registry = ToolRegistry()

    # File tools
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListFilesTool())
    registry.register(SearchFilesTool())

    # Web tools
    registry.register(WebBrowseTool())
    registry.register(WebSearchTool())
    registry.register(SaveBookmarkTool())

    # Note tools
    registry.register(HealthNoteTool())
    registry.register(QuickNoteTool())
    registry.register(ReadNotesTool())

    # Google tools
    registry.register(CalendarListEventsTool())
    registry.register(CalendarCreateEventTool())
    registry.register(CalendarDeleteEventTool())
    registry.register(DriveListFilesTool())
    registry.register(DriveSearchTool())
    registry.register(GmailListTool())
    registry.register(GmailReadTool())
    registry.register(GmailSendTool())

    # GitHub tools
    registry.register(GitHubListReposTool())
    registry.register(GitHubListIssuesTool())
    registry.register(GitHubCreateIssueTool())
    registry.register(GitHubReadFileTool())
    registry.register(GitHubListProjectsTool())
    registry.register(GitHubListProjectItemsTool())
    registry.register(GitHubAddProjectItemTool())

    # WordPress tools
    registry.register(WordPressListPostsTool())
    registry.register(WordPressGetPostTool())
    registry.register(WordPressCreatePostTool())
    registry.register(WordPressUpdatePostTool())
    registry.register(WordPressDeletePostTool())
    registry.register(WordPressUploadMediaTool())
    registry.register(WordPressListTagsTool())
    registry.register(WordPressListCategoriesTool())

    return registry

"""WordPress integration tools - Posts, Media, Tags, Categories."""

from typing import Any

from app.core.config import settings
from app.services.integrations.wordpress import WordPressService
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter

_wp = WordPressService()


def _strip_html(html: str) -> str:
    """Naively strip HTML tags for text summaries."""
    import re
    text = re.sub(r"<[^>]+>", "", html)
    return text.strip()


class WordPressListPostsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_posts_list",
            description="List recent WordPress posts. Can filter by status.",
            parameters=[
                ToolParameter(
                    name="status", type="string",
                    description="Post status filter (default 'any').",
                    required=False,
                    enum=["publish", "draft", "pending", "private", "any"],
                ),
                ToolParameter(
                    name="per_page", type="integer",
                    description="Number of posts to return (default 10).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured. Set ASSISTANT_WORDPRESS_URL, ASSISTANT_WORDPRESS_USERNAME, and ASSISTANT_WORDPRESS_APP_PASSWORD."
        try:
            posts = await _wp.list_posts(
                status=kwargs.get("status", "any"),
                per_page=kwargs.get("per_page", 10),
            )
        except Exception as e:
            return f"Error listing posts: {e}"

        if not posts:
            return "No posts found."

        lines = []
        for p in posts:
            title = _strip_html(p.get("title", {}).get("rendered", "Untitled"))
            status = p.get("status", "?")
            pid = p.get("id", "?")
            lines.append(f"- [{status}] #{pid}: {title}")
        return "WordPress posts:\n" + "\n".join(lines)


class WordPressGetPostTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_posts_get",
            description="Get a WordPress post by ID, including full content.",
            parameters=[
                ToolParameter(name="post_id", type="integer", description="The post ID"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            p = await _wp.get_post(kwargs["post_id"])
        except Exception as e:
            return f"Error getting post: {e}"

        title = _strip_html(p.get("title", {}).get("rendered", "Untitled"))
        content = _strip_html(p.get("content", {}).get("rendered", ""))
        if len(content) > 2000:
            content = content[:2000] + "... (truncated)"
        status = p.get("status", "?")
        url = p.get("link", "")
        excerpt = _strip_html(p.get("excerpt", {}).get("rendered", ""))

        return (
            f"Post #{p.get('id', '?')}: {title}\n"
            f"Status: {status}\n"
            f"URL: {url}\n"
            f"Excerpt: {excerpt}\n\n"
            f"Content:\n{content}"
        )


class WordPressCreatePostTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_posts_create",
            description="Create a new WordPress post. Categories and tags accept comma-separated names (will be created if they don't exist).",
            parameters=[
                ToolParameter(name="title", type="string", description="Post title"),
                ToolParameter(name="content", type="string", description="Post content (HTML supported)"),
                ToolParameter(
                    name="status", type="string",
                    description="Post status (default 'draft').",
                    required=False,
                    enum=["publish", "draft", "pending", "private"],
                ),
                ToolParameter(
                    name="categories", type="string",
                    description="Comma-separated category names.",
                    required=False,
                ),
                ToolParameter(
                    name="tags", type="string",
                    description="Comma-separated tag names.",
                    required=False,
                ),
                ToolParameter(
                    name="excerpt", type="string",
                    description="Post excerpt/summary.",
                    required=False,
                ),
                ToolParameter(
                    name="privacy_level", type="string",
                    description="Privacy level: 'public' (default), 'semi-private' (images hidden behind password), 'full-private' (all content hidden behind password).",
                    required=False,
                    enum=["public", "semi-private", "full-private"],
                ),
                ToolParameter(
                    name="post_password", type="string",
                    description="Password for semi-private or full-private posts. Leave blank to use the site default password.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            cat_ids = None
            tag_ids = None
            if kwargs.get("categories"):
                names = [n.strip() for n in kwargs["categories"].split(",")]
                cat_ids = await _wp.get_or_create_categories(names)
            if kwargs.get("tags"):
                names = [n.strip() for n in kwargs["tags"].split(",")]
                tag_ids = await _wp.get_or_create_tags(names)

            post = await _wp.create_post(
                title=kwargs["title"],
                content=kwargs["content"],
                status=kwargs.get("status", "draft"),
                categories=cat_ids,
                tags=tag_ids,
                excerpt=kwargs.get("excerpt", ""),
                privacy_level=kwargs.get("privacy_level", "public"),
                post_password=kwargs.get("post_password", ""),
            )
            return (
                f"Post created: #{post['id']} - {_strip_html(post.get('title', {}).get('rendered', ''))}\n"
                f"Status: {post.get('status', '?')}\n"
                f"URL: {post.get('link', '')}"
            )
        except Exception as e:
            return f"Error creating post: {e}"


class WordPressUpdatePostTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_posts_update",
            description="Update an existing WordPress post. Only provided fields are changed.",
            parameters=[
                ToolParameter(name="post_id", type="integer", description="The post ID to update"),
                ToolParameter(name="title", type="string", description="New title", required=False),
                ToolParameter(name="content", type="string", description="New content", required=False),
                ToolParameter(
                    name="status", type="string",
                    description="New status.",
                    required=False,
                    enum=["publish", "draft", "pending", "private"],
                ),
                ToolParameter(
                    name="categories", type="string",
                    description="Comma-separated category names.",
                    required=False,
                ),
                ToolParameter(
                    name="tags", type="string",
                    description="Comma-separated tag names.",
                    required=False,
                ),
                ToolParameter(name="excerpt", type="string", description="New excerpt", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            fields: dict[str, Any] = {}
            if kwargs.get("title"):
                fields["title"] = kwargs["title"]
            if kwargs.get("content"):
                fields["content"] = kwargs["content"]
            if kwargs.get("status"):
                fields["status"] = kwargs["status"]
            if kwargs.get("excerpt"):
                fields["excerpt"] = kwargs["excerpt"]
            if kwargs.get("categories"):
                names = [n.strip() for n in kwargs["categories"].split(",")]
                fields["categories"] = await _wp.get_or_create_categories(names)
            if kwargs.get("tags"):
                names = [n.strip() for n in kwargs["tags"].split(",")]
                fields["tags"] = await _wp.get_or_create_tags(names)

            if not fields:
                return "No fields to update."

            post = await _wp.update_post(kwargs["post_id"], **fields)
            return (
                f"Post updated: #{post['id']} - {_strip_html(post.get('title', {}).get('rendered', ''))}\n"
                f"Status: {post.get('status', '?')}"
            )
        except Exception as e:
            return f"Error updating post: {e}"


class WordPressDeletePostTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_posts_delete",
            description="Delete a WordPress post by ID (moves to trash).",
            parameters=[
                ToolParameter(name="post_id", type="integer", description="The post ID to delete"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            await _wp.delete_post(kwargs["post_id"])
            return f"Post #{kwargs['post_id']} deleted (moved to trash)."
        except Exception as e:
            return f"Error deleting post: {e}"


class WordPressUploadMediaTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_media_upload",
            description="Upload an image from the data directory to WordPress. Automatically converts to WebP and resizes to under 100KB.",
            parameters=[
                ToolParameter(
                    name="file_path", type="string",
                    description="Path to the image file relative to the data directory (e.g. 'photos/pic.jpg').",
                ),
                ToolParameter(
                    name="alt_text", type="string",
                    description="Alt text for the image.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            file_path = settings.data_dir / kwargs["file_path"]
            # Ensure sandboxed
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(settings.data_dir.resolve())):
                return "Error: file path must be within the data directory."
            if not resolved.exists():
                return f"Error: file not found: {kwargs['file_path']}"

            raw_data = resolved.read_bytes()
            webp_data, filename = _wp._process_image(raw_data)

            media = await _wp.upload_media(
                filename=filename,
                data=webp_data,
                content_type="image/webp",
                alt_text=kwargs.get("alt_text", ""),
            )

            return (
                f"Image uploaded: ID #{media.get('id', '?')}\n"
                f"URL: {media.get('source_url', '')}\n"
                f"Size: {len(webp_data)} bytes (WebP)"
            )
        except Exception as e:
            return f"Error uploading media: {e}"


class WordPressListTagsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_tags_list",
            description="List WordPress tags, optionally filtering by search term.",
            parameters=[
                ToolParameter(
                    name="search", type="string",
                    description="Search term to filter tags.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            tags = await _wp.list_tags(search=kwargs.get("search", ""))
        except Exception as e:
            return f"Error listing tags: {e}"

        if not tags:
            return "No tags found."

        lines = [f"- {t['name']} (ID: {t['id']}, count: {t.get('count', 0)})" for t in tags]
        return "WordPress tags:\n" + "\n".join(lines)


class WordPressListCategoriesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wordpress_categories_list",
            description="List all WordPress categories.",
            parameters=[],
        )

    async def execute(self, **kwargs: Any) -> str:
        if not _wp.is_configured:
            return "WordPress not configured."
        try:
            cats = await _wp.list_categories()
        except Exception as e:
            return f"Error listing categories: {e}"

        if not cats:
            return "No categories found."

        lines = [f"- {c['name']} (ID: {c['id']}, count: {c.get('count', 0)})" for c in cats]
        return "WordPress categories:\n" + "\n".join(lines)

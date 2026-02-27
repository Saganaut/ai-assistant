"""Integration status and data endpoints for Google and GitHub."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.integrations.github import GitHubService
from app.services.integrations.google import GoogleCalendarService
from app.services.integrations.wordpress import WordPressService
from app.services.tools.google_tools import get_google_service

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Project sources persistence ---

_SOURCES_FILE = settings.data_dir / "github_project_sources.json"


def _load_project_sources() -> list[str]:
    if _SOURCES_FILE.exists():
        try:
            return json.loads(_SOURCES_FILE.read_text())
        except Exception:
            pass
    return []


def _save_project_sources(sources: list[str]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _SOURCES_FILE.write_text(json.dumps(sources))


# --- Status ---


def _check_google() -> dict:
    """Check Google credentials: configured (file exists) and connected (token valid)."""
    service = get_google_service()
    if not service.is_configured:
        return {"configured": False, "connected": False, "services": []}

    try:
        creds = service._get_credentials()
        if creds and creds.token:
            return {
                "configured": True,
                "connected": True,
                "services": ["calendar", "drive", "gmail"],
            }
    except Exception as e:
        logger.debug(f"Google credentials validation failed: {e}")

    return {"configured": True, "connected": False, "services": []}


async def _check_github() -> dict:
    """Check GitHub token: configured (token set) and connected (API responds)."""
    if not settings.github_token:
        return {"configured": False, "connected": False}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {settings.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=5.0,
            )
            if resp.status_code == 200:
                return {"configured": True, "connected": True}
    except Exception as e:
        logger.debug(f"GitHub token validation failed: {e}")

    return {"configured": True, "connected": False}


async def _check_wordpress() -> dict:
    """Check WordPress: configured (settings set) and connected (XML-RPC auth works)."""
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False, "connected": False}

    try:
        result = await wp.check_xmlrpc()
        if result.get("ok"):
            return {"configured": True, "connected": True}
    except Exception as e:
        logger.debug(f"WordPress connection check failed: {e}")

    return {"configured": True, "connected": False}


@router.get("/status")
async def integration_status():
    google_status = _check_google()
    github_status = await _check_github()
    wordpress_status = await _check_wordpress()
    return {
        "google": google_status,
        "github": github_status,
        "wordpress": wordpress_status,
    }


# --- Calendar ---


@router.get("/calendar/events")
async def calendar_events(
    date: str = Query(
        default="",
        description="Date in YYYY-MM-DD format. Defaults to today.",
    ),
):
    """Fetch Google Calendar events for a given day."""
    service = get_google_service()
    if not service.is_configured:
        return {"configured": False, "events": []}

    try:
        if date:
            day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        time_min = day.isoformat()
        time_max = (day + timedelta(days=1)).isoformat()

        calendar = GoogleCalendarService(service)
        events = await calendar.list_events(
            time_min=time_min,
            time_max=time_max,
            max_results=50,
        )

        results = []
        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})
            results.append({
                "id": event.get("id", ""),
                "title": event.get("summary", "(No title)"),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "location": event.get("location", ""),
                "all_day": "date" in start and "dateTime" not in start,
            })

        return {"configured": True, "events": results}
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {e}")
        return {"configured": True, "events": [], "error": str(e)}


# --- GitHub Projects ---


@router.get("/github/project-sources")
async def get_project_sources():
    """Get the list of GitHub usernames/orgs to search for projects."""
    return {"sources": _load_project_sources()}


class AddSourceRequest(BaseModel):
    owner: str


@router.post("/github/project-sources")
async def add_project_source(req: AddSourceRequest):
    """Add a GitHub username/org to search for projects."""
    owner = req.owner.strip()
    if not owner:
        return {"error": "Owner cannot be empty"}

    sources = _load_project_sources()
    if owner.lower() not in [s.lower() for s in sources]:
        sources.append(owner)
        _save_project_sources(sources)
    return {"sources": sources}


@router.delete("/github/project-sources/{owner}")
async def remove_project_source(owner: str):
    """Remove a GitHub username/org from project sources."""
    sources = _load_project_sources()
    sources = [s for s in sources if s.lower() != owner.lower()]
    _save_project_sources(sources)
    return {"sources": sources}


@router.get("/github/projects")
async def github_projects():
    """List GitHub Projects v2 the user owns or is a collaborator on."""
    if not settings.github_token:
        return {"configured": False, "projects": []}

    try:
        sources = _load_project_sources()
        github = GitHubService()
        projects = await github.list_accessible_projects(extra_owners=sources)
        results = [
            {
                "id": p.get("id", ""),
                "number": p.get("number"),
                "title": p.get("title", ""),
                "description": p.get("shortDescription", "") or "",
                "closed": p.get("closed", False),
                "owner": (p.get("owner") or {}).get("login", ""),
            }
            for p in projects
            if not p.get("closed", False)
        ]
        return {"configured": True, "projects": results}
    except Exception as e:
        logger.error(f"Failed to fetch GitHub projects: {e}")
        return {"configured": True, "projects": [], "error": str(e)}


@router.get("/github/projects/{project_id}/items")
async def github_project_items(project_id: str):
    """List items in a GitHub Project, grouped by status column."""
    if not settings.github_token:
        return {"configured": False, "columns": []}

    try:
        github = GitHubService()
        items = await github.list_project_items(project_id)

        # Group items by their Status field
        columns: dict[str, list[dict]] = {}
        no_status_items: list[dict] = []

        for item in items:
            content = item.get("content", {}) or {}
            parsed = {
                "id": item.get("id", ""),
                "title": content.get("title", "(Draft)"),
                "number": content.get("number"),
                "state": content.get("state", ""),
                "url": content.get("url", ""),
            }

            # Extract status field value
            status = ""
            for fv in item.get("fieldValues", {}).get("nodes", []):
                field = fv.get("field", {})
                if field.get("name") == "Status":
                    status = fv.get("name", "")
                    break

            if status:
                columns.setdefault(status, []).append(parsed)
            else:
                no_status_items.append(parsed)

        # Build ordered column list
        result_columns = []
        for col_name, col_items in columns.items():
            result_columns.append({"name": col_name, "items": col_items})

        if no_status_items:
            result_columns.append({"name": "No Status", "items": no_status_items})

        return {"configured": True, "columns": result_columns}
    except Exception as e:
        logger.error(f"Failed to fetch project items: {e}")
        return {"configured": True, "columns": [], "error": str(e)}


@router.get("/github/issues/{owner}/{repo}/{number}")
async def github_issue_detail(owner: str, repo: str, number: int):
    """Get details for a specific GitHub issue."""
    if not settings.github_token:
        return {"configured": False}

    try:
        github = GitHubService()
        issue = await github.get_issue(owner, repo, number)
        comments = [
            {
                "author": c.get("user", {}).get("login", "?"),
                "body": c.get("body", ""),
                "created_at": c.get("created_at", ""),
            }
            for c in issue.get("_comments", [])
        ]
        return {
            "configured": True,
            "issue": {
                "number": issue.get("number"),
                "title": issue.get("title", ""),
                "state": issue.get("state", ""),
                "body": issue.get("body", "") or "",
                "url": issue.get("html_url", ""),
                "author": issue.get("user", {}).get("login", ""),
                "assignees": [a.get("login", "") for a in issue.get("assignees", [])],
                "labels": [l.get("name", "") for l in issue.get("labels", [])],
                "created_at": issue.get("created_at", ""),
                "updated_at": issue.get("updated_at", ""),
                "comments": comments,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch issue: {e}")
        return {"configured": True, "error": str(e)}


# --- WordPress ---

def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


def _format_wp_post(p: dict) -> dict:
    return {
        "id": p.get("id"),
        "title": _strip_html(p.get("title", {}).get("rendered", "Untitled")),
        "status": p.get("status", ""),
        "date": p.get("date", ""),
        "url": p.get("link", ""),
        "excerpt": _strip_html(p.get("excerpt", {}).get("rendered", "")),
        "content": _strip_html(p.get("content", {}).get("rendered", "")),
        "tags": p.get("tags", []),
        "categories": p.get("categories", []),
        "privacy_level": p.get("privacy_level", "public"),
    }


@router.get("/wordpress/categories")
async def wordpress_categories():
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False, "categories": []}

    try:
        cats = await wp.list_categories()
        return {
            "configured": True,
            "categories": [
                {"id": c.get("id"), "name": c.get("name", "")}
                for c in cats
                if c.get("name", "").lower() != "uncategorized"
            ],
        }
    except Exception as e:
        logger.error(f"Failed to fetch WordPress categories: {e}")
        return {"configured": True, "categories": [], "error": str(e)}


@router.get("/wordpress/posts")
async def wordpress_posts(
    status: str = Query(default="any", description="Post status filter"),
    per_page: int = Query(default=10, description="Number of posts"),
):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False, "posts": []}

    try:
        posts = await wp.list_posts(status=status, per_page=per_page)
        return {
            "configured": True,
            "posts": [_format_wp_post(p) for p in posts],
        }
    except Exception as e:
        logger.error(f"Failed to fetch WordPress posts: {e}")
        return {"configured": True, "posts": [], "error": str(e)}


@router.get("/wordpress/posts/{post_id}")
async def wordpress_post_detail(post_id: int):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    try:
        post = await wp.get_post(post_id)
        return {"configured": True, "post": _format_wp_post(post)}
    except Exception as e:
        logger.error(f"Failed to fetch WordPress post: {e}")
        return {"configured": True, "error": str(e)}


class CreatePostRequest(BaseModel):
    title: str
    content: str
    status: str = "draft"
    categories: list[str] | None = None
    tags: list[str] | None = None
    excerpt: str = ""
    featured_media: int | None = None
    privacy_level: str = "public"
    post_password: str = ""


@router.post("/wordpress/posts")
async def wordpress_create_post(req: CreatePostRequest):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    try:
        cat_ids = None
        tag_ids = None
        if req.categories:
            cat_ids = await wp.get_or_create_categories(req.categories)
        if req.tags:
            tag_ids = await wp.get_or_create_tags(req.tags)

        post = await wp.create_post(
            title=req.title,
            content=req.content,
            status=req.status,
            categories=cat_ids,
            tags=tag_ids,
            featured_media=req.featured_media,
            excerpt=req.excerpt,
            privacy_level=req.privacy_level,
            post_password=req.post_password,
        )
        return {"configured": True, "post": _format_wp_post(post)}
    except Exception as e:
        logger.error(f"Failed to create WordPress post: {e}")
        return {"configured": True, "error": str(e)}


class UpdatePostRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    excerpt: str | None = None
    privacy_level: str | None = None
    post_password: str | None = None


@router.put("/wordpress/posts/{post_id}")
async def wordpress_update_post(post_id: int, req: UpdatePostRequest):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    try:
        fields: dict = {}
        if req.title is not None:
            fields["title"] = req.title
        if req.content is not None:
            fields["content"] = req.content
        if req.status is not None:
            fields["status"] = req.status
        if req.excerpt is not None:
            fields["excerpt"] = req.excerpt
        if req.categories is not None:
            fields["categories"] = await wp.get_or_create_categories(req.categories)
        if req.tags is not None:
            fields["tags"] = await wp.get_or_create_tags(req.tags)
        if req.privacy_level is not None:
            fields["privacy_level"] = req.privacy_level
        if req.post_password is not None:
            fields["post_password"] = req.post_password

        post = await wp.update_post(post_id, **fields)
        return {"configured": True, "post": _format_wp_post(post)}
    except Exception as e:
        logger.error(f"Failed to update WordPress post: {e}")
        return {"configured": True, "error": str(e)}


@router.delete("/wordpress/posts/{post_id}")
async def wordpress_delete_post(post_id: int):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    try:
        await wp.delete_post(post_id)
        return {"configured": True, "deleted": True}
    except Exception as e:
        logger.error(f"Failed to delete WordPress post: {e}")
        return {"configured": True, "deleted": False, "error": str(e)}


@router.get("/wordpress/media/check")
async def wordpress_media_check():
    """Diagnostic: test XML-RPC auth and upload capability."""
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    results: dict = {
        "configured": True,
        "username": settings.wordpress_username,
        "xmlrpc_url": f"{settings.wordpress_url}/xmlrpc.php",
    }

    # Test XML-RPC reachability
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.wordpress_url}/xmlrpc.php",
                timeout=10.0,
            )
            results["xmlrpc_reachable"] = resp.status_code != 404
    except Exception as e:
        results["xmlrpc_reachable"] = False
        results["xmlrpc_error"] = str(e)

    # Test XML-RPC auth (tries with and without spaces)
    results["xmlrpc_auth"] = await wp.check_xmlrpc()

    # Test XML-RPC media upload with tiny 1x1 PNG
    try:
        tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        media = await wp.upload_media(
            filename="diag-test.png",
            data=tiny_png,
            content_type="image/png",
        )
        media_id = media.get("id")
        results["test_upload"] = {"ok": True, "media_id": media_id}

        # Clean up
        if media_id:
            try:
                await wp.delete_post(media_id)
            except Exception:
                pass
    except Exception as e:
        results["test_upload"] = {"ok": False, "error": str(e)}

    return results


@router.post("/wordpress/media")
async def wordpress_upload_media(
    file: UploadFile = File(...),
    alt_text: str = Form(""),
):
    wp = WordPressService()
    if not wp.is_configured:
        return {"configured": False}

    try:
        raw = await file.read()
        processed, filename = wp._process_image(raw)
        media = await wp.upload_media(
            filename=filename,
            data=processed,
            content_type="image/webp",
            alt_text=alt_text,
        )

        return {
            "configured": True,
            "media": {
                "id": media.get("id"),
                "url": media.get("source_url", ""),
            },
        }
    except Exception as e:
        logger.error(f"Failed to upload WordPress media: {e}")
        return {"configured": True, "error": str(e)}

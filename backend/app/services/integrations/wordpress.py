"""WordPress integration — REST API for reads, XML-RPC for authenticated writes.

Many WordPress hosting setups (Apache CGI/FastCGI) strip the HTTP Authorization
header before it reaches PHP, breaking REST API auth.  XML-RPC sends credentials
inside the request body, bypassing this entirely.  We use:

- REST API (unauthenticated) for public reads: list published posts, categories, tags
- XML-RPC for anything requiring auth: create/update/delete posts, upload media
"""

import asyncio
import base64
import io
import logging
import xmlrpc.client
from typing import Any

import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 100_000  # 100 KB


class WordPressService:
    """WordPress client — REST API for reads, XML-RPC for authenticated writes."""

    def __init__(self) -> None:
        self._url = settings.wordpress_url.rstrip("/")
        self._username = settings.wordpress_username
        self._app_password = settings.wordpress_app_password

    @property
    def is_configured(self) -> bool:
        return bool(self._url and self._username and self._app_password)

    def _base(self) -> str:
        return f"{self._url}/wp-json/wp/v2"

    def _headers(self) -> dict[str, str]:
        if not self.is_configured:
            raise ValueError(
                "WordPress not configured. Set ASSISTANT_WORDPRESS_URL, "
                "ASSISTANT_WORDPRESS_USERNAME, and ASSISTANT_WORDPRESS_APP_PASSWORD."
            )
        token = base64.b64encode(
            f"{self._username}:{self._app_password}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}

    def _xmlrpc(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(
            f"{self._url}/xmlrpc.php", use_datetime=True
        )

    def _xmlrpc_call(self, method: str, *args: Any) -> Any:
        """Synchronous XML-RPC call (run via asyncio.to_thread)."""
        proxy = self._xmlrpc()
        func = getattr(proxy, method)
        return func(*args)

    async def _call(self, method: str, *args: Any) -> Any:
        """Async wrapper for XML-RPC calls."""
        return await asyncio.to_thread(self._xmlrpc_call, method, *args)

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    async def list_posts(
        self,
        status: str = "any",
        per_page: int = 10,
    ) -> list[dict[str, Any]]:
        """List posts via XML-RPC (supports draft/pending with auth)."""
        filter_args: dict[str, Any] = {"number": per_page, "orderby": "post_date"}
        if status != "any":
            filter_args["post_status"] = status

        try:
            posts = await self._call(
                "wp.getPosts",
                0,
                self._username,
                self._app_password,
                filter_args,
            )
        except xmlrpc.client.Fault as e:
            logger.error("XML-RPC wp.getPosts failed: %s", e)
            # Fallback: try REST API for public posts only
            return await self._list_posts_rest(per_page)

        results: list[dict[str, Any]] = []
        for p in posts:
            if status == "any" or p.get("post_status") == status:
                results.append(self._xmlrpc_post_to_rest(p))
        return results

    async def _list_posts_rest(self, per_page: int = 10) -> list[dict[str, Any]]:
        """Fallback: list published posts via REST (no auth needed)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base()}/posts",
                params={"per_page": per_page, "status": "publish"},
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_post(self, post_id: int) -> dict[str, Any]:
        try:
            post = await self._call(
                "wp.getPost",
                0,
                self._username,
                self._app_password,
                post_id,
            )
            return self._xmlrpc_post_to_rest(post)
        except xmlrpc.client.Fault:
            # Fallback: REST (works for published posts)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base()}/posts/{post_id}",
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()

    async def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        featured_media: int | None = None,
        excerpt: str = "",
        privacy_level: str = "public",
        post_password: str = "",
    ) -> dict[str, Any]:
        post_data: dict[str, Any] = {
            "post_title": title,
            "post_content": content,
            "post_status": status,
        }
        if excerpt:
            post_data["post_excerpt"] = excerpt
        if featured_media:
            post_data["post_thumbnail"] = featured_media
        if categories:
            post_data["terms"] = post_data.get("terms", {})
            post_data["terms"]["category"] = categories
        if tags:
            post_data["terms"] = post_data.get("terms", {})
            post_data["terms"]["post_tag"] = tags
        post_data["custom_fields"] = [
            {"key": "_privacy_level", "value": privacy_level},
            {"key": "_custom_password", "value": post_password},
        ]

        post_id = await self._call(
            "wp.newPost",
            0,
            self._username,
            self._app_password,
            post_data,
        )
        # wp.newPost returns the new post ID as a string
        return await self.get_post(int(post_id))

    async def update_post(self, post_id: int, **fields: Any) -> dict[str, Any]:
        post_data: dict[str, Any] = {}
        if "title" in fields:
            post_data["post_title"] = fields["title"]
        if "content" in fields:
            post_data["post_content"] = fields["content"]
        if "status" in fields:
            post_data["post_status"] = fields["status"]
        if "excerpt" in fields:
            post_data["post_excerpt"] = fields["excerpt"]
        if "categories" in fields:
            post_data["terms"] = post_data.get("terms", {})
            post_data["terms"]["category"] = fields["categories"]
        if "tags" in fields:
            post_data["terms"] = post_data.get("terms", {})
            post_data["terms"]["post_tag"] = fields["tags"]
        if "privacy_level" in fields or "post_password" in fields:
            post_data["custom_fields"] = []
            if "privacy_level" in fields:
                post_data["custom_fields"].append(
                    {"key": "_privacy_level", "value": fields["privacy_level"]}
                )
            if "post_password" in fields:
                post_data["custom_fields"].append(
                    {"key": "_custom_password", "value": fields["post_password"]}
                )

        await self._call(
            "wp.editPost",
            0,
            self._username,
            self._app_password,
            post_id,
            post_data,
        )
        return await self.get_post(post_id)

    async def delete_post(self, post_id: int) -> dict[str, Any]:
        result = await self._call(
            "wp.deletePost",
            0,
            self._username,
            self._app_password,
            post_id,
        )
        return {"deleted": bool(result)}

    @staticmethod
    def _xmlrpc_post_to_rest(p: dict) -> dict[str, Any]:
        """Convert XML-RPC post dict to the REST-API-like shape the frontend expects."""
        terms = p.get("terms", [])
        cat_ids = [t["term_id"] for t in terms if t.get("taxonomy") == "category"]
        tag_ids = [t["term_id"] for t in terms if t.get("taxonomy") == "post_tag"]

        # Extract custom privacy meta
        custom_fields = p.get("custom_fields", [])
        privacy_level = "public"
        for cf in custom_fields:
            if cf.get("key") == "_privacy_level" and cf.get("value"):
                privacy_level = cf["value"]
                break

        return {
            "id": int(p.get("post_id", 0)),
            "title": {"rendered": p.get("post_title", "")},
            "status": p.get("post_status", ""),
            "date": (
                p["post_date_gmt"].isoformat()
                if hasattr(p.get("post_date_gmt"), "isoformat")
                else str(p.get("post_date_gmt", ""))
            ),
            "link": p.get("link", ""),
            "excerpt": {"rendered": p.get("post_excerpt", "")},
            "content": {"rendered": p.get("post_content", "")},
            "tags": tag_ids,
            "categories": cat_ids,
            "privacy_level": privacy_level,
        }

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    async def upload_media(
        self,
        filename: str,
        data: bytes,
        content_type: str,
        alt_text: str = "",
    ) -> dict[str, Any]:
        """Upload media via XML-RPC (bypasses Authorization header stripping)."""
        media_data: dict[str, Any] = {
            "name": filename,
            "type": content_type,
            "bits": xmlrpc.client.Binary(data),
            "overwrite": True,
        }

        result = await self._call(
            "wp.uploadFile",
            0,
            self._username,
            self._app_password,
            media_data,
        )
        # result = {'id': '123', 'file': 'image.webp', 'url': '...', 'type': '...'}
        return {
            "id": int(result.get("id", 0)),
            "source_url": result.get("url", ""),
        }

    async def list_media(self, per_page: int = 10) -> list[dict[str, Any]]:
        """List media (public REST endpoint, no auth needed)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base()}/media",
                params={"per_page": per_page},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Image processing
    # ------------------------------------------------------------------

    def _process_image(self, data: bytes) -> tuple[bytes, str]:
        """Convert image to WebP, resizing until under 100 KB."""
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        quality = 80
        for _ in range(10):
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=quality)
            webp_bytes = buf.getvalue()
            if len(webp_bytes) <= MAX_IMAGE_BYTES:
                return webp_bytes, "image.webp"
            # Reduce dimensions by 75%
            new_w = int(img.width * 0.75)
            new_h = int(img.height * 0.75)
            if new_w < 10 or new_h < 10:
                break
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # Return whatever we have
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=60)
        return buf.getvalue(), "image.webp"

    # ------------------------------------------------------------------
    # Tags & Categories (public REST reads + XML-RPC for creates)
    # ------------------------------------------------------------------

    async def list_tags(
        self, search: str = "", per_page: int = 100
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"per_page": per_page}
        if search:
            params["search"] = search
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base()}/tags",
                params=params,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_categories(self, per_page: int = 100) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base()}/categories",
                params={"per_page": per_page},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_or_create_tags(self, names: list[str]) -> list[int]:
        """Resolve tag names to IDs, creating via XML-RPC if needed."""
        ids: list[int] = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            existing = await self.list_tags(search=name, per_page=10)
            found = next(
                (t for t in existing if t.get("name", "").lower() == name.lower()),
                None,
            )
            if found:
                ids.append(found["id"])
            else:
                # Create via XML-RPC
                term_id = await self._call(
                    "wp.newTerm",
                    0,
                    self._username,
                    self._app_password,
                    {"taxonomy": "post_tag", "name": name},
                )
                ids.append(int(term_id))
        return ids

    async def get_or_create_categories(self, names: list[str]) -> list[int]:
        """Resolve category names to IDs, creating via XML-RPC if needed."""
        all_cats = await self.list_categories()
        cat_map = {c["name"].lower(): c["id"] for c in all_cats}

        ids: list[int] = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            if name.lower() in cat_map:
                ids.append(cat_map[name.lower()])
            else:
                term_id = await self._call(
                    "wp.newTerm",
                    0,
                    self._username,
                    self._app_password,
                    {"taxonomy": "category", "name": name},
                )
                new_id = int(term_id)
                ids.append(new_id)
                cat_map[name.lower()] = new_id
        return ids

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    async def check_xmlrpc(self) -> dict[str, Any]:
        """Test XML-RPC connectivity and auth (tries with and without spaces)."""
        passwords_to_try = [
            ("as-is", self._app_password),
            ("no-spaces", self._app_password.replace(" ", "")),
        ]

        for label, password in passwords_to_try:
            try:
                profile = await self._call(
                    "wp.getProfile",
                    0,
                    self._username,
                    password,
                )
                # If this worked and it was no-spaces, update to use that
                if label == "no-spaces" and password != self._app_password:
                    logger.info("WordPress: app password works without spaces")
                return {
                    "ok": True,
                    "password_format": label,
                    "username": profile.get("username", ""),
                    "display_name": profile.get("display_name", ""),
                }
            except xmlrpc.client.Fault as e:
                if e.faultCode == 403:
                    continue  # try next format
                return {"ok": False, "fault_code": e.faultCode, "fault_string": e.faultString}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        return {
            "ok": False,
            "fault_code": 403,
            "fault_string": "Incorrect username or password (tried with and without spaces)",
            "hint": "Verify: WP Admin → Users → ai-assistant → Application Passwords. "
                    "Generate a new one if needed. Also check that XML-RPC is not "
                    "blocked by a security plugin.",
        }

"""MCP server (FastMCP "blog-agent"): thin wrappers over the blog_manager tools.

Run: python -m blog_manager.mcp_server  (stdio). Procedures live in skills/
(publish-post, delete-post, cleanup-blog); rules in AGENTS.md. stdout is
reserved for protocol traffic; logs go to stderr.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# paths.py resolves config.yaml and blog paths from the repo root, not cwd.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .cleanup_tool import execute_cleanup as _execute_cleanup
from .cleanup_tool import find_unused_assets as _find_unused_assets
from .delete_post_tool import delete_files as _delete_files
from .delete_post_tool import find_files_to_delete as _find_files_to_delete
from .notion_export import notion_fetch as _notion_fetch
from .post_validate import post_validate as _post_validate
from .post_writer import post_write as _post_write
from .taxonomy import taxonomy_ensure as _taxonomy_ensure

SERVER_INSTRUCTIONS = """\
Tools for the wholmesian Jekyll blog (Notion -> Jekyll). Follow the skills \
`publish-post`, `delete-post` and `cleanup-blog` for step-by-step procedures \
and AGENTS.md for formatting rules. Never delete anything (confirm=true) \
without explicit user confirmation, and never create categories or projects.
"""

mcp = FastMCP("blog-agent", instructions=SERVER_INSTRUCTIONS)


@mcp.tool()
def notion_fetch(page_id_or_url: str, slug: str | None = None, config_path: str | None = None) -> dict:
    """Fetch a Notion page (properties, blocks, downloaded images, markdown draft). See skill `publish-post`."""
    return _notion_fetch(page_id_or_url, slug=slug, config_path=config_path)


@mcp.tool()
def post_write(slug: str, date: str, content: str | None = None, content_file: str | None = None,
               overwrite: bool = False, config_path: str | None = None) -> dict:
    """Save finished post markdown as _posts/YYYY-MM-DD-slug.md. Pass exactly one of content/content_file. See skill `publish-post`."""
    return _post_write(slug, date, content=content, content_file=content_file,
                       overwrite=overwrite, config_path=config_path)


@mcp.tool()
def taxonomy_ensure(tags: list[dict] | None = None, series: list[dict] | None = None,
                    config_path: str | None = None) -> dict:
    """Create missing tag/series pages and tag_slugs.yml entries. Items: {"taxonomy": "...", "english_title": "..."}. See skill `publish-post`."""
    return _taxonomy_ensure(tags=tags, series=series, config_path=config_path)


@mcp.tool()
def post_validate(file_path: str, config_path: str | None = None) -> dict:
    """Validate a post file against the AGENTS.md rules. Read-only. See skill `publish-post`."""
    return _post_validate(file_path, config_path=config_path)


@mcp.tool()
def find_files_to_delete(title: str, config_path: str | None = None) -> dict:
    """Locate a post and its images by exact title. Read-only. See skill `delete-post`."""
    return _find_files_to_delete(title, config_path=config_path)


@mcp.tool()
def delete_files(files_to_delete: list[str], confirm: bool = False, config_path: str | None = None) -> dict:
    """Delete files found by find_files_to_delete. Dry-run unless confirm=true; set confirm=true ONLY after the user explicitly confirmed this exact list. See skill `delete-post`."""
    return _delete_files(files_to_delete, confirm=confirm, config_path=config_path)


@mcp.tool()
def find_unused_assets(config_path: str | None = None) -> dict:
    """List unused tag/series/project pages and images. Read-only. See skill `cleanup-blog`."""
    return _find_unused_assets(config_path=config_path)


@mcp.tool()
def execute_cleanup(files_to_delete: list[str], confirm: bool = False, config_path: str | None = None) -> dict:
    """Delete unused files the user selected. Dry-run unless confirm=true; set confirm=true ONLY after the user explicitly confirmed the selection. See skill `cleanup-blog`."""
    return _execute_cleanup(files_to_delete, confirm=confirm, config_path=config_path)


def main() -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run()


if __name__ == "__main__":
    main()

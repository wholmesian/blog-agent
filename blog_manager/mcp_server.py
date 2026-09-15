"""MCP (Model Context Protocol) server for the blog-agent tools.

This exposes the same five tools that the Google ADK agent (`agent.py`) uses,
but over the Model Context Protocol instead of ADK, so the agent can be used
from any MCP-compatible host -- Google Antigravity, Claude Desktop, Claude
Code, etc. -- instead of only through `adk run` / `adk web`.

Run it directly for a quick manual check:

    python -m blog_manager.mcp_server

Or point an MCP host at it (see README.md for Antigravity / Claude Desktop
config examples). Hosts spawn this as a subprocess and talk to it over
stdio, so it must not print anything to stdout other than protocol
messages -- all the tool implementations below already log with `print()`
to stdout inside blog_manager's tool modules, so we redirect that internal
chatter to stderr before the MCP server (and therefore stdout) is used for
protocol traffic.
"""

import contextlib
import io
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# All of the underlying tool implementations (notion_to_jekyll_tool.py,
# delete_post_tool.py, cleanup_tool.py) assume they're being run with the
# repository root (this file's parent directory) as the current working
# directory -- that's where config.yaml lives, and config.yaml's own paths
# (e.g. "../wholmesian.github.io/_posts") are relative to that same
# directory. `adk run` / `adk web` satisfy this because you `cd` into the
# repo before launching them. An MCP host, however, spawns this server with
# an arbitrary (often unrelated) working directory, so we pin it here,
# once, before importing the tool modules or loading .env.
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
load_dotenv(os.path.join(REPO_ROOT, ".env"))

from .cleanup_tool import execute_cleanup as _execute_cleanup
from .cleanup_tool import find_unused_assets as _find_unused_assets
from .delete_post_tool import delete_files as _delete_files
from .delete_post_tool import find_files_to_delete as _find_files_to_delete
from .notion_to_jekyll_tool import convert_notion_to_jekyll as _convert_notion_to_jekyll

SERVER_INSTRUCTIONS = """\
You have access to tools for managing a Jekyll blog (wholmesian.github.io) \
that is normally fed from Notion.

- To publish a Notion page as a blog post, call `convert_notion_to_jekyll` \
with the Notion page ID or URL. Do not hand-write the markdown yourself; \
rely entirely on the tool's output.
- To delete a post: first call `find_files_to_delete` with the post's exact \
title, show the user the markdown and image files it found, and only call \
`delete_files` after the user explicitly confirms.
- To clean up unused assets (tags, series, projects, images): first call \
`find_unused_assets`, present the categorized results as a numbered list, \
ask the user which items to remove (all / none / specific numbers), and \
call `execute_cleanup` with only the files the user selected. Do not use \
`delete_files` for this -- `execute_cleanup` also syncs `tag_slugs.yml`.
"""

mcp = FastMCP("blog-agent", instructions=SERVER_INSTRUCTIONS)


@contextlib.contextmanager
def _stdout_to_stderr():
    """Redirect the tool modules' own print() logging to stderr.

    Tool calls happen after the MCP server has taken over stdio for JSON-RPC
    traffic, so anything the underlying functions print() to stdout (they do
    a fair bit, e.g. "Fetching Notion page: ...") would corrupt the protocol
    stream. The tools return their real result as a value either way, so we
    just relocate the incidental prints, not any information the caller
    needs.
    """
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout


@mcp.tool()
def convert_notion_to_jekyll(page_id: str, config_path: str = "config.yaml") -> str:
    """Convert a Notion page into a Jekyll markdown blog post.

    Parses the given Notion page's properties and content blocks, downloads
    any embedded images, generates frontmatter and body markdown via Gemini,
    saves the result under the configured posts directory, and creates any
    new tag/series pages it discovers along the way.

    Args:
        page_id: The Notion page ID or URL to convert.
        config_path: Path to config.yaml (defaults to the repo's own).

    Returns:
        A message describing success (with the saved file path) or failure.
    """
    with _stdout_to_stderr():
        return _convert_notion_to_jekyll(page_id, config_path)


@mcp.tool()
def find_files_to_delete(title: str, config_path: str = "config.yaml") -> dict:
    """Find the markdown post and associated images for a given post title.

    This is step 1 of the two-step delete flow: it only locates files, it
    never deletes anything. Present the results to the user and get explicit
    confirmation before calling `delete_files`.

    Args:
        title: The exact post title, as it appears in the frontmatter.
        config_path: Path to config.yaml (defaults to the repo's own).

    Returns:
        A dict with 'post_files' and 'image_files' lists, or an 'error' key.
    """
    with _stdout_to_stderr():
        return _find_files_to_delete(title, config_path)


@mcp.tool()
def delete_files(files_to_delete: list[str]) -> str:
    """Delete the given files from disk (and clean up any now-empty dirs).

    Only call this with a file list that came from `find_files_to_delete`
    and that the user has explicitly confirmed should be deleted.

    Args:
        files_to_delete: Absolute or relative paths of files to delete.

    Returns:
        A message with the count of files deleted.
    """
    with _stdout_to_stderr():
        return _delete_files(files_to_delete)


@mcp.tool()
def find_unused_assets(config_path: str = "config.yaml") -> dict:
    """Scan the blog repo for tags, series, projects and images that no
    published post currently references.

    This only scans and reports; nothing is deleted. Present the findings to
    the user (they may want to keep some) before calling `execute_cleanup`
    with just the items they select.

    Args:
        config_path: Path to config.yaml (defaults to the repo's own).

    Returns:
        A dict of unused file paths keyed by 'tags', 'series', 'projects',
        'posts_img', and 'projects_img'.
    """
    with _stdout_to_stderr():
        return _find_unused_assets(config_path)


@mcp.tool()
def execute_cleanup(files_to_delete: list[str], config_path: str = "config.yaml") -> str:
    """Delete the given (previously found-unused) files, syncing
    `_data/tag_slugs.yml` if any tag pages are among them.

    Only call this with files the user explicitly selected from the output
    of `find_unused_assets`. Do not use `delete_files` for this workflow.

    Args:
        files_to_delete: Absolute paths of files to delete.
        config_path: Path to config.yaml (defaults to the repo's own).

    Returns:
        A message with the count of files deleted.
    """
    with _stdout_to_stderr():
        return _execute_cleanup(files_to_delete, config_path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

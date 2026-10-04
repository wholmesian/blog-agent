import asyncio

from blog_manager.mcp_server import mcp

EXPECTED = {"notion_fetch", "post_write", "taxonomy_ensure", "post_validate",
            "find_files_to_delete", "delete_files", "find_unused_assets", "execute_cleanup"}


def test_tool_registry():
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED


def test_confirm_param_defaults_false():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name in ("delete_files", "execute_cleanup"):
        assert tools[name].inputSchema["properties"]["confirm"]["default"] is False
    assert "skill" in tools["delete_files"].description


def test_delete_via_mcp_is_dry_run_by_default(blog):
    target = blog / "assets/images/posts_img/2026-04-25/pic.png"
    asyncio.run(mcp.call_tool("delete_files", {"files_to_delete": [str(target)]}))
    assert target.exists()

"""Command line interface: `python -m blog_manager <command>`.

stdout is always exactly one JSON document; logs go to stderr.
Exit codes: 0 ok, 1 tool reported failure, 2 usage error.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(2)


def _pairs(values, flag):
    out = []
    for v in values or []:
        tax, sep, eng = v.partition("=")
        if not sep or not tax.strip() or not eng.strip():
            raise ValueError(f"{flag} expects TAXONOMY=english_title, got {v!r}")
        out.append({"taxonomy": tax.strip(), "english_title": eng.strip()})
    return out


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="python -m blog_manager", description="Blog tools (JSON output).")
    p.add_argument("--config", default=None, help="path to config.yaml")
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)

    s = sub.add_parser("notion-fetch", help="fetch a Notion page")
    s.add_argument("id_or_url")
    s.add_argument("--slug")

    s = sub.add_parser("post-write", help="write a post into _posts")
    s.add_argument("--slug", required=True)
    s.add_argument("--date", required=True, help="YYYY-MM-DD")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--stdin", action="store_true")
    s.add_argument("--overwrite", action="store_true")

    s = sub.add_parser("taxonomy-ensure", help="create missing tag/series pages")
    s.add_argument("--tag", action="append", default=[], metavar="TAXONOMY=english_title")
    s.add_argument("--series", action="append", default=[], metavar="TAXONOMY=english_title")

    s = sub.add_parser("post-validate", help="validate a post file")
    s.add_argument("file")

    s = sub.add_parser("find-files-to-delete", help="find files of a post by title")
    s.add_argument("title")

    s = sub.add_parser("delete-files", help="delete files (dry-run unless --yes)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--yes", action="store_true")

    sub.add_parser("find-unused-assets", help="list unused tags/series/projects/images")

    s = sub.add_parser("execute-cleanup", help="delete unused files (dry-run unless --yes)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--yes", action="store_true")
    return p


def _dispatch(a):
    cfg = a.config
    c = a.command
    if c == "notion-fetch":
        from .notion_export import notion_fetch
        return notion_fetch(a.id_or_url, slug=a.slug, config_path=cfg)
    if c == "post-write":
        from .post_writer import post_write
        if a.stdin:
            return post_write(a.slug, a.date, content=sys.stdin.read(),
                              overwrite=a.overwrite, config_path=cfg)
        return post_write(a.slug, a.date, content_file=a.file,
                          overwrite=a.overwrite, config_path=cfg)
    if c == "taxonomy-ensure":
        from .taxonomy import taxonomy_ensure
        return taxonomy_ensure(tags=_pairs(a.tag, "--tag"), series=_pairs(a.series, "--series"),
                               config_path=cfg)
    if c == "post-validate":
        from .post_validate import post_validate
        return post_validate(a.file, config_path=cfg)
    if c == "find-files-to-delete":
        from .delete_post_tool import find_files_to_delete
        return find_files_to_delete(a.title, config_path=cfg)
    if c == "delete-files":
        from .delete_post_tool import delete_files
        return delete_files(a.paths, confirm=a.yes, config_path=cfg)
    if c == "find-unused-assets":
        from .cleanup_tool import find_unused_assets
        return find_unused_assets(config_path=cfg)
    if c == "execute-cleanup":
        from .cleanup_tool import execute_cleanup
        return execute_cleanup(a.paths, confirm=a.yes, config_path=cfg)
    raise ValueError(f"unknown command {c}")


def _exit_code(result) -> int:
    if isinstance(result, dict):
        if "ok" in result:
            return 0 if result["ok"] else 1
        return 1 if result.get("error") else 0
    return 0


def main(argv=None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    load_dotenv(REPO_ROOT / ".env")
    try:
        result = _dispatch(args)
    except ValueError as e:
        print(f"usage error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # keep stdout JSON-only
        logging.getLogger(__name__).exception("command failed")
        result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")
    sys.stdout.flush()
    return _exit_code(result)


if __name__ == "__main__":
    sys.exit(main())

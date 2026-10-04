"""작성된 마크다운을 _posts/YYYY-MM-DD-slug.md 로 저장합니다."""
import re
from datetime import datetime
from pathlib import Path

from .paths import BlogPaths

_SLUG_RE = re.compile(r"^[A-Za-z0-9-]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def post_write(slug: str, date: str, content: str = None, content_file: str = None,
               overwrite: bool = False, config_path: str = None) -> dict:
    try:
        if not isinstance(slug, str) or not _SLUG_RE.match(slug):
            return {"ok": False, "error": f"Invalid slug {slug!r}: only A-Z a-z 0-9 and '-' allowed."}
        if not isinstance(date, str) or not _DATE_RE.match(date):
            return {"ok": False, "error": f"Invalid date {date!r}: expected YYYY-MM-DD."}
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"ok": False, "error": f"Invalid calendar date {date!r}."}
        if (content is None) == (content_file is None):
            return {"ok": False, "error": "Provide exactly one of content or content_file."}
        if content_file is not None:
            src = Path(content_file).expanduser()
            if not src.is_file():
                return {"ok": False, "error": f"content_file not found: {content_file}"}
            content = src.read_text(encoding="utf-8")
        if not content.strip():
            return {"ok": False, "error": "Content is empty."}

        posts_dir = BlogPaths(config_path).posts_dir.resolve()
        target = (posts_dir / f"{date}-{slug}.md").resolve()
        if target.parent != posts_dir:
            return {"ok": False, "error": "Resolved path escapes the posts directory."}
        existed = target.exists()
        if existed and not overwrite:
            return {"ok": False, "error": f"File already exists: {target}. Pass overwrite=True to replace it.",
                    "path": str(target)}
        posts_dir.mkdir(parents=True, exist_ok=True)
        if not content.endswith("\n"):
            content += "\n"
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(target), "overwritten": existed,
                "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}

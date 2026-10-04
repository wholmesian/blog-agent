"""Notion 페이지 -> (프로퍼티, 블록, 이미지, 마크다운 초안) 추출. LLM 호출 없음."""
import logging
import re
from datetime import datetime

from .image_handler import ImageHandler
from .notion_markdown import blocks_to_markdown, rich_text_plain
from .notion_parser import NotionParser
from .paths import BlogPaths

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"([0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12})$")
SLUG_RE = re.compile(r"^[A-Za-z0-9-]+$")


def extract_page_id(page_id_or_url: str) -> str:
    """Notion URL/ID 문자열에서 페이지 ID를 뽑습니다. 실패 시 ValueError."""
    raw = (page_id_or_url or "").strip().split("?")[0].split("#")[0].rstrip("/")
    m = _ID_RE.search(raw)
    if not m:
        raise ValueError(f"Cannot extract a Notion page id from: {page_id_or_url!r}")
    return m.group(1).replace("-", "")


def process_blocks_for_images(blocks, image_handler, category, date_str="", title="",
                              download=True, collected=None):
    """이미지 블록을 재귀 순회하며 다운로드 후 URL을 웹루트 경로로 교체합니다.
    캡션은 블록 데이터(image.caption)에 그대로 남습니다. 수집된 이미지 정보 리스트를 반환."""
    if collected is None:
        collected = []
    for block in blocks:
        if block.get("type") == "image":
            data = block.get("image", {})
            kind = "file" if "file" in data else ("external" if "external" in data else None)
            if kind:
                url = data[kind]["url"]
                entry = {"block_id": block.get("id"), "original_url": url,
                         "caption": rich_text_plain(data.get("caption")),
                         "web_path": None, "downloaded": False}
                if download:
                    try:
                        web_path = image_handler.download_image(url, category, date_str, title)
                        entry["web_path"] = web_path
                        entry["downloaded"] = web_path != url
                        if entry["downloaded"]:
                            data[kind]["url"] = web_path
                    except Exception as e:  # 네트워크/파일시스템 오류는 항목별로 보고
                        logger.warning("Image download failed: %s", e)
                        entry["error"] = str(e)
                collected.append(entry)
        if block.get("children"):
            process_blocks_for_images(block["children"], image_handler, category, date_str,
                                      title, download, collected)
    return collected


def _first(properties, keys, pred=None):
    for k in keys:
        if k in properties and properties[k]:
            return properties[k]
    if pred:
        for k, v in properties.items():
            if pred(k) and v:
                return v
    return None


def _slug_from_title(title: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
    return s


def notion_fetch(page_id_or_url: str, slug: str = None, config_path: str = None) -> dict:
    try:
        page_id = extract_page_id(page_id_or_url)
        parser = NotionParser()
        page = parser.get_page(page_id)
        properties = parser.extract_properties(page)
        blocks = parser.get_blocks(page_id)

        category = "default"
        cat = _first(properties, ["category", "Category", "카테고리"],
                     lambda k: "categor" in k.lower() or "카테고리" in k)
        if isinstance(cat, list) and cat:
            category_name = cat[0]
        elif isinstance(cat, str):
            category_name = cat
        else:
            category_name = None

        def date10(v):
            return str(v)[:10] if v else ""
        upload = date10(_first(properties, ["upload_date", "date"],
                               lambda k: "date" in k.lower() or "날짜" in k))
        modified = date10(_first(properties, ["modified_date"])) or upload
        if not upload:
            upload = datetime.now().strftime("%Y-%m-%d")
        title = properties.get("title") or properties.get("Name") or "Untitled"

        base = {"ok": True, "page_id": page_id, "properties": properties, "title": title,
                "category": category_name, "upload_date": upload, "modified_date": modified}

        if slug is not None:
            slug = slug.strip()
            if not SLUG_RE.match(slug):
                return {"ok": False, "error": f"Invalid slug {slug!r}: use only A-Z a-z 0-9 and '-'."}
        elif title.isascii():
            slug = _slug_from_title(title) or "untitled"
        else:
            base.update({"slug_required": True, "slug": None, "blocks": blocks, "images": [],
                         "suggested_filename": None, "markdown_draft": None,
                         "message": "Title is non-ASCII; call again with an English slug. "
                                    "Images were not downloaded."})
            return base

        paths = BlogPaths(config_path)
        image_handler = ImageHandler(config_path=config_path)
        images = process_blocks_for_images(blocks, image_handler, category, upload, slug)
        base.update({"slug_required": False, "slug": slug, "blocks": blocks, "images": images,
                     "suggested_filename": f"{upload}-{slug}.md",
                     "posts_dir": str(paths.posts_dir),
                     "markdown_draft": blocks_to_markdown(blocks)})
        return base
    except Exception as e:
        logger.exception("notion_fetch failed")
        return {"ok": False, "error": str(e)}

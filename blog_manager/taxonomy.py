"""없는 태그/시리즈 페이지를 생성하고 tag_slugs.yml을 갱신합니다 (카테고리/프로젝트는 건드리지 않음)."""
import json
import logging
import re

import yaml

from .paths import BlogPaths

logger = logging.getLogger(__name__)

TAG_TEMPLATE = ('---\ntitle: "{title}"\nlayout: tag\npermalink: /tags/{slug}/\n'
                'author_profile: true\ntaxonomy: {taxonomy}\nsidebar:\n  nav: "categories"\n---\n')
SERIES_TEMPLATE = ('---\ntitle: "{title}"\nlayout: series\npermalink: /series/{slug}/\n'
                   'author_profile: true\ntaxonomy: {taxonomy}\nsidebar:\n  nav: "categories"\n---\n')


def safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text.lower()).strip("-")


def read_frontmatter(path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def collect_taxonomies(directory) -> dict:
    """디렉토리 내 페이지의 {taxonomy: path}."""
    out = {}
    if directory.is_dir():
        for f in sorted(directory.glob("*.md")):
            tax = read_frontmatter(f).get("taxonomy")
            if tax is not None:
                out[str(tax)] = f
    return out


def load_tag_slugs(paths: BlogPaths) -> dict:
    f = paths.tag_slugs_file
    if not f.exists():
        return {}
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return {str(k): v for k, v in data.items()} if isinstance(data, dict) else {}


def _yaml_scalar(s: str) -> str:
    if re.fullmatch(r"[\w가-힣][\w가-힣 .\-]*", s) and not s.strip().isdigit():
        return s
    return json.dumps(s, ensure_ascii=False)


def _append_slug(paths: BlogPaths, taxonomy: str, eng: str):
    f = paths.tag_slugs_file
    f.parent.mkdir(parents=True, exist_ok=True)
    content = f.read_text(encoding="utf-8") if f.exists() else ""
    with open(f, "a", encoding="utf-8") as fh:
        if content and not content.endswith("\n"):
            fh.write("\n")
        fh.write(f"{_yaml_scalar(taxonomy)}: {_yaml_scalar(eng)}\n")


def _norm(items):
    out = []
    for it in items or []:
        if isinstance(it, str):
            it = {"taxonomy": it}
        tax = str(it.get("taxonomy", "")).strip()
        eng = str(it.get("english_title") or tax).strip()
        out.append((tax, eng))
    return out


def taxonomy_ensure(tags=None, series=None, config_path: str = None) -> dict:
    try:
        paths = BlogPaths(config_path)
        created, skipped, errors, slugs_added = [], [], [], []

        def process(kind, items, directory, template, prefix):
            existing = collect_taxonomies(directory)
            for tax, eng in items:
                if not tax:
                    errors.append({"kind": kind, "error": "empty taxonomy"})
                    continue
                slug = safe_slug(eng)
                if not slug:
                    errors.append({"kind": kind, "taxonomy": tax,
                                   "error": "english_title must contain ASCII letters/digits"})
                    continue
                if tax in existing:
                    skipped.append({"kind": kind, "taxonomy": tax, "reason": "page exists",
                                    "path": str(existing[tax])})
                else:
                    page = directory / f"{prefix}-{slug}.md"
                    if page.exists():
                        errors.append({"kind": kind, "taxonomy": tax,
                                       "error": f"{page.name} exists with a different taxonomy"})
                        continue
                    directory.mkdir(parents=True, exist_ok=True)
                    page.write_text(template.format(title=tax.replace('"', '\\"'), slug=slug,
                                                    taxonomy=tax), encoding="utf-8")
                    existing[tax] = page
                    created.append({"kind": kind, "taxonomy": tax, "path": str(page)})
                if kind == "tag" and tax != eng and tax not in load_tag_slugs(paths):
                    _append_slug(paths, tax, eng)
                    slugs_added.append({"taxonomy": tax, "slug": eng})

        process("tag", _norm(tags), paths.tags_dir, TAG_TEMPLATE, "tag")
        process("series", _norm(series), paths.series_dir, SERIES_TEMPLATE, "series")
        return {"ok": not errors, "created": created, "skipped": skipped,
                "slugs_added": slugs_added, "errors": errors}
    except Exception as e:
        logger.exception("taxonomy_ensure failed")
        return {"ok": False, "error": str(e)}

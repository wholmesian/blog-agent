"""포스트 마크다운이 AGENTS.md §1/§2 규칙을 지키는지 검증합니다 (읽기 전용)."""
import re
from datetime import datetime
from pathlib import Path

import yaml

from .paths import BlogPaths
from .taxonomy import collect_taxonomies

REQUIRED_KEYS = ["title", "excerpt", "categories", "permalink", "toc", "toc_sticky",
                 "date", "last_modified_at"]
CAPTION_RE = re.compile(r'^<p align="center" style="color:gray; font-size: 0\.8em;">.+</p>$')
IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _split_frontmatter(text):
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def navigation_categories(paths: BlogPaths) -> dict:
    """{category title: category link}. navigation.yml의 categories[].children[] 에서
    url '/categories/club/pseudolab/' -> '/club/pseudolab'."""
    nav = yaml.safe_load(paths.navigation_file.read_text(encoding="utf-8")) or {}
    out = {}
    for group in nav.get("categories", []) or []:
        for child in group.get("children", []) or []:
            title, url = child.get("title"), child.get("url")
            if title and url:
                link = "/" + url.strip("/")
                link = re.sub(r"^/categories", "", link)
                out[str(title)] = link
    return out


def _raw_list_items(raw_fm, key):
    items, on = [], False
    for line in raw_fm.splitlines():
        if re.match(rf"^{key}:\s*$", line):
            on = True
            continue
        if on:
            m = re.match(r"^\s*-\s*(.*)$", line)
            if m:
                items.append(m.group(1))
            elif line.strip():
                break
    return items


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def post_validate(file_path: str, config_path: str = None) -> dict:
    errors, warnings = [], []
    missing_tags, missing_series, missing_projects = [], [], []
    result = {"ok": False, "errors": errors, "warnings": warnings, "missing_tags": missing_tags,
              "missing_series": missing_series, "missing_projects": missing_projects}
    try:
        paths = BlogPaths(config_path)
        f = Path(file_path).expanduser()
        if not f.is_file():
            errors.append(f"File not found: {file_path}")
            return result
        text = f.read_text(encoding="utf-8")
        raw_fm, body = _split_frontmatter(text)
        if raw_fm is None:
            errors.append("Missing or malformed YAML frontmatter (must start with '---').")
            return result
        try:
            fm = yaml.safe_load(raw_fm)
        except yaml.YAMLError as e:
            errors.append(f"Frontmatter is not valid YAML: {e}")
            return result
        if not isinstance(fm, dict):
            errors.append("Frontmatter is not a mapping.")
            return result

        for k in REQUIRED_KEYS:
            if k not in fm or fm[k] in (None, "", []):
                errors.append(f"Missing required frontmatter key: {k}")
        if "tags" not in fm:
            warnings.append("No 'tags' key in frontmatter.")

        # excerpt: 큰따옴표
        m = re.search(r"^excerpt:[ \t]*(.*)$", raw_fm, re.M)
        if m and not (len(m.group(1).strip()) >= 2 and m.group(1).strip().startswith('"')
                      and m.group(1).strip().endswith('"')):
            errors.append("excerpt must be wrapped in double quotes.")

        # 카테고리
        cats = _as_list(fm.get("categories"))
        category_link = None
        if "categories" in fm:
            if len(cats) != 1:
                errors.append(f"Exactly one category is required, found {len(cats)}.")
            if cats:
                cat = str(cats[0])
                try:
                    nav = navigation_categories(paths)
                except Exception as e:
                    nav = None
                    errors.append(f"Cannot read navigation.yml: {e}")
                if nav is not None:
                    if cat in nav:
                        category_link = nav[cat]
                    else:
                        ci = {k.lower(): k for k in nav}
                        hint = f" (did you mean '{ci[cat.lower()]}'?)" if cat.lower() in ci else ""
                        errors.append(f"Category '{cat}' is not in navigation.yml{hint}. "
                                      "Categories must be added by the user manually; do not create it.")

        # permalink
        m = re.search(r"^permalink:[ \t]*(.*)$", raw_fm, re.M)
        perma = fm.get("permalink")
        if m and m.group(1).strip()[:1] in ('"', "'"):
            errors.append("permalink must not be wrapped in quotes.")
        if isinstance(perma, str):
            if category_link:
                prefix = category_link + "/"
                code = perma[len(prefix):] if perma.startswith(prefix) else None
                if not code or "/" in code:
                    errors.append(f"permalink must be '{category_link}/<permalink_code>', got '{perma}'.")
            if not perma.startswith("/"):
                errors.append("permalink must start with '/'.")

        # toc
        for k in ("toc", "toc_sticky"):
            if k in fm and fm[k] is not True:
                errors.append(f"{k} must be true.")

        # 날짜
        for k in ("date", "last_modified_at"):
            m = re.search(rf"^{k}:[ \t]*(.*)$", raw_fm, re.M)
            if m:
                val = m.group(1).strip()
                try:
                    if not DATE_RE.match(val):
                        raise ValueError
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"{k} must be a valid YYYY-MM-DD date, got '{val}'.")
        fm_name = re.match(r"^(\d{4}-\d{2}-\d{2})-", f.name)
        m = re.search(r"^date:[ \t]*(\S+)", raw_fm, re.M)
        if fm_name and m and fm_name.group(1) != m.group(1):
            warnings.append(f"Filename date {fm_name.group(1)} differs from frontmatter date {m.group(1)}.")
        if f.parent.name == "_posts" and not fm_name:
            warnings.append("Filename should look like YYYY-MM-DD-slug.md.")

        # 따옴표 경고
        for key in ("categories", "tags", "projects", "series"):
            if any(i[:1] in ('"', "'") for i in _raw_list_items(raw_fm, key)):
                warnings.append(f"Values under '{key}' should not be quoted.")

        # tags / series / projects 존재 확인
        tag_tax = set(collect_taxonomies(paths.tags_dir))
        series_tax = set(collect_taxonomies(paths.series_dir))
        project_tax = set(collect_taxonomies(paths.projects_dir))
        for t in _as_list(fm.get("tags")):
            if str(t) not in tag_tax:
                missing_tags.append(str(t))
        for s in _as_list(fm.get("series")):
            if str(s) not in series_tax:
                missing_series.append(str(s))
        for p in _as_list(fm.get("projects")):
            if str(p) not in project_tax:
                missing_projects.append(str(p))
                errors.append(f"Project '{p}' has no page in _pages/projects. Projects must be "
                              "added by the user manually; do not create it.")
        if len(_as_list(fm.get("projects"))) > 1:
            warnings.append("At most one project is expected.")
        if len(_as_list(fm.get("series"))) > 1:
            warnings.append("At most one series is expected.")
        if missing_tags:
            warnings.append(f"Tags without pages (run taxonomy_ensure): {missing_tags}")
        if missing_series:
            warnings.append(f"Series without pages (run taxonomy_ensure): {missing_series}")

        _check_body(body, paths, errors, warnings)
        result["ok"] = not errors
        return result
    except Exception as e:
        errors.append(f"Validation crashed: {e}")
        result["ok"] = False
        return result


def _check_body(body, paths, errors, warnings):
    root = paths.blog_root.resolve()
    lines = body.splitlines()
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in IMG_RE.finditer(line):
            url = m.group(1)
            if re.match(r"^[a-z]+://", url) or url.startswith("data:"):
                continue
            if not url.startswith("/"):
                warnings.append(f"Line {i + 1}: image path '{url}' is not an absolute web path.")
                continue
            rel = url.split("?")[0].lstrip("/")
            found = None
            for base in (root, root / "_site"):
                cand = (base / rel).resolve()
                if cand.is_file() and (cand == root or root in cand.parents):
                    found = base
                    break
            if found is None:
                errors.append(f"Line {i + 1}: image file not found under blog root: {url}")
            elif found != root:
                warnings.append(f"Line {i + 1}: image exists only under _site (build output): {url}")
            # 캡션 검사
            j = i + 1
            while j < len(lines) and not lines[j].strip() and j <= i + 2:
                j += 1
            if j < len(lines):
                nxt = lines[j].strip()
                caption_like = (nxt.startswith("<p") or nxt.startswith("<figcaption")
                                or nxt.startswith("<em") or nxt.startswith("<center")
                                or nxt.startswith("<sub")
                                or re.fullmatch(r"(\*[^*].*\*|_[^_].*_)", nxt) is not None)
                if caption_like and not CAPTION_RE.match(nxt):
                    errors.append(f"Line {j + 1}: image caption must use "
                                  '<p align="center" style="color:gray; font-size: 0.8em;">…</p>.')

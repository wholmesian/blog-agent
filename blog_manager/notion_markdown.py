"""Notion 블록 -> 마크다운 초안 변환기 (결정적, LLM 없음, 프론트매터 없음)."""
import html

CAPTION_TEMPLATE = '<p align="center" style="color:gray; font-size: 0.8em;">{}</p>'

_LANG_MAP = {"plain text": "", "c++": "cpp", "c#": "csharp", "objective-c": "objectivec",
             "shell": "bash", "vb.net": "vbnet", "f#": "fsharp", "webassembly": "wasm"}


def rich_text_plain(rich_text) -> str:
    return "".join(t.get("plain_text", "") for t in (rich_text or []))


def render_rich_text(rich_text) -> str:
    """rich_text 배열을 인라인 마크다운으로 변환합니다."""
    out = []
    for t in rich_text or []:
        if t.get("type") == "equation":
            text = "$" + t.get("equation", {}).get("expression", t.get("plain_text", "")) + "$"
            out.append(text)
            continue
        text = t.get("plain_text", "")
        if not text:
            continue
        ann = t.get("annotations", {}) or {}
        if ann.get("code"):
            fence = "``" if "`" in text else "`"
            text = f"{fence}{text}{fence}"
        else:
            # 앞뒤 공백은 강조 기호 밖으로 빼야 마크다운이 깨지지 않는다.
            core = text.strip()
            if core:
                lead = text[: len(text) - len(text.lstrip())]
                trail = text[len(text.rstrip()):]
                if ann.get("bold") and ann.get("italic"):
                    core = f"***{core}***"
                elif ann.get("bold"):
                    core = f"**{core}**"
                elif ann.get("italic"):
                    core = f"*{core}*"
                if ann.get("strikethrough"):
                    core = f"~~{core}~~"
                text = lead + core + trail
        href = t.get("href")
        if href:
            text = f"[{text}]({href})"
        out.append(text)
    return "".join(out)


def _image_url(data: dict) -> str:
    if "file" in data:
        return data["file"].get("url", "")
    if "external" in data:
        return data["external"].get("url", "")
    return ""


def _code_fence(code: str, lang: str) -> str:
    fence = "```"
    while fence in code:
        fence += "`"
    return f"{fence}{lang}\n{code}\n{fence}"


def _indent(text: str, prefix: str) -> str:
    return "\n".join((prefix + line) if line.strip() else line for line in text.split("\n"))


def _quote(text: str) -> str:
    return "\n".join(("> " + line) if line.strip() else ">" for line in text.split("\n"))


def _render_children(block) -> str:
    return render_blocks(block.get("children", [])).strip("\n")


def _table(block) -> str:
    rows = []
    for row in block.get("children", []):
        if row.get("type") != "table_row":
            continue
        cells = [render_rich_text(c).replace("|", "\\|").replace("\n", " ")
                 for c in row["table_row"].get("cells", [])]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _render_block(block, number=None):
    """블록 하나를 (kind, text)로 변환합니다. kind는 연속 리스트 판별용."""
    t = block.get("type", "")
    data = block.get(t, {}) if isinstance(block.get(t), dict) else {}
    rt = render_rich_text(data.get("rich_text"))
    if t == "paragraph":
        text = rt
        if block.get("children"):
            text = (text + "\n\n" if text else "") + _indent(_render_children(block), "    ")
        return "p", text
    if t in ("heading_1", "heading_2", "heading_3"):
        text = "#" * int(t[-1]) + " " + rt
        if block.get("children"):
            text += "\n\n" + _render_children(block)
        return "h", text
    if t in ("bulleted_list_item", "numbered_list_item", "to_do"):
        if t == "bulleted_list_item":
            marker = "- "
        elif t == "numbered_list_item":
            marker = f"{number or 1}. "
        else:
            marker = "- [x] " if data.get("checked") else "- [ ] "
        text = marker + rt
        if block.get("children"):
            text += "\n" + _indent(_render_children(block), "    ")
        return "list", text
    if t == "quote":
        text = rt
        if block.get("children"):
            text += "\n\n" + _render_children(block)
        return "q", _quote(text)
    if t == "callout":
        icon = data.get("icon") or {}
        emoji = icon.get("emoji", "") if icon.get("type") == "emoji" else ""
        text = (emoji + " " if emoji else "") + rt
        if block.get("children"):
            text += "\n\n" + _render_children(block)
        return "q", _quote(text)
    if t == "code":
        lang = (data.get("language") or "").lower()
        lang = _LANG_MAP.get(lang, lang)
        text = _code_fence(rich_text_plain(data.get("rich_text")), lang)
        cap = rich_text_plain(data.get("caption"))
        if cap:
            text += "\n" + CAPTION_TEMPLATE.format(html.escape(cap, quote=False))
        return "code", text
    if t == "divider":
        return "hr", "---"
    if t == "image":
        url = _image_url(data)
        cap = rich_text_plain(data.get("caption"))
        text = f"![{cap.replace(chr(10), ' ') if cap else 'image'}]({url})"
        if cap:
            text += "\n" + CAPTION_TEMPLATE.format(html.escape(cap, quote=False))
        return "img", text
    if t == "toggle":
        inner = _render_children(block)
        text = f"<details markdown=\"1\">\n<summary>{rt}</summary>\n\n{inner}\n\n</details>"
        return "toggle", text
    if t == "table":
        return "table", _table(block)
    if t == "equation":
        return "eq", "$$\n" + data.get("expression", "") + "\n$$"
    if t == "bookmark":
        url = data.get("url", "")
        return "p", f"[{url}]({url})" if url else ""
    if t in ("column_list", "column"):
        return "p", _render_children(block)
    return "unsupported", f"<!-- unsupported block: {t} -->"


def render_blocks(blocks) -> str:
    """블록 리스트를 마크다운 문자열로 변환합니다."""
    parts = []  # (kind, text)
    counter = 0
    for block in blocks or []:
        t = block.get("type", "")
        if t == "numbered_list_item":
            counter += 1
        else:
            counter = 0
        kind, text = _render_block(block, counter if t == "numbered_list_item" else None)
        if t == "table_row":
            continue
        parts.append((kind, text, t))
    out = []
    prev_type = None
    for kind, text, t in parts:
        if out:
            same_list = kind == "list" and prev_type is not None and prev_type in (
                "bulleted_list_item", "numbered_list_item", "to_do") and (
                prev_type == t or {prev_type, t} <= {"bulleted_list_item", "to_do"})
            out.append("\n" if same_list else "\n\n")
        out.append(text)
        prev_type = t
    return "".join(out).strip("\n") + ("\n" if out else "")


def blocks_to_markdown(blocks) -> str:
    return render_blocks(blocks)

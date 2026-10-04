from blog_manager.notion_export import extract_page_id
from blog_manager.notion_markdown import blocks_to_markdown


def rt(text, **ann):
    href = ann.pop("href", None)
    return {"type": "text", "plain_text": text, "href": href,
            "annotations": {"bold": False, "italic": False, "strikethrough": False,
                            "code": False, **ann}}


def blk(t, rich=None, children=None, **extra):
    b = {"type": t, "id": "x", t: {"rich_text": rich or [], **extra}}
    if children:
        b["children"] = children
    return b


def test_basic_blocks():
    md = blocks_to_markdown([
        blk("heading_2", [rt("제목")]),
        blk("paragraph", [rt("a "), rt("b", bold=True), rt(" "), rt("i", italic=True), rt(" "),
                          rt("c", code=True), rt(" "), rt("l", href="http://x.y")]),
        blk("divider"),
        blk("quote", [rt("q")]),
        blk("code", [rt("print(1)")], language="python"),
        blk("equation", expression="E=mc^2"),
        blk("to_do", [rt("t")], checked=True),
    ])
    assert "## 제목" in md
    assert "a **b** *i* `c` [l](http://x.y)" in md
    assert "\n---\n" in md and "> q" in md
    assert "```python\nprint(1)\n```" in md
    assert "$$\nE=mc^2\n$$" in md and "- [x] t" in md


def test_lists_nesting_and_numbering():
    md = blocks_to_markdown([
        blk("bulleted_list_item", [rt("a")], children=[blk("bulleted_list_item", [rt("a1")])]),
        blk("bulleted_list_item", [rt("b")]),
        blk("paragraph", [rt("gap")]),
        blk("numbered_list_item", [rt("one")]),
        blk("numbered_list_item", [rt("two")]),
    ])
    assert "- a\n    - a1\n- b\n\ngap\n\n1. one\n2. two" in md


def test_image_caption_exact_format():
    img = {"type": "image", "id": "i", "image": {"type": "file", "file": {"url": "/assets/images/posts_img/d/a.png"},
                                                  "caption": [rt("캡션 <b>")]}}
    md = blocks_to_markdown([img])
    assert md.startswith("![캡션 <b>](/assets/images/posts_img/d/a.png)\n")
    assert '<p align="center" style="color:gray; font-size: 0.8em;">캡션 &lt;b&gt;</p>' in md
    nocap = {"type": "image", "id": "i", "image": {"type": "external", "external": {"url": "/a.png"}, "caption": []}}
    assert "<p" not in blocks_to_markdown([nocap])


def test_toggle_table_unsupported_callout():
    table = {"type": "table", "id": "t", "table": {}, "children": [
        {"type": "table_row", "table_row": {"cells": [[rt("h1")], [rt("h2")]]}},
        {"type": "table_row", "table_row": {"cells": [[rt("a")], [rt("b")]]}}]}
    md = blocks_to_markdown([
        blk("toggle", [rt("sum")], children=[blk("paragraph", [rt("inner")])]),
        table,
        {"type": "weird", "id": "w", "weird": {}},
        blk("callout", [rt("note")], icon={"type": "emoji", "emoji": "💡"}),
    ])
    assert "<summary>sum</summary>" in md and "inner" in md and "</details>" in md
    assert "| h1 | h2 |\n| --- | --- |\n| a | b |" in md
    assert "<!-- unsupported block: weird -->" in md
    assert "> 💡 note" in md


def test_extract_page_id():
    assert extract_page_id("https://www.notion.so/ws/My-Title-0123456789abcdef0123456789abcdef?pvs=4") == \
        "0123456789abcdef0123456789abcdef"
    assert extract_page_id("01234567-89ab-cdef-0123-456789abcdef") == "0123456789abcdef0123456789abcdef"
    try:
        extract_page_id("nonsense")
        assert False
    except ValueError:
        pass

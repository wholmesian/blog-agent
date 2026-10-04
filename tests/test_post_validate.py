from pathlib import Path

from blog_manager.post_validate import post_validate

SAMPLE = Path(__file__).resolve().parent.parent / "examples/2026-04-25-sample.md"

GOOD = '''---
title: "T"
excerpt: "E"

categories:
  - PseudoLab
tags:
  - 시간
projects:
  - polmap
series:
  - sabermetrics

permalink: /club/pseudolab/code1

toc: true
toc_sticky: true

date: 2026-04-25
last_modified_at: 2026-04-26
---

![a](/assets/images/posts_img/2026-04-25/pic.png)
<p align="center" style="color:gray; font-size: 0.8em;">cap</p>
'''


def write(blog, text, name="2026-04-25-t.md"):
    f = blog / "_posts" / name
    f.write_text(text, encoding="utf-8")
    return str(f)


def test_sample_passes(blog):
    r = post_validate(str(SAMPLE))
    assert r["ok"], r
    assert r["missing_tags"] == [] and r["missing_series"] == []


def test_good(blog):
    r = post_validate(write(blog, GOOD))
    assert r["ok"], r
    assert r["errors"] == []


def test_wrong_category_and_permalink(blog):
    r = post_validate(write(blog, GOOD.replace("PseudoLab", "Nope")))
    assert not r["ok"] and any("not in navigation" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace("/club/pseudolab/code1", "/club/bookclub/code1")))
    assert not r["ok"] and any("permalink" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace("/club/pseudolab/code1", '"/club/pseudolab/code1"')))
    assert any("quotes" in e for e in r["errors"])


def test_toc_excerpt_dates(blog):
    r = post_validate(write(blog, GOOD.replace("toc_sticky: true", "toc_sticky: false")))
    assert any("toc_sticky" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace('excerpt: "E"', "excerpt: E")))
    assert any("excerpt" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace("date: 2026-04-25", "date: 2026-4-25")))
    assert any("date" in e for e in r["errors"])


def test_missing_key_and_two_categories(blog):
    r = post_validate(write(blog, GOOD.replace('title: "T"\n', "")))
    assert any("title" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace("  - PseudoLab", "  - PseudoLab\n  - Book Club")))
    assert any("Exactly one" in e for e in r["errors"])


def test_missing_taxonomy_and_project(blog):
    r = post_validate(write(blog, GOOD.replace("  - 시간", "  - 없는태그").replace("  - sabermetrics", "  - nos")
                            .replace("  - polmap", "  - nop")))
    assert r["missing_tags"] == ["없는태그"] and r["missing_series"] == ["nos"]
    assert r["missing_projects"] == ["nop"] and not r["ok"]
    assert not (blog / "_pages/projects/project-nop.md").exists()


def test_images(blog):
    r = post_validate(write(blog, GOOD.replace("pic.png", "gone.png")))
    assert any("not found" in e for e in r["errors"])
    r = post_validate(write(blog, GOOD.replace(
        '<p align="center" style="color:gray; font-size: 0.8em;">cap</p>', "*cap*")))
    assert any("caption" in e for e in r["errors"])
    no_cap = GOOD.rsplit("<p align", 1)[0]
    assert post_validate(write(blog, no_cap))["ok"]


def test_no_frontmatter(blog):
    assert not post_validate(write(blog, "hello"))["ok"]
    assert not post_validate(str(blog / "nope.md"))["ok"]

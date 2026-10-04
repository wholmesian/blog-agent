import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NAV = """main:
  - title: "About"
    url: /about/
categories:
  - title: "모임"
    children:
      - title: "PseudoLab"
        url: /categories/club/pseudolab/
      - title: "Book Club"
        url: /categories/club/bookclub/
"""


def page(layout, title, permalink, taxonomy):
    return (f'---\ntitle: "{title}"\nlayout: {layout}\npermalink: {permalink}\n'
            f'author_profile: true\ntaxonomy: {taxonomy}\nsidebar:\n  nav: "categories"\n---\n')


@pytest.fixture
def blog(tmp_path, monkeypatch):
    root = tmp_path / "blog"
    (root / "_data").mkdir(parents=True)
    (root / "_data" / "navigation.yml").write_text(NAV, encoding="utf-8")
    (root / "_data" / "tag_slugs.yml").write_text("시간: time\n", encoding="utf-8")
    for d in ("_posts", "_pages/tags", "_pages/series", "_pages/projects", "assets/images/posts_img/2026-04-25"):
        (root / d).mkdir(parents=True)
    (root / "_pages/tags/tag-time.md").write_text(page("tag", "시간", "/tags/time/", "시간"), encoding="utf-8")
    for t in ("야구", "세이버메트릭스", "KBO"):
        slug = {"야구": "baseball", "세이버메트릭스": "sabermetrics", "KBO": "kbo"}[t]
        (root / f"_pages/tags/tag-{slug}.md").write_text(page("tag", t, f"/tags/{slug}/", t), encoding="utf-8")
    (root / "_pages/series/series-sabermetrics.md").write_text(
        page("series", "sabermetrics", "/series/sabermetrics/", "sabermetrics"), encoding="utf-8")
    (root / "_pages/projects/project-polmap.md").write_text(
        '---\ntitle: "Polmap"\nlayout: project\npermalink: /projects/polmap/\ntaxonomy: polmap\n---\n', encoding="utf-8")
    (root / "assets/images/posts_img/2026-04-25/pic.png").write_bytes(b"\x89PNG")
    monkeypatch.setenv("BLOG_ROOT", str(root))
    return root

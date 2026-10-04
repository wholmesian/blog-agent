import os
import pytest
import yaml


@pytest.fixture
def blog(tmp_path, monkeypatch):
    root = tmp_path / "blog"
    for d in ["_posts", "_pages/tags", "_pages/series", "_pages/projects", "_data",
              "assets/images/posts_img", "_site/assets/images/posts_img", "_layouts"]:
        (root / d).mkdir(parents=True)
    (root / "_config.yml").write_text("title: x\n")
    (root / "_layouts" / "default.html").write_text("x")
    (root / "_data" / "tag_slugs.yml").write_text("한글: korean\n파이썬: python\n")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(yaml.safe_dump({
        "blog_root": str(root),
        "mapping": {"default": {
            "post_dir": str(root / "_posts"),
            "image_dir": str(root / "assets/images/posts_img"),
            "image_web_root": "/assets/images/posts_img/",
        }},
    }))
    monkeypatch.setenv("BLOG_ROOT", str(root))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    return {"root": root, "cfg": str(cfg), "outside": outside}


def make_post(root, name, title, img=None):
    body = "---\ntitle: \"%s\"\n---\nbody\n" % title
    if img:
        d = root / "assets/images/posts_img" / os.path.dirname(img)
        d.mkdir(parents=True, exist_ok=True)
        (root / "assets/images/posts_img" / img).write_text("png")
        body += "![a](/assets/images/posts_img/%s)\n" % img
    p = root / "_posts" / name
    p.write_text(body)
    return p

from blog_manager.cleanup_tool import find_unused_assets, execute_cleanup


def make_tag(root, name, taxonomy):
    p = root / "_pages/tags" / name
    p.write_text('---\ntitle: "%s"\nlayout: tag\ntaxonomy: %s\n---\n' % (taxonomy, taxonomy))
    return p


def test_find_unused_keys_and_content(blog):
    root = blog["root"]
    (root / "_posts" / "2026-01-01-a.md").write_text(
        "---\ntitle: A\ntags:\n  - used\n---\n![x](/assets/images/posts_img/u.png)\n")
    (root / "assets/images/posts_img/u.png").write_text("1")
    (root / "assets/images/posts_img/unused.png").write_text("1")
    make_tag(root, "tag-used.md", "used")
    t = make_tag(root, "tag-old.md", "old")
    r = find_unused_assets(blog["cfg"])
    assert set(r) == {"tags", "series", "projects", "posts_img", "projects_img"}
    assert r["tags"] == [str(t)]
    assert [os.path.basename(x) for x in r["posts_img"]] == ["unused.png"]


def test_dry_run_keeps_files_and_slugs(blog):
    root = blog["root"]
    t = make_tag(root, "tag-python.md", "파이썬")
    slugs = root / "_data/tag_slugs.yml"
    before = slugs.read_text()
    res = execute_cleanup([str(t)], config_path=blog["cfg"])
    assert res["dry_run"] and res["deleted"] == [str(t)]
    assert t.exists() and slugs.read_text() == before


def test_confirm_deletes_and_syncs_tag_slugs(blog):
    root = blog["root"]
    t = make_tag(root, "tag-python.md", "파이썬")
    other = make_tag(root, "tag-korean.md", "한글")
    res = execute_cleanup([str(t)], confirm=True, config_path=blog["cfg"])
    assert res["ok"] and not res["dry_run"] and res["deleted"] == [str(t)]
    assert not t.exists() and other.exists()
    content = (root / "_data/tag_slugs.yml").read_text()
    assert "python" not in content and "korean" in content


def test_cleanup_rejects_unsafe(blog):
    root = blog["root"]
    slugs = root / "_data/tag_slugs.yml"
    before = slugs.read_text()
    res = execute_cleanup([str(slugs), str(root / "_config.yml"), str(blog["outside"] / "secret.txt")],
                          confirm=True, config_path=blog["cfg"])
    assert res["deleted"] == [] and len(res["skipped"]) == 3
    assert slugs.read_text() == before and (root / "_config.yml").exists()


def test_cleanup_empty_dir_removal(blog):
    root = blog["root"]
    d = root / "assets/images/posts_img/2026-01-01"; d.mkdir()
    f = d / "a.png"; f.write_text("1")
    res = execute_cleanup([str(f)], confirm=True, config_path=blog["cfg"])
    assert res["ok"] and not d.exists()
    assert (root / "assets/images/posts_img").exists()

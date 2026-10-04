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

from blog_manager.delete_post_tool import find_files_to_delete, delete_files


def test_find_single(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "Hello", img="2026-01-01/a.png")
    r = find_files_to_delete("Hello", blog["cfg"])
    assert "error" not in r
    assert r["post_files"] == [str(p)]
    assert len(r["image_files"]) == 1 and r["image_files"][0].endswith("a.png")


def test_find_not_found(blog):
    assert "error" in find_files_to_delete("Nope", blog["cfg"])


def test_find_multiple_returns_candidates(blog):
    make_post(blog["root"], "2026-01-01-a.md", "Same", img="d1/a.png")
    make_post(blog["root"], "2026-01-02-b.md", "Same", img="d2/b.png")
    r = find_files_to_delete("Same", blog["cfg"])
    assert "error" in r and "Multiple" in r["error"]
    assert len(r["candidates"]) == 2
    assert all(len(c["image_files"]) == 1 for c in r["candidates"])


def test_dry_run_default_does_not_delete(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "A", img="d/a.png")
    r = find_files_to_delete("A", blog["cfg"])
    res = delete_files(r["post_files"] + r["image_files"], config_path=blog["cfg"])
    assert res["dry_run"] is True and res["ok"] is True
    assert len(res["deleted"]) == 2
    assert p.exists() and (blog["root"] / "assets/images/posts_img/d/a.png").exists()


def test_confirm_deletes_and_cleans_empty_dirs(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "A", img="d/a.png")
    r = find_files_to_delete("A", blog["cfg"])
    res = delete_files(r["post_files"] + r["image_files"], confirm=True, config_path=blog["cfg"])
    assert res["dry_run"] is False and res["ok"] and len(res["deleted"]) == 2
    assert not p.exists()
    assert not (blog["root"] / "assets/images/posts_img/d").exists()  # empty subdir removed
    assert (blog["root"] / "assets/images/posts_img").exists()  # allowed dirs kept
    assert (blog["root"] / "_posts").exists()
    assert (blog["root"] / "assets/images").exists()


def test_empty_dir_not_removed_if_not_empty(blog):
    make_post(blog["root"], "2026-01-01-a.md", "A", img="d/a.png")
    keep = blog["root"] / "assets/images/posts_img/d/keep.png"; keep.write_text("1")
    delete_files([str(blog["root"] / "assets/images/posts_img/d/a.png")], confirm=True, config_path=blog["cfg"])
    assert keep.exists()


def test_unsafe_paths_skipped_even_with_confirm(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "A")
    bad = [str(blog["root"] / "_config.yml"), str(blog["outside"] / "secret.txt"),
           str(blog["root"] / "_posts" / ".." / ".." / "outside" / "secret.txt")]
    res = delete_files([str(p)] + bad, confirm=True, config_path=blog["cfg"])
    assert len(res["deleted"]) == 1 and len(res["skipped"]) == 3
    assert (blog["root"] / "_config.yml").exists()
    assert (blog["outside"] / "secret.txt").exists()


def test_symlink_escape_not_deleted(blog):
    link = blog["root"] / "_posts" / "l.md"
    link.symlink_to(blog["outside"] / "secret.txt")
    res = delete_files([str(link)], confirm=True, config_path=blog["cfg"])
    assert res["deleted"] == [] and len(res["skipped"]) == 1
    assert (blog["outside"] / "secret.txt").exists()

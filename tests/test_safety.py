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

from blog_manager.safety import assert_deletable, validate_batch, UnsafePathError


def test_allows_post(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "A")
    assert assert_deletable(str(p), blog["cfg"]) == p.resolve()


def test_allows_assets_and_site_images(blog):
    a = blog["root"] / "assets/images/posts_img/x.png"; a.write_text("1")
    b = blog["root"] / "_site/assets/images/posts_img/y.png"; b.write_text("1")
    c = blog["root"] / "_pages/tags/tag-a.md"; c.write_text("1")
    for p in (a, b, c):
        assert assert_deletable(str(p), blog["cfg"])


def test_rejects_traversal(blog):
    p = str(blog["root"] / "_posts" / ".." / ".." / "outside" / "secret.txt")
    with pytest.raises(UnsafePathError, match="outside"):
        assert_deletable(p, blog["cfg"])


def test_rejects_traversal_within_root(blog):
    p = str(blog["root"] / "_posts" / ".." / "_config.yml")
    with pytest.raises(UnsafePathError, match="allowed"):
        assert_deletable(p, blog["cfg"])


def test_rejects_symlink_escape(blog):
    link = blog["root"] / "_posts" / "link.md"
    link.symlink_to(blog["outside"] / "secret.txt")
    with pytest.raises(UnsafePathError, match="outside"):
        assert_deletable(str(link), blog["cfg"])


def test_rejects_symlinked_dir_escape(blog):
    d = blog["root"] / "assets/images/posts_img/evil"
    d.symlink_to(blog["outside"], target_is_directory=True)
    with pytest.raises(UnsafePathError):
        assert_deletable(str(d / "secret.txt"), blog["cfg"])


def test_rejects_outside_root(blog):
    with pytest.raises(UnsafePathError, match="outside"):
        assert_deletable(str(blog["outside"] / "secret.txt"), blog["cfg"])


@pytest.mark.parametrize("rel", ["_config.yml", "_layouts/default.html", "_data/tag_slugs.yml"])
def test_rejects_non_allowed_dir(blog, rel):
    with pytest.raises(UnsafePathError, match="allowed"):
        assert_deletable(str(blog["root"] / rel), blog["cfg"])


def test_rejects_directory_and_missing_and_root(blog):
    with pytest.raises(UnsafePathError, match="directory"):
        assert_deletable(str(blog["root"] / "_posts" / "sub") if (blog["root"] / "_posts" / "sub").mkdir() is None else "", blog["cfg"])
    with pytest.raises(UnsafePathError, match="allowed"):
        assert_deletable(str(blog["root"] / "_posts"), blog["cfg"])
    with pytest.raises(UnsafePathError, match="exist"):
        assert_deletable(str(blog["root"] / "_posts" / "nope.md"), blog["cfg"])
    with pytest.raises(UnsafePathError, match="empty"):
        assert_deletable("", blog["cfg"])


def test_validate_batch(blog):
    p = make_post(blog["root"], "2026-01-01-a.md", "A")
    ok, rej = validate_batch([str(p), str(p), str(blog["root"] / "_config.yml")], blog["cfg"])
    assert ok == [p.resolve()]
    assert len(rej) == 1 and "reason" in rej[0] and rej[0]["path"].endswith("_config.yml")

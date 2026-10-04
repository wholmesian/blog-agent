from blog_manager.post_writer import post_write


def test_write_and_refuse_overwrite(blog):
    r = post_write("my-post", "2026-04-25", content="hello")
    assert r["ok"] and r["path"].endswith("_posts/2026-04-25-my-post.md")
    assert (blog / "_posts/2026-04-25-my-post.md").read_text() == "hello\n"
    r2 = post_write("my-post", "2026-04-25", content="new")
    assert not r2["ok"] and "overwrite" in r2["error"]
    r3 = post_write("my-post", "2026-04-25", content="new", overwrite=True)
    assert r3["ok"] and r3["overwritten"]
    assert (blog / "_posts/2026-04-25-my-post.md").read_text() == "new\n"


def test_content_file(blog, tmp_path):
    f = tmp_path / "x.md"
    f.write_text("body", encoding="utf-8")
    assert post_write("a", "2026-01-01", content_file=str(f))["ok"]


def test_invalid_inputs(blog):
    for slug in ("../evil", "a/b", "한글", "", "a b"):
        assert not post_write(slug, "2026-04-25", content="x")["ok"]
    for d in ("2026-4-25", "20260425", "2026-13-01", "x"):
        assert not post_write("a", d, content="x")["ok"]
    assert not post_write("a", "2026-04-25")["ok"]
    assert not post_write("a", "2026-04-25", content="x", content_file="y")["ok"]
    assert not post_write("a", "2026-04-25", content="  ")["ok"]
    assert not post_write("a", "2026-04-25", content_file="/nonexistent.md")["ok"]
    assert list((blog / "_posts").iterdir()) == []

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, stdin=None):
    p = subprocess.run([sys.executable, "-m", "blog_manager", *args], cwd=ROOT,
                       input=stdin, capture_output=True, text=True, env=os.environ.copy())
    return p.returncode, p.stdout, p.stderr


def run_json(*args, **kw):
    code, out, err = run(*args, **kw)
    return code, json.loads(out), err


def test_usage_errors_exit_2():
    assert run()[0] == 2
    assert run("nope")[0] == 2
    assert run("post-write", "--slug", "a", "--date", "2026-01-01")[0] == 2
    assert run("taxonomy-ensure", "--tag", "noequals")[0] == 2


def test_post_write_stdin_and_overwrite(blog):
    code, out, _ = run_json("post-write", "--slug", "hi", "--date", "2026-04-25", "--stdin", stdin="hello")
    assert code == 0 and out["ok"]
    assert (blog / "_posts/2026-04-25-hi.md").exists()
    code, out, _ = run_json("post-write", "--slug", "hi", "--date", "2026-04-25", "--stdin", stdin="x")
    assert code == 1 and not out["ok"]
    code, out, _ = run_json("post-write", "--slug", "hi", "--date", "2026-04-25", "--stdin",
                            "--overwrite", stdin="x")
    assert code == 0


def test_taxonomy_ensure_and_validate(blog, tmp_path):
    code, out, _ = run_json("taxonomy-ensure", "--tag", "새태그=new-tag", "--series", "새시리즈=new-series")
    assert code == 0 and len(out["created"]) == 2
    assert (blog / "_pages/tags/tag-new-tag.md").exists()
    f = tmp_path / "bad.md"
    f.write_text("no frontmatter", encoding="utf-8")
    code, out, _ = run_json("post-validate", str(f))
    assert code == 1 and not out["ok"]


def test_delete_dry_run_then_yes(blog):
    target = blog / "assets/images/posts_img/2026-04-25/pic.png"
    code, out, _ = run_json("delete-files", str(target))
    assert code == 0 and out["dry_run"] and target.exists()
    code, out, _ = run_json("delete-files", str(target), "--yes")
    assert code == 0 and not out["dry_run"] and not target.exists()


def test_delete_outside_blog_refused(blog, tmp_path):
    f = tmp_path / "secret.txt"
    f.write_text("s")
    code, out, _ = run_json("delete-files", str(f), "--yes")
    assert f.exists()
    assert out["skipped"] or out["errors"]


def test_cleanup_dry_run(blog):
    code, out, _ = run_json("find-unused-assets")
    assert code == 0 and isinstance(out, dict)
    tag = blog / "_pages/tags/tag-time.md"
    code, out, _ = run_json("execute-cleanup", str(tag))
    assert out["dry_run"] and tag.exists()


def test_stdout_json_only_and_config_flag(blog):
    code, out, err = run("--config", str(ROOT / "config.yaml"), "find-unused-assets")
    assert code == 0
    json.loads(out)

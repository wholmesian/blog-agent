"""삭제 대상 경로 검증. blog_root 하위의 허용 디렉토리 안의 일반 파일만 통과시킵니다."""
import os
from pathlib import Path

from .paths import BlogPaths

ALLOWED_SUBDIRS = ("_posts", "_pages", "assets/images", "_site/assets/images")


class UnsafePathError(ValueError):
    """삭제가 허용되지 않는 경로."""


def allowed_roots(config_path=None, paths: BlogPaths = None) -> list:
    """허용 디렉토리(resolve된 절대 Path) 목록."""
    paths = paths or BlogPaths(config_path)
    root = paths.blog_root.resolve()
    return [(root / sub).resolve() for sub in ALLOWED_SUBDIRS]


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_deletable(path, config_path=None, paths: BlogPaths = None) -> Path:
    """삭제 가능한 경로면 resolve된 Path를 반환하고, 아니면 UnsafePathError를 발생시킵니다."""
    paths = paths or BlogPaths(config_path)
    if path is None or str(path).strip() == "":
        raise UnsafePathError("empty path")
    raw = Path(os.path.expanduser(str(path)))
    if not raw.is_absolute():
        raw = paths.blog_root / raw
    resolved = raw.resolve()  # symlink 및 '..' 해석

    root = paths.blog_root.resolve()
    if not _is_within(resolved, root):
        raise UnsafePathError(f"path is outside blog_root: {path}")
    if not any(_is_within(resolved, a) and resolved != a for a in allowed_roots(paths=paths)):
        raise UnsafePathError(
            f"path is not inside an allowed directory ({', '.join(ALLOWED_SUBDIRS)}): {path}"
        )
    if not resolved.exists():
        raise UnsafePathError(f"path does not exist: {path}")
    if resolved.is_dir():
        raise UnsafePathError(f"path is a directory, only files can be deleted: {path}")
    if not resolved.is_file():
        raise UnsafePathError(f"path is not a regular file: {path}")
    return resolved


def validate_batch(files, config_path=None, paths: BlogPaths = None):
    """(ok_paths, rejected[{path, reason}]) 반환. ok_paths는 중복 제거된 resolve된 Path 리스트."""
    paths = paths or BlogPaths(config_path)
    ok, rejected, seen = [], [], set()
    for f in files or []:
        try:
            p = assert_deletable(f, paths=paths)
        except UnsafePathError as e:
            rejected.append({"path": str(f), "reason": str(e)})
            continue
        if p not in seen:
            seen.add(p)
            ok.append(p)
    return ok, rejected


def remove_empty_dirs(start_dirs, config_path=None, paths: BlogPaths = None) -> list:
    """파일 삭제 후 비어 있는 부모 디렉토리를 허용 디렉토리 내부에서만 제거(허용 루트 자체는 유지, 상위로 재귀하지 않음)."""
    paths = paths or BlogPaths(config_path)
    roots = allowed_roots(paths=paths)
    removed = []
    for d in sorted({Path(x) for x in start_dirs}):
        if any(_is_within(d, r) and d != r for r in roots) and d.is_dir() and not any(d.iterdir()):
            try:
                d.rmdir()
                removed.append(str(d))
            except OSError:
                pass
    return removed

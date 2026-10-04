"""config.yaml 로딩과 블로그 경로 해석을 한 곳에서 담당합니다.

모든 상대 경로는 현재 작업 디렉토리(cwd)가 아니라 repo 루트(이 패키지의 상위
디렉토리) 기준으로 해석되므로, 어느 위치에서 실행해도 같은 결과를 냅니다.
"""
import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"
DEFAULT_BLOG_ROOT = "../wholmesian.github.io"


def resolve_path(p) -> Path:
    """상대 경로는 repo 루트 기준으로, 절대 경로는 그대로 절대 Path로 변환합니다."""
    path = Path(os.path.expanduser(str(p)))
    if not path.is_absolute():
        path = REPO_ROOT / path
    return Path(os.path.normpath(path))


def load_config(config_path=None) -> dict:
    """config.yaml을 읽습니다. 기본값/상대 경로는 repo 루트 기준입니다."""
    path = resolve_path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class BlogPaths:
    """블로그 repo 안의 주요 경로를 절대 Path로 제공합니다."""

    def __init__(self, config_path=None, config: dict = None):
        self.config = config if config is not None else load_config(config_path)

    @property
    def blog_root(self) -> Path:
        raw = os.environ.get("BLOG_ROOT") or self.config.get("blog_root") or DEFAULT_BLOG_ROOT
        return resolve_path(raw)

    @property
    def posts_dir(self) -> Path:
        return self.blog_root / "_posts"

    @property
    def tags_dir(self) -> Path:
        return self.blog_root / "_pages" / "tags"

    @property
    def series_dir(self) -> Path:
        return self.blog_root / "_pages" / "series"

    @property
    def projects_dir(self) -> Path:
        return self.blog_root / "_pages" / "projects"

    @property
    def tag_slugs_file(self) -> Path:
        return self.blog_root / "_data" / "tag_slugs.yml"

    @property
    def navigation_file(self) -> Path:
        return self.blog_root / "_data" / "navigation.yml"

    @property
    def projects_img_dirs(self) -> list:
        return [
            self.blog_root / "assets" / "images" / "projects_img",
            self.blog_root / "_site" / "assets" / "images" / "projects_img",
        ]

    def mapping(self, category: str = "default") -> dict:
        """카테고리별 mapping 설정 (없으면 default)."""
        mapping = self.config.get("mapping", {})
        return mapping.get(category, mapping.get("default", {}))

    def post_dir(self, category: str = "default") -> Path:
        raw = self.mapping(category).get("post_dir")
        return resolve_path(raw) if raw else self.posts_dir

    def image_dir(self, category: str = "default") -> Path:
        raw = self.mapping(category).get("image_dir")
        if raw:
            return resolve_path(raw)
        return self.blog_root / "assets" / "images" / "posts_img"

    def image_web_root(self, category: str = "default") -> str:
        return self.mapping(category).get("image_web_root", "/assets/images/posts_img/")

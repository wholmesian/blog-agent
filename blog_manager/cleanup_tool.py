import logging
import os
import re
import yaml

from .paths import BlogPaths, load_config
from .safety import remove_empty_dirs, validate_batch

logger = logging.getLogger(__name__)

def find_unused_assets(config_path: str = None) -> dict:
    """
    Scans the blog repository to find unused tags, series, projects, and images.
    Returns a dictionary of unused files categorized by type.
    """
    try:
        config = load_config(config_path)
    except Exception as e:
        return {"error": f"Failed to load config: {e}"}

    paths = BlogPaths(config=config)
    post_dir = str(paths.post_dir())
    image_dir = str(paths.image_dir())
    
    tags_dir = str(paths.tags_dir)
    series_dir = str(paths.series_dir)
    projects_dir = str(paths.projects_dir)
    projects_img_dir_1, projects_img_dir_2 = [str(p) for p in paths.projects_img_dirs]
    
    used_tags = set()
    used_series = set()
    used_projects = set()
    used_posts_img_urls = set()
    used_projects_img_urls = set()
    
    def parse_yaml_frontmatter(content):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1])
            except:
                pass
        return {}

    # 1. Parse _posts/
    if os.path.exists(post_dir):
        for filename in os.listdir(post_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(post_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                continue
                
            fm = parse_yaml_frontmatter(content)
            if fm:
                if "tags" in fm and isinstance(fm["tags"], list):
                    used_tags.update(fm["tags"])
                if "series" in fm and isinstance(fm["series"], list):
                    used_series.update(fm["series"])
                if "projects" in fm and isinstance(fm["projects"], list):
                    used_projects.update(fm["projects"])
            
            posts_img_pattern = r'(/assets/images/posts_img/[^\s\)\"\'\>]+)'
            projects_img_pattern = r'(/assets/images/projects_img/[^\s\)\"\'\>]+)'
            
            used_posts_img_urls.update(re.findall(posts_img_pattern, content))
            used_projects_img_urls.update(re.findall(projects_img_pattern, content))

    # 2. Parse _pages/projects/
    if os.path.exists(projects_dir):
        for filename in os.listdir(projects_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(projects_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                continue
            
            fm = parse_yaml_frontmatter(content)
            if fm and "image" in fm:
                img = fm["image"]
                if img.startswith("/assets/images/projects_img/"):
                    used_projects_img_urls.add(img)
            
            projects_img_pattern = r'(/assets/images/projects_img/[^\s\)\"\'\>]+)'
            used_projects_img_urls.update(re.findall(projects_img_pattern, content))

    used_posts_img_paths = set()
    for url in used_posts_img_urls:
        rel_path = url.replace("/assets/images/posts_img/", "")
        if rel_path.startswith("/"): rel_path = rel_path[1:]
        used_posts_img_paths.add(os.path.normpath(os.path.join(image_dir, rel_path)))
        
    used_projects_img_paths = set()
    for url in used_projects_img_urls:
        rel_path = url.replace("/assets/images/projects_img/", "")
        if rel_path.startswith("/"): rel_path = rel_path[1:]
        used_projects_img_paths.add(os.path.normpath(os.path.join(projects_img_dir_1, rel_path)))
        used_projects_img_paths.add(os.path.normpath(os.path.join(projects_img_dir_2, rel_path)))

    unused_files = {
        "tags": [],
        "series": [],
        "projects": [],
        "posts_img": [],
        "projects_img": []
    }

    # 3. Find unused tags
    if os.path.exists(tags_dir):
        for filename in os.listdir(tags_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(tags_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                continue
            fm = parse_yaml_frontmatter(content)
            taxonomy = fm.get("taxonomy")
            if taxonomy and taxonomy not in used_tags:
                unused_files["tags"].append(os.path.abspath(filepath))

    # 4. Find unused series
    if os.path.exists(series_dir):
        for filename in os.listdir(series_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(series_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                continue
            fm = parse_yaml_frontmatter(content)
            taxonomy = fm.get("taxonomy")
            if taxonomy and taxonomy not in used_series:
                unused_files["series"].append(os.path.abspath(filepath))

    # 5. Find unused projects
    if os.path.exists(projects_dir):
        for filename in os.listdir(projects_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(projects_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                continue
            fm = parse_yaml_frontmatter(content)
            taxonomy = fm.get("taxonomy")
            if taxonomy and taxonomy not in used_projects:
                unused_files["projects"].append(os.path.abspath(filepath))

    # 6. Find unused posts_img
    if os.path.exists(image_dir):
        for root, dirs, files in os.walk(image_dir):
            for filename in files:
                if filename.startswith("."): continue
                filepath = os.path.abspath(os.path.join(root, filename))
                if filepath not in [os.path.abspath(p) for p in used_posts_img_paths]:
                    unused_files["posts_img"].append(filepath)

    # 7. Find unused projects_img
    for p_img_dir in [projects_img_dir_1, projects_img_dir_2]:
        if os.path.exists(p_img_dir):
            for root, dirs, files in os.walk(p_img_dir):
                for filename in files:
                    if filename.startswith("."): continue
                    filepath = os.path.abspath(os.path.join(root, filename))
                    if filepath not in [os.path.abspath(p) for p in used_projects_img_paths]:
                        unused_files["projects_img"].append(filepath)

    return unused_files

def execute_cleanup(files_to_delete: list[str], confirm: bool = False, config_path: str = None) -> dict:
    """
    Deletes the specified unused files. Dry-run by default; pass confirm=True to really delete.
    If a tag page is really deleted, _data/tag_slugs.yml is also updated (never in dry-run).
    Every path is validated by safety.assert_deletable.

    Returns:
        {ok, dry_run, deleted[], skipped[{path, reason}], errors[{path, reason}]}
    """
    try:
        paths = BlogPaths(config=load_config(config_path))
    except Exception as e:
        return {"ok": False, "dry_run": not confirm, "deleted": [], "skipped": [],
                "errors": [{"path": "", "reason": f"Failed to load config: {e}"}]}

    tag_slugs_path = str(paths.tag_slugs_file)
    tags_dir = paths.tags_dir.resolve()

    ok_paths, rejected = validate_batch(files_to_delete, paths=paths)
    result = {"ok": True, "dry_run": not confirm, "deleted": [], "skipped": rejected, "errors": []}

    dirs_to_check = set()
    slugs_to_remove = set()

    for p in ok_paths:
        if not confirm:
            result["deleted"].append(str(p))
            continue
        if p.parent == tags_dir and p.name.startswith("tag-") and p.name.endswith(".md"):
            slugs_to_remove.add(p.name[4:-3])
        try:
            os.remove(p)
            result["deleted"].append(str(p))
            dirs_to_check.add(p.parent)
        except Exception as e:
            logger.error(f"Failed to delete {p}: {e}")
            result["errors"].append({"path": str(p), "reason": str(e)})
            slugs_to_remove.discard(p.name[4:-3])

    if confirm and slugs_to_remove and os.path.exists(tag_slugs_path):
        try:
            with open(tag_slugs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    val = parts[1].strip()
                    if val not in slugs_to_remove:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            with open(tag_slugs_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            logger.error(f"Failed to update tag_slugs.yml: {e}")
            result["errors"].append({"path": tag_slugs_path, "reason": str(e)})

    if confirm:
        remove_empty_dirs(dirs_to_check, paths=paths)
    result["ok"] = not result["errors"]
    return result

import os
import re
import yaml

def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def find_unused_assets(config_path: str = "config.yaml") -> dict:
    """
    Scans the blog repository to find unused tags, series, projects, and images.
    Returns a dictionary of unused files categorized by type.
    """
    try:
        config = load_config(config_path)
    except Exception as e:
        return {"error": f"Failed to load config: {e}"}

    mapping = config.get("mapping", {}).get("default", {})
    post_dir = mapping.get("post_dir", "../wholmesian.github.io/_posts")
    image_dir = mapping.get("image_dir", "../wholmesian.github.io/assets/images/posts_img/")
    image_web_root = mapping.get("image_web_root", "/assets/images/posts_img/")
    
    base_dir = os.path.dirname(post_dir)
    
    tags_dir = os.path.join(base_dir, "_pages", "tags")
    series_dir = os.path.join(base_dir, "_pages", "series")
    projects_dir = os.path.join(base_dir, "_pages", "projects")
    projects_img_dir_1 = os.path.join(base_dir, "assets", "images", "projects_img")
    projects_img_dir_2 = os.path.join(base_dir, "_site", "assets", "images", "projects_img")
    
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

def execute_cleanup(files_to_delete: list[str], config_path: str = "config.yaml") -> str:
    """
    Deletes the specified files from the file system.
    If a tag file is deleted, it also updates _data/tag_slugs.yml to remove the mapping.
    
    Args:
        files_to_delete: A list of absolute file paths to delete.
        config_path: Path to the config file.
    """
    try:
        config = load_config(config_path)
        base_dir = os.path.dirname(config.get("mapping", {}).get("default", {}).get("post_dir", "../wholmesian.github.io/_posts"))
    except:
        base_dir = "../wholmesian.github.io"
        
    tag_slugs_path = os.path.join(base_dir, "_data", "tag_slugs.yml")
    
    deleted_count = 0
    dirs_to_check = set()
    slugs_to_remove = set()
    
    for filepath in files_to_delete:
        if os.path.exists(filepath) and os.path.isfile(filepath):
            if "_pages/tags/tag-" in filepath.replace("\\\\", "/").replace("\\", "/"):
                basename = os.path.basename(filepath)
                if basename.startswith("tag-") and basename.endswith(".md"):
                    slug = basename[4:-3]
                    slugs_to_remove.add(slug)
                    
            try:
                os.remove(filepath)
                deleted_count += 1
                dirs_to_check.add(os.path.dirname(filepath))
            except Exception as e:
                print(f"Failed to delete {filepath}: {e}")
                
    if slugs_to_remove and os.path.exists(tag_slugs_path):
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
            print(f"Failed to update tag_slugs.yml: {e}")

    for d in dirs_to_check:
        if os.path.exists(d) and os.path.isdir(d):
            if not os.listdir(d):
                try:
                    os.rmdir(d)
                except Exception:
                    pass

    return f"Successfully deleted {deleted_count} files."

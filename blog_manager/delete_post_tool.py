import logging
import os
import re

from .paths import BlogPaths, load_config
from .safety import remove_empty_dirs, validate_batch

logger = logging.getLogger(__name__)

def find_files_to_delete(title: str, config_path: str = None) -> dict:
    """
    Finds the markdown file and associated images for a given blog post title.
    
    Args:
        title: The exact title of the blog post to delete (as it appears in the frontmatter).
        config_path: Path to the config.yaml file (default is 'config.yaml').
        
    Returns:
        A dictionary containing 'post_files' and 'image_files' to be deleted.
    """
    try:
        config = load_config(config_path)
    except Exception as e:
        return {"error": f"Failed to load config: {e}"}
        
    mapping = config.get("mapping", {})
    
    post_files_found = []
    candidates = []
    image_files_found = []
    
    paths = BlogPaths(config=config)
    
    for cat in mapping:
        post_dir = str(paths.post_dir(cat))
        image_dir = str(paths.image_dir(cat))
        image_web_root = paths.image_web_root(cat)
        
        if not os.path.exists(post_dir):
            continue
            
        for filename in os.listdir(post_dir):
            if not filename.endswith(".md"):
                continue
                
            filepath = os.path.join(post_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
                
            # Parse frontmatter to find title
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                # Match title field: title: "something" or title: something
                title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', frontmatter, re.MULTILINE)
                if title_match and title_match.group(1) == title:
                    post_files_found.append(os.path.abspath(filepath))
                    cand = {"post_file": os.path.abspath(filepath), "image_files": []}
                    candidates.append(cand)
                    
                    # Extract image URLs from content
                    escaped_root = re.escape(image_web_root)
                    pattern = rf"({escaped_root}[^\s\)\"']+)"
                    image_urls = re.findall(pattern, content)
                    
                    for url in image_urls:
                        # Convert web path to local path
                        if url.startswith(image_web_root):
                            rel_path = url[len(image_web_root):]
                            if rel_path.startswith("/"):
                                rel_path = rel_path[1:]
                            local_img_path = os.path.join(image_dir, rel_path)
                            if os.path.exists(local_img_path):
                                image_files_found.append(os.path.abspath(local_img_path))
                                cand["image_files"].append(os.path.abspath(local_img_path))
    
    if not post_files_found:
        return {"error": f"Could not find any blog post with title '{title}'."}

    if len(post_files_found) > 1:
        return {
            "error": f"Multiple posts ({len(post_files_found)}) match title '{title}'. Ask the user which one to delete.",
            "candidates": candidates,
            "post_files": post_files_found,
            "image_files": image_files_found,
        }

    return {
        "post_files": post_files_found,
        "image_files": image_files_found,
        "candidates": candidates,
    }


def delete_files(files_to_delete: list[str], confirm: bool = False, config_path: str = None) -> dict:
    """
    Deletes the specified files. Dry-run by default; pass confirm=True to really delete.
    Every path is validated by safety.assert_deletable.

    Returns:
        {ok, dry_run, deleted[], skipped[{path, reason}], errors[{path, reason}]}
        In dry-run, `deleted` lists what WOULD be deleted.
    """
    try:
        paths = BlogPaths(config=load_config(config_path))
    except Exception as e:
        return {"ok": False, "dry_run": not confirm, "deleted": [], "skipped": [],
                "errors": [{"path": "", "reason": f"Failed to load config: {e}"}]}

    ok_paths, rejected = validate_batch(files_to_delete, paths=paths)
    result = {"ok": True, "dry_run": not confirm, "deleted": [], "skipped": rejected, "errors": []}

    dirs_to_check = set()
    for p in ok_paths:
        if not confirm:
            result["deleted"].append(str(p))
            continue
        try:
            os.remove(p)
            result["deleted"].append(str(p))
            dirs_to_check.add(p.parent)
        except Exception as e:
            logger.error(f"Failed to delete {p}: {e}")
            result["errors"].append({"path": str(p), "reason": str(e)})

    if confirm:
        remove_empty_dirs(dirs_to_check, paths=paths)
    result["ok"] = not result["errors"]
    return result

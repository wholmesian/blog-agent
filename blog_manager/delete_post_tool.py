import os
import re
import yaml

def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def find_files_to_delete(title: str, config_path: str = "config.yaml") -> dict:
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
    image_files_found = []
    
    for cat, cat_config in mapping.items():
        post_dir = cat_config.get("post_dir", "../wholmesian.github.io/_posts")
        image_dir = cat_config.get("image_dir", "../wholmesian.github.io/assets/images/posts_img/")
        image_web_root = cat_config.get("image_web_root", "/assets/images/posts_img/")
        
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
    
    if not post_files_found:
        return {"error": f"Could not find any blog post with title '{title}'."}
        
    return {
        "post_files": post_files_found,
        "image_files": image_files_found
    }

def delete_files(files_to_delete: list[str]) -> str:
    """
    Deletes the specified files from the file system.
    
    Args:
        files_to_delete: A list of absolute or relative file paths to delete.
        
    Returns:
        A success message indicating how many files were deleted.
    """
    deleted_count = 0
    dirs_to_check = set()
    
    for filepath in files_to_delete:
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                os.remove(filepath)
                deleted_count += 1
                dirs_to_check.add(os.path.dirname(filepath))
            except Exception as e:
                print(f"Failed to delete {filepath}: {e}")
                
    # Clean up empty directories
    for d in dirs_to_check:
        if os.path.exists(d) and os.path.isdir(d):
            if not os.listdir(d):
                try:
                    os.rmdir(d)
                except Exception:
                    pass

    return f"Successfully deleted {deleted_count} files."

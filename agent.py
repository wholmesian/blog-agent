import argparse
import os
import yaml
from notion_parser import NotionParser
from image_handler import ImageHandler
from gemini_formatter import GeminiFormatter
from datetime import datetime

def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def process_blocks_for_images(blocks, image_handler, category, date_str="", title=""):
    """
    재귀적으로 블럭을 순회하며 이미지 블럭을 찾고, 
    이미지를 다운로드한 뒤 해당 블럭의 URL을 로컬 절대 경로로 교체합니다.
    """
    for block in blocks:
        if block.get("type") == "image":
            image_data = block.get("image", {})
            url = None
            if "file" in image_data:
                url = image_data["file"]["url"]
            elif "external" in image_data:
                url = image_data["external"]["url"]
                
            if url:
                print(f"Downloading image from block {block['id']}...")
                local_web_path = image_handler.download_image(url, category, date_str, title)
                
                # Gemini가 프롬프트를 처리할 때 로컬 경로를 인식하도록 덮어쓰기
                if "file" in image_data:
                    block["image"]["file"]["url"] = local_web_path
                elif "external" in image_data:
                    block["image"]["external"]["url"] = local_web_path
                    
        if "children" in block:
            process_blocks_for_images(block["children"], image_handler, category, date_str, title)

def main():
    parser = argparse.ArgumentParser(description="Notion to Markdown Blog Agent using Gemini")
    parser.add_argument("page_id", help="The Notion Page ID or URL to process")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml file")
    args = parser.parse_args()

    print("Initializing components...")
    parser_module = NotionParser()
    image_handler = ImageHandler(config_path=args.config)
    gemini_formatter = GeminiFormatter(config_path=args.config)
    config = load_config(args.config)

    # Notion Page ID 추출 (URL이 들어와도 파싱 가능하도록)
    page_id = args.page_id
    if "?" in page_id:
        page_id = page_id.split("?")[0]
    if "-" in page_id and len(page_id) > 32:
        page_id = page_id.split("-")[-1]

    print(f"Fetching Notion page: {page_id}")
    page = parser_module.get_page(page_id)
    properties = parser_module.extract_properties(page)
    
    print("Fetching blocks...")
    blocks = parser_module.get_blocks(page_id)
    
    # 카테고리 추출 (매핑용)
    category = "default"
    # 노션 프로퍼티 이름이 "Category" 또는 "카테고리" 일 수 있음
    cat_keys = [k for k in properties.keys() if "categor" in k.lower() or "카테고리" in k]
    if cat_keys:
        cat_val = properties[cat_keys[0]]
        if isinstance(cat_val, list) and len(cat_val) > 0:
            category = cat_val[0]
        elif isinstance(cat_val, str):
            category = cat_val

    # 파일명 생성 및 이미지 폴더명용 날짜/제목 추출
    date_str = properties.get("upload_date", properties.get("date", ""))
    if not date_str:
        date_keys = [k for k in properties.keys() if "date" in k.lower() or "날짜" in k]
        date_str = properties.get(date_keys[0], "") if date_keys else ""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    title = properties.get("title", properties.get("Name", "Untitled"))
    
    print(f"Translating title '{title}' to English slug...")
    english_title = gemini_formatter.translate_to_english(title)
    safe_title = "".join([c if c.isalnum() else "-" for c in english_title.replace(" ", "-")])
    if not safe_title:
        safe_title = "untitled"

    print(f"Processing images (Category mapping: {category})...")
    process_blocks_for_images(blocks, image_handler, category, date_str, english_title)
    
    print("Generating Markdown with Gemini API...")
    result = gemini_formatter.format_to_markdown(properties, blocks)
    
    markdown_content = result.get("markdown_content", "")
    new_tags = result.get("new_tags", [])
    new_series = result.get("new_series", [])
    category_path = result.get("category_path", category)
    
    # 저장 경로 결정
    mapping = config.get("mapping", {})
    cat_config = mapping.get(category, mapping.get("default", {}))
    post_dir = cat_config.get("post_dir", "../wholmesian.github.io/_posts")
    
    if not os.path.exists(post_dir):
        os.makedirs(post_dir, exist_ok=True)
        
    # 파일명 생성: YYYY-MM-DD-english-title.md
    filename = f"{date_str[:10]}-{safe_title}.md"
    file_path = os.path.join(post_dir, filename)
    
    print(f"Saving markdown to {file_path} ...")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    def is_taxonomy_in_slugs(taxonomy):
        slugs_file = "../wholmesian.github.io/_data/tag_slugs.yml"
        if os.path.exists(slugs_file):
            with open(slugs_file, "r", encoding="utf-8") as rf:
                for line in rf:
                    if line.strip().startswith(f"{taxonomy}:"):
                        return True
        return False

    def write_tag_slug_mapping(taxonomy, english_title):
        slugs_file = "../wholmesian.github.io/_data/tag_slugs.yml"
        if os.path.exists(slugs_file):
            with open(slugs_file, "r", encoding="utf-8") as rf:
                content = rf.read()
            with open(slugs_file, "a", encoding="utf-8") as sf:
                if content and not content.endswith("\n"):
                    sf.write("\n")
                sf.write(f"{taxonomy}: {english_title}\n")

    if new_tags:
        print(f"Identified new tags to create: {len(new_tags)}")
        tags_dir = "../wholmesian.github.io/_pages/tags"
        os.makedirs(tags_dir, exist_ok=True)
        for tag_obj in new_tags:
            taxonomy = tag_obj.get("taxonomy", "")
            eng_title = tag_obj.get("english_title", taxonomy)
            if not taxonomy:
                continue
                
            if is_taxonomy_in_slugs(taxonomy):
                # Use a default for non-interactive environments or just assume 'N'
                print(f"\n[!] Tag taxonomy '{taxonomy}' already exists in tag_slugs.yml.")
                # If we want to allow override via some flag, we can add it later.
                # For now, let's just skip to avoid blocking.
                print(f"Skipping tag creation for '{taxonomy}'.")
                continue
            
            tag_safe = "".join([c if c.isalnum() else "-" for c in eng_title.lower().replace(" ", "-")])
            tag_file = os.path.join(tags_dir, f"tag-{tag_safe}.md")
            if not os.path.exists(tag_file):
                print(f"Creating tag page: {tag_file}")
                with open(tag_file, "w", encoding="utf-8") as tf:
                    tf.write(f"---\ntitle: \"{taxonomy}\"\nlayout: tag\npermalink: /tags/{tag_safe}/\nauthor_profile: true\ntaxonomy: {taxonomy}\nsidebar:\n  nav: \"categories\"\n---\n")
                
                if taxonomy != eng_title and not is_taxonomy_in_slugs(taxonomy):
                    write_tag_slug_mapping(taxonomy, eng_title)

    if new_series:
        print(f"Identified new series to create: {len(new_series)}")
        series_dir = "../wholmesian.github.io/_pages/series"
        os.makedirs(series_dir, exist_ok=True)
        for series_obj in new_series:
            taxonomy = series_obj.get("taxonomy", "")
            korean_title = series_obj.get("korean_title", taxonomy)
            if not taxonomy:
                continue
            
            series_safe = "".join([c if c.isalnum() else "-" for c in taxonomy.lower().replace(" ", "-")])
            series_file = os.path.join(series_dir, f"series-{series_safe}.md")
            if not os.path.exists(series_file):
                print(f"Creating series page: {series_file}")
                with open(series_file, "w", encoding="utf-8") as sf:
                    sf.write(f"---\ntitle: \"{korean_title}\"\nlayout: series\npermalink: /series/{series_safe}/\nauthor_profile: true\nsidebar:\n  nav: \"categories\"\n---\n")

    print("\n✅ Blog post generation completed successfully!")

if __name__ == "__main__":
    main()

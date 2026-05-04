import os
import requests
import yaml
import uuid
from urllib.parse import urlparse

class ImageHandler:
    """
    Notion 문서에 포함된 이미지를 다운로드하고, 설정된 웹루트 경로로 변환하는 클래스입니다.
    """
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def download_image(self, url: str, category: str = "default", date_str: str = "", title: str = "") -> str:
        """
        주어진 URL에서 이미지를 다운로드하여 로컬에 저장한 후, 마크다운 본문에 쓰일 절대 경로를 반환합니다.
        """
        mapping = self.config.get("mapping", {})
        # 카테고리가 맵핑에 없으면 default 설정 사용
        cat_config = mapping.get(category, mapping.get("default", {}))
        
        image_dir = cat_config.get("image_dir", "./images")
        web_root = cat_config.get("image_web_root", "/images")
        
        # 포스트 날짜 폴더 경로 설정 (YYYY-MM-DD 형식 보장)
        date_folder = date_str[:10] if date_str else "1970-01-01"
        target_dir = os.path.join(image_dir, date_folder)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # URL의 path 부분에서 확장자 추출 (노션 AWS 임시 URL 대응)
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext:
            ext = ".png" # 확장자가 없으면 기본값 png
            
        # 파일명 구성 (title.extension 또는 여러 장일 경우 title_1.extension)
        safe_title = "".join([c if c.isalnum() else "-" for c in title.lower().replace(" ", "-")])
        if not safe_title:
            safe_title = "image"
            
        if not hasattr(self, 'image_counters'):
            self.image_counters = {}
            
        base_name = f"{date_folder}-{safe_title}"
        if base_name not in self.image_counters:
            self.image_counters[base_name] = 1
        else:
            self.image_counters[base_name] += 1
            
        count = self.image_counters[base_name]
        filename = f"{safe_title}_{count}{ext}" if count > 1 else f"{safe_title}{ext}"
        
        local_path = os.path.join(target_dir, filename)
        
        # 다운로드 실행
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            print(f"Warning: Failed to download image from {url}")
            return url # 실패 시 원본 링크 반환
                
        # 마크다운에 삽입될 웹루트 절대 경로 문자열 반환 (예: /assets/images/posts_img/2026-04-25/title.png)
        web_path = f"{web_root.rstrip('/')}/{date_folder}/{filename}"
        return web_path

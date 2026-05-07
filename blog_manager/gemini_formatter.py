import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiFormatter:
    """
    Gemini API를 사용하여 Notion의 원시 데이터를 정제된 마크다운과 
    Frontmatter가 포함된 문서로 변환하고 추가적인 추론(태그, 카테고리 등)을 수행하는 클래스입니다.
    """
    def __init__(self, config_path="config.yaml"):
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables. Please check your .env file.")
        
        genai.configure(api_key=gemini_key)
        
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        gemini_config = self.config.get("gemini", {})
        model_name = gemini_config.get("model_name", "gemini-1.5-pro")
        
        system_instruction = gemini_config.get("system_instruction", "")
        instruction_file = gemini_config.get("system_instruction_file")
        if instruction_file and os.path.exists(instruction_file):
            with open(instruction_file, "r", encoding="utf-8") as f:
                system_instruction = f.read()
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )

    def translate_to_english(self, text: str) -> str:
        """한글 등 비영어권 문자열을 URL 친화적인 영어 slug로 번역합니다."""
        if all(ord(c) < 128 for c in text):
            return text
            
        prompt = f"Translate the following Korean title into a short, concise, and URL-friendly English title. Just return the translated English string without any punctuation or extra formatting.\n\nTitle: {text}"
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1)
        )
        return response.text.strip().lower()

    def format_to_markdown(self, properties: dict, blocks: list) -> dict:
        """
        프로퍼티와 전처리된 블럭(이미지 경로가 절대경로로 변경된 상태) 데이터를 바탕으로
        Gemini에게 마크다운 생성과 메타데이터 추론을 요청합니다.
        
        반환값은 딕셔너리 형태이며, 아래의 키를 포함합니다:
        - markdown_content: Frontmatter가 포함된 최종 마크다운 텍스트
        - new_tags: 새롭게 생성해야 할 태그 목록
        - category_path: 추론된 카테고리 경로
        """
        
        prompt = f"""
다음은 노션에서 추출한 페이지의 프로퍼티(메타데이터)와 본문 블럭 데이터입니다.

[Properties]
{json.dumps(properties, ensure_ascii=False, indent=2)}

[Blocks (본문 내용)]
{json.dumps(blocks, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 Jekyll 등의 정적 사이트 생성기에서 바로 사용할 수 있는 완벽한 마크다운 문서를 작성해주세요.
- 파일 최상단에 YAML Frontmatter를 반드시 포함하세요. (title, date, categories, tags 등)
- 본문의 구조(제목, 리스트, 인용구, 코드, 이미지 링크 등)를 마크다운 문법으로 아름답게 구성하세요.
- 주어진 카테고리(혹은 내용)를 기반으로 적절한 상위/하위 카테고리 계층 구조를 추론해주세요.
- 주어진 태그 중 블로그에 새롭게 추가해야 할 것 같은 의미있는 태그를 식별해주세요.

결과는 반드시 아래의 JSON 형식으로만 출력해주세요. JSON 객체 외에 어떠한 텍스트도 출력하지 마세요.
{{
    "markdown_content": "---\\nlayout: post\\ntitle: ...\\n---\\n\\n본문 내용...",
    "new_tags": [{{"taxonomy": "태그원문", "english_title": "tag-slug"}}],
    "new_series": [{{"taxonomy": "시리즈원문", "english_title": "번역된 영어 제목(URL용)"}}],
    "category_path": "상위카테고리/하위카테고리"
}}
"""
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=self.config.get("gemini", {}).get("temperature", 0.2),
                response_mime_type="application/json"
            )
        )
        
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # 모델이 간혹 ```json 형식으로 감싸서 보내는 경우를 대비한 Fallback
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            
            try:
                return json.loads(text.strip())
            except Exception as e:
                raise RuntimeError(f"Failed to parse Gemini response as JSON: {e}\nResponse: {response.text}")

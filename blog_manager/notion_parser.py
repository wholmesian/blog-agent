import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class NotionParser:
    """
    Notion API를 통해 페이지의 프로퍼티(메타데이터)와 하위 블럭(본문)을 추출하는 클래스입니다.
    """
    def __init__(self):
        notion_key = os.getenv("NOTION_API_KEY")
        if not notion_key:
            raise ValueError("NOTION_API_KEY is not set in environment variables. Please check your .env file.")
        self.client = Client(auth=notion_key)

    def get_page(self, page_id: str) -> dict:
        """페이지 객체(메타데이터 포함)를 가져옵니다."""
        return self.client.pages.retrieve(page_id=page_id)

    def get_blocks(self, block_id: str) -> list:
        """
        페이지 또는 블럭의 하위 블럭들을 모두 가져옵니다. (페이징 처리 포함)
        하위 블럭이 존재할 경우 재귀적으로 'children' 키에 담아 반환합니다.
        """
        blocks = []
        cursor = None
        while True:
            response = self.client.blocks.children.list(block_id=block_id, start_cursor=cursor)
            blocks.extend(response.get("results", []))
            cursor = response.get("next_cursor")
            if not cursor:
                break
                
        # 자식 블럭이 있는 경우 재귀적으로 가져와서 구조화
        for block in blocks:
            if block.get("has_children"):
                block["children"] = self.get_blocks(block["id"])
                
        return blocks

    def extract_properties(self, page: dict) -> dict:
        """
        페이지의 properties(노션 데이터베이스 컬럼)에서 유효한 값을 추출하여 딕셔너리로 반환합니다.
        """
        properties = page.get("properties", {})
        extracted = {}
        for key, prop in properties.items():
            prop_type = prop.get("type")
            if prop_type == "title":
                extracted[key] = "".join([t["plain_text"] for t in prop["title"]])
            elif prop_type == "rich_text":
                extracted[key] = "".join([t["plain_text"] for t in prop["rich_text"]])
            elif prop_type == "select" and prop["select"]:
                extracted[key] = prop["select"]["name"]
            elif prop_type == "multi_select":
                extracted[key] = [s["name"] for s in prop["multi_select"]]
            elif prop_type == "date" and prop["date"]:
                extracted[key] = prop["date"]["start"]
            elif prop_type == "url":
                extracted[key] = prop["url"]
            elif prop_type == "checkbox":
                extracted[key] = prop["checkbox"]
            elif prop_type == "number":
                extracted[key] = prop["number"]
            elif prop_type == "created_time":
                extracted[key] = prop["created_time"]
            elif prop_type == "last_edited_time":
                extracted[key] = prop["last_edited_time"]
            # 추가적인 타입이 필요하면 이 곳에 확장
        return extracted

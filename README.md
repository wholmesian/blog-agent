# blog-agent
wholmesian.github.io 관리를 돕는 Agentic AI 도구

## 🛠 구현된 도구 (Implemented Tools)

현재 `blog_manager` 에이전트에는 블로그 관리를 자동화하기 위한 세 가지 핵심 도구가 구현되어 있습니다.

### 1. Notion to Jekyll 변환 도구 (`convert_notion_to_jekyll`)
- **기능**: 사용자가 제공한 Notion 페이지 ID 또는 URL을 기반으로 페이지 내용을 파싱하고, Jekyll 블로그용 Markdown 포스트로 변환합니다.
- **특징**:
  - 노션 본문 블록 및 메타데이터 추출
  - 본문 내 이미지를 다운로드하여 로컬 및 웹루트 경로로 자동 매핑
  - Gemini API를 활용하여 제목을 영어 Slug로 변환 및 프론트매터 자동 생성
  - 포스트에 포함된 새로운 태그(Tag) 및 시리즈(Series) 페이지 자동 생성

### 2. 블로그 포스트 검색 도구 (`find_files_to_delete`)
- **기능**: 삭제하고자 하는 블로그 포스트의 제목(title)을 입력받아, 해당하는 마크다운 파일과 해당 포스트에서 사용된 이미지 파일들을 탐색합니다.
- **특징**:
  - 사용자의 실수로 인한 삭제를 방지하기 위한 2단계 삭제 프로세스의 첫 번째 단계
  - Frontmatter를 분석하여 정확한 포스트를 찾고, 본문 내에서 로컬 이미지 참조를 추출

### 3. 블로그 포스트 삭제 도구 (`delete_files`)
- **기능**: `find_files_to_delete` 도구가 반환한 파일 목록을 실제로 파일 시스템에서 삭제합니다.
- **특징**:
  - 사용자로부터 명시적인 확인(Confirmation)을 받은 후에만 실행
  - 마크다운 파일 및 이미지 파일을 삭제하며, 이미지가 삭제된 후 빈 폴더가 남으면 함께 정리

<br>

## ⚙️ 시스템 워크플로우 시각화

```mermaid
flowchart TD
    User(["👤 사용자"])

    subgraph AgentLoop["🔄 Agentic Loop"]
        LLM["🤖 Blog Agent\nGemini 2.5 Flash · Google ADK\n\n자연어 이해 & 도구 선택"]
    end

    subgraph T1["🛠 Tool 1 · convert_notion_to_jekyll"]
        N1["NotionParser\n페이지 메타데이터 & 블록 추출"]
        N2["ImageHandler\n이미지 다운로드 & 경로 매핑"]
        N3["GeminiFormatter\n제목 슬러그 변환 & Markdown 생성"]
        N4["파일 저장 & 새 태그·시리즈 페이지 생성"]
        N1 --> N2 --> N3 --> N4
    end

    subgraph T2["🗑 Tool 2 · find_files_to_delete + delete_files"]
        D1["find_files_to_delete\nFrontmatter 스캔 & 이미지 경로 추출"]
        D2{{"⚠️ 사용자 확인\nAgent가 파일 목록 제시"}}
        D3["delete_files\n.md & 이미지 파일 삭제\n빈 디렉토리 정리"]
        D1 --> D2 -->|"Yes"| D3
    end

    subgraph Jekyll["📁 Jekyll 블로그 (wholmesian.github.io)"]
        J1["_posts/"]
        J2["assets/images/posts_img/"]
        J3["_pages/tags/ & _pages/series/"]
    end

    User -->|"자연어 요청\nNotion URL 또는 포스트 제목"| LLM
    LLM -->|"포스트 발행"| T1
    LLM -->|"포스트 삭제"| T2
    N4 --> J1
    N4 --> J2
    N4 --> J3
    D3 --> J1
    D3 --> J2
    T1 -->|"결과 반환"| LLM
    T2 -->|"결과 반환"| LLM
    LLM -->|"결과 보고 & 확인 요청"| User
    User -->|"확인 (Yes / No)"| LLM
```

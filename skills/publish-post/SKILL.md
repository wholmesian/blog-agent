---
name: publish-post
description: Notion 페이지를 Jekyll 블로그 포스트로 발행합니다. "이 노션 페이지를 블로그로 만들어줘", "노션 글 발행해줘", "포스트 올려줘", "Notion URL을 포스트로 변환" 같은 요청에 사용. Use when asked to publish/convert a Notion page (URL or ID) into a blog post for the Jekyll blog.
---

# 포스트 발행 (Notion -> Jekyll)

포맷 규칙(프론트매터, 본문, 캡션, 태그/시리즈)은 repo 루트의 `AGENTS.md` §1–§5를 따릅니다. 도구는 MCP(`notion_fetch` 등)가 연결되어 있으면 MCP로, 아니면 CLI(`venv/bin/python -m blog_manager <cmd>`, JSON은 stdout)로 호출합니다. `.env`는 읽거나 출력하지 않습니다.

## 절차

1. **조회**: `notion-fetch <id_or_url>` 실행. 결과의 `ok`가 false면 `error`를 사용자에게 알리고 중단.
2. **slug 결정**: 결과에 `slug_required: true`가 있으면(비영어 제목) 제목을 바탕으로 짧고 URL 친화적인 영어 slug(`A-Z a-z 0-9 -`만, 소문자 권장)를 정해 `notion-fetch <id_or_url> --slug <slug>`로 다시 실행. 이때 이미지가 다운로드됩니다.
3. **마크다운 작성**: 응답의 `markdown_draft`(결정적 변환 초안), `properties`, `images`(캡션, `web_path`), `upload_date`, `modified_date`, `category`를 바탕으로 최종본을 작성합니다.
   - 맨 위에 AGENTS.md §1 형식의 프론트매터 (title, excerpt는 큰따옴표, categories 1개, tags, projects/series는 있을 때만, permalink=`{category_link}/{permalink_code}`, toc/toc_sticky true, date=upload_date, last_modified_at=modified_date).
   - 본문은 초안의 구조를 유지하며 다듬되, 이미지 경로는 `images[].web_path`를 쓰고 캡션은 이미지 바로 아래 `<p align="center" style="color:gray; font-size: 0.8em;">캡션</p>`로 반드시 포함 (AGENTS.md §2).
   - `category_link`는 `../wholmesian.github.io/_data/navigation.yml`에서 확인.
4. **임시 파일 저장**: 작업용 임시 디렉토리(예: 세션 scratchpad)에 `<date>-<slug>.md`로 저장. 블로그 repo에 직접 쓰지 않습니다.
5. **검증**: `post-validate <tmpfile>`.
   - `errors`가 있으면 원인을 고쳐 다시 검증하고, 통과할 때까지 반복.
   - **카테고리가 navigation.yml에 없거나 프로젝트 페이지가 없으면(`missing_projects`) 수정하지 말고 중단**하고 사용자에게 수동 추가가 필요하다고 알립니다 (AGENTS.md §5).
   - `missing_tags` / `missing_series`는 오류가 아니라 다음 단계의 입력입니다.
6. **태그/시리즈 생성**: `missing_tags`/`missing_series`가 있으면 `taxonomy-ensure --tag "태그=english_title" ... --series "시리즈=english_title"`. 영어 이름은 AGENTS.md §3–§4대로 번역해 정합니다. `tag_slugs.yml`은 이 도구가 갱신하므로 직접 편집 금지.
7. **저장**: `post-write --slug <slug> --date <upload_date> --file <tmpfile>`. 같은 이름의 파일이 이미 있다는 오류가 나면 덮어쓸지 사용자에게 먼저 묻고, 승인 시에만 `--overwrite`.
8. **보고**: 저장된 포스트 경로, 새로 만든 태그/시리즈 페이지, 다운로드된 이미지 수, 남은 경고를 사용자에게 요약합니다.

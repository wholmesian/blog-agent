---
name: cleanup-blog
description: 블로그에서 더 이상 쓰지 않는 태그, 시리즈, 프로젝트 페이지와 이미지를 찾아 선택적으로 삭제합니다. "블로그 정리해줘", "안 쓰는 태그/이미지 지워줘", "미사용 에셋 정리" 같은 요청에 사용. Use when asked to clean up the blog or find/remove unused tags, series, projects, or images.
---

# 블로그 정리 (미사용 에셋)

도구는 MCP(`find_unused_assets`, `execute_cleanup`)가 연결되어 있으면 MCP로, 아니면 CLI(`venv/bin/python -m blog_manager <cmd>`)로 호출합니다.

## 절차

1. **탐색**: `find-unused-assets` (읽기 전용). `_posts/`에서 참조되지 않는 파일을 `tags`, `series`, `projects`, `posts_img`, `projects_img` 분류로 반환합니다.
2. **번호 목록 제시**: 분류별로 묶어 **전체에 걸친 일련번호**를 붙여 보여줍니다 (경로는 blog_root 기준 상대 경로로 줄여 써도 되지만 선택 후 실제 호출에는 원래 절대 경로를 사용). 항목이 없으면 정리할 것이 없다고 알리고 종료.
   - `projects` 항목은 사용자가 수동 관리하는 자산이므로 "프로젝트 페이지는 직접 관리하는 항목입니다"라고 표시하고, 사용자가 명시적으로 고른 경우에만 포함합니다.
3. **선택 요청**: 어떤 항목을 지울지 묻습니다 (`all`, `none`, 또는 번호/범위, 예: `1,3,5-8`). 기본값은 삭제하지 않음입니다. `none`이면 종료.
4. **(선택) 사전 점검**: 선택된 경로로 `execute-cleanup <path>...`(`--yes` 없이) dry-run 실행 후 결과를 보여주고, 필요하면 최종 확인을 한 번 더 받습니다.
5. **삭제**: **사용자가 선택한 항목만** `execute-cleanup <path>... --yes` (MCP: `execute_cleanup(files, confirm=true)`). 이 워크플로우에서는 `delete-files`를 쓰지 않습니다 — `execute-cleanup`이 삭제된 태그 페이지에 대응하는 `tag_slugs.yml` 항목도 동기화하기 때문입니다.
6. **보고**: `deleted`, `skipped`(허용 경로 밖 등), `errors`를 요약합니다. `tag_slugs.yml`은 직접 편집하지 않습니다.

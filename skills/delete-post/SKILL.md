---
name: delete-post
description: 블로그 포스트와 그 포스트에서 쓰던 이미지를 삭제합니다. "이 포스트 지워줘", "[제목] 글이랑 이미지 삭제해줘", "포스트 삭제" 같은 요청에 사용. Use when asked to delete a blog post and its images by title.
---

# 포스트 삭제

도구는 MCP(`find_files_to_delete`, `delete_files`)가 연결되어 있으면 MCP로, 아니면 CLI(`venv/bin/python -m blog_manager <cmd>`)로 호출합니다. 삭제는 되돌릴 수 없으므로 반드시 사용자 확인 후에만 진행합니다.

## 절차

1. **탐색**: `find-files-to-delete "<title>"` (읽기 전용). 제목은 사용자가 말한 그대로 사용.
   - 결과가 `Could not find ...` 오류면 사용자에게 알리고 제목 확인을 요청.
   - `Multiple posts ... match` 오류(`candidates` 포함)면 후보를 보여주고 어떤 것을 지울지 사용자에게 묻고, 선택된 포스트의 파일만 이후 단계 대상으로 삼습니다.
2. **목록 제시**: 찾은 마크다운 파일(`post_files`)과 이미지 파일(`image_files`)을 전체 경로와 함께 사용자에게 보여주고 **삭제해도 되는지 명시적으로 묻습니다.** 확인 전에는 삭제 도구를 호출하지 않습니다.
3. **확인 해석**: 사용자가 "네/예/yes" 등으로 명확히 승인한 경우에만 진행. 모호하거나 일부만 승인하면 승인된 항목만 대상으로 하거나 다시 묻습니다.
4. **(선택) 사전 점검**: `delete-files <path>...`(`--yes` 없이)는 dry-run이며 무엇이 삭제될지/거부될지 보여줍니다.
5. **삭제**: 승인된 경로만 인자로 `delete-files <path>... --yes` (MCP: `delete_files(files, confirm=true)`).
6. **보고**: `deleted`, `skipped`(허용 경로 밖 등으로 거부된 항목과 사유), `errors`를 사용자에게 요약. 이미지 삭제 후 빈 폴더는 도구가 정리합니다.

## 주의

- 목록에 없던 파일을 추가로 삭제하지 않습니다.
- 다른 포스트가 같은 이미지를 참조할 수 있는지 의심되면(예: 공유 이미지) 사용자에게 알립니다.

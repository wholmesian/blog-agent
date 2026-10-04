# blog-agent 에이전트 지침

이 repo(`blog-agent`)는 Notion 페이지를 Jekyll 블로그(`../wholmesian.github.io`) 포스트로 발행하고, 기존 포스트 삭제와 미사용 에셋 정리를 돕는 **결정적(deterministic) 도구 모음**입니다. 이 repo에서 작업하는 코딩 에이전트(Claude Code, Codex, Antigravity 등)인 당신이 판단과 글쓰기(영어 slug 결정, 프론트매터 작성, 본문 다듬기)를 맡고, 파일 입출력·검증·삭제는 아래 도구가 맡습니다. 아래 §0–§5는 블로그 포맷 규칙으로, 포스트를 작성할 때 반드시 따릅니다.

## Tools

호스트에 `blog-agent` MCP 서버가 연결되어 있으면 MCP 도구(snake_case)를 쓰고, 아니면 CLI를 씁니다. CLI는 repo 루트에서 `venv/bin/python -m blog_manager <command>`로 실행하며, 결과는 stdout의 JSON, 로그는 stderr입니다. 전역 옵션 `--config PATH`.

| CLI 명령 | MCP 도구 | 설명 |
|---|---|---|
| `notion-fetch <id_or_url> [--slug S]` | `notion_fetch` | 프로퍼티/블록 조회, 이미지 다운로드·경로 치환, 캡션 보존. `markdown_draft`(결정적 변환 초안) 반환. 비영어 제목이면 `slug_required: true`로 slug를 요구 |
| `post-write --slug S --date YYYY-MM-DD (--file PATH \| --stdin) [--overwrite]` | `post_write` | `_posts/YYYY-MM-DD-slug.md` 저장. 기존 파일은 `--overwrite` 없이는 거부 |
| `taxonomy-ensure [--tag 태그=english_title]... [--series 시리즈=english_title]...` | `taxonomy_ensure` | 없는 태그/시리즈 페이지 생성, 필요 시 `tag_slugs.yml` 갱신 (멱등) |
| `post-validate <file>` | `post_validate` | §1–§2 규칙 검증(읽기 전용). 오류/경고, 페이지 없는 tags/series/projects 목록 반환 |
| `find-files-to-delete <title>` | `find_files_to_delete` | 제목으로 포스트와 사용 이미지 탐색(읽기 전용) |
| `delete-files <path>... [--yes]` | `delete_files(confirm)` | 기본 dry-run, `--yes`/`confirm=true`일 때만 실제 삭제 |
| `find-unused-assets` | `find_unused_assets` | 미사용 tags/series/projects/이미지 탐색(읽기 전용) |
| `execute-cleanup <path>... [--yes]` | `execute_cleanup(confirm)` | 기본 dry-run, 확인 시 삭제 + `tag_slugs.yml` 동기화 |

- `notion-fetch`는 결정적 변환기가 만든 `markdown_draft`를 돌려줍니다. 이것은 **초안**이며, 프론트매터 작성과 최종 다듬기는 당신(호스트 LLM)의 몫입니다.
- 삭제류 도구는 `blog_root` 하위의 허용 디렉토리(`_posts`, `_pages`, `assets/images` 등)만 대상으로 하며 그 밖의 경로는 거부됩니다.

## Workflows

작업 종류에 맞는 절차서를 먼저 읽고 그대로 따르세요. (Claude Code는 `.claude/skills/`, 그 외 호스트는 `.agents/skills/`를 지원하면 자동 로드되고, 아니면 아래 파일을 직접 읽으세요.)

- 포스트 발행(Notion → Jekyll): [skills/publish-post/SKILL.md](skills/publish-post/SKILL.md)
- 포스트 삭제: [skills/delete-post/SKILL.md](skills/delete-post/SKILL.md)
- 블로그 정리(미사용 에셋): [skills/cleanup-blog/SKILL.md](skills/cleanup-blog/SKILL.md)

## Rules

- 카테고리와 프로젝트는 **절대 직접 생성/수정하지 않습니다.** 필요하면 작업을 멈추고 사용자에게 알립니다. (§5)
- 사용자가 삭제 대상 목록을 본 뒤 **명시적으로 확인하기 전에는 어떤 것도 삭제하지 않습니다.** `--yes`/`confirm=true`는 확인받은 항목에만 사용합니다.
- `.env`는 읽거나 출력하지 않습니다. (Notion 키는 도구가 알아서 읽습니다.)
- `tag_slugs.yml`을 직접 편집하지 않습니다. `taxonomy-ensure`를 사용합니다.
- 태그/시리즈 페이지는 수동으로 만들지 않고 `taxonomy-ensure`로 만듭니다.
- `post-write` 전에 항상 임시 파일로 `post-validate`를 통과시킵니다.
- 영어 slug와 프론트매터는 호스트 LLM(당신)이 작성합니다. slug는 `A-Z a-z 0-9 -`만 사용합니다.
- `../wholmesian.github.io`는 위 도구를 통해서만 변경합니다.

## 0. 블로그 기본 소개

이 블로그는 `../wholmesian.github.io` 디렉토리에 존재하는 jekyll 블로그입니다. 

이 블로그의 카테고리와 상위 메뉴는 `../wholmesian.github.io/_data/navigation.yml`파일에서 확인할 수 있습니다.

태그의 한국어 taxonomy와 permalink 사이에 혼선이 생기는 것을 막기 위해 `../wholmesian.github.io/_data/tag_slugs.yml` 파일을 만들어 두었습니다.

`../wholmesian.github.io/_data/_pages/` 밑에는 카테고리(`category`), 시리즈(`series`), 태그(`tags`), 프로젝트(`projects`), 그리고 포스트(`_posts`) 페이지를 위한 디렉토리들이 들어있습니다.

## 1. Frontmatter 작성 규칙
파일 최상단에 YAML 형식의 Frontmatter를 정확히 생성하세요. 아래의 템플릿 예시를 참고하여 필요한 메타데이터(제목, 날짜, 카테고리, 태그, 프로젝트 등)를 모두 포함해야 합니다.

```yaml
---
title: "노션에서 추출한 제목"
excerpt: "노션 문서의 excerpt 속성을 그대로 가져와서 큰따옴표로 감싸서 작성"

categories:
  - Some Category
tags:
  - 태그1
  - tag2
projects:
  - projects-1
series:
  - series1

permalink: /menu/category/post_link

toc: true
toc_sticky: true

date: YYYY-MM-DD
last_modified_at: YYYY-MM-DD
---
```

frontmatter의 각 항목들은 모두 노션 페이지의 프로퍼티로부터 가져오면 됩니다. 각 항목에 대한 설명은 아래와 같습니다. 
- title: 노션 페이지의 제목을 가져옵니다.
- excerpt: 노션 페이지의 excerpt 프로퍼티 내용을 그대로 가져옵니다. 큰따옴표로 감싸서 작성해야 합니다.
- categories: 노션 페이지의 category 프로퍼티를 그대로 가져옵니다. 카테고리는 늘 1개이며, 띄어쓰기가 들어갈 수 있습니다. 카테고리에는 따옴표를 넣지 않습니다. 카테고리는 항상 영어로 작성되어 있습니다.
- tags: 노션 페이지의 tag 프로퍼티를 그대로 가져옵니다. 태그는 여러 개 존재하는 경우에는 태그를 모두 가져와 하이픈을 이용한 불렛 포인트 형식으로 나열합니다. 태그에는 따옴표를 넣지 않습니다. 
- project: 노션 페이지의 project 프로퍼티를 그대로 가져옵니다. project는 최대 1개이며, 아예 존재하지 않는 경우가 많습니다. 프로젝트에도 따옴표를 넣지 않고 영어로 작성합니다.
- series: 노션 페이지의 series 프로퍼티를 그대로 가져옵니다. series는 최대 1개이며, 아예 존재하지 않는 경우가 많습니다. 시리즈에도 따옴표를 넣지 않고 영어로 작성합니다.
- date: 노션 페이지의 upload_date 프로퍼티를 가져와 YYYY-MM-DD 형식으로 적습니다.
- last_modified_at: 노션 페이지의 modified_date 프로퍼티를 가져와 YYYY-MM-DD 형식으로 적습니다.
- permalink: 노션 페이지의 permalink_code 프로퍼티를 가져와 `{category_link}/{permalink_code}` 형식으로 작성합니다. 예를 들어, permalink_code가 `sample`이고 PseudoLab 카테고리라면 해당 문서의 permalink는 `/club/pseudolab/sample` 입니다. permalink에는 따옴표를 두르지 않습니다.
- toc와 toc_sticky는 항상 true로 설정합니다.

## 2. 본문 변환 규칙
1. 제공된 텍스트의 구조(헤딩, 목록, 코드 블록, 인용구 등)를 유지하며 아름다운 마크다운으로 변환하세요.
2. 본문에 포함된 이미지 경로(url)는 제공된 로컬/웹루트 절대 경로로 변경되어야 합니다.
3. 이미지에 캡션(caption)이 존재하는 경우 절대 누락하지 말고, 아래 예시와 같이 `<p>` 태그를 사용하여 가운데 정렬, 회색, 약간 작은 글씨의 특별한 디자인으로 이미지 바로 아래에 삽입하세요.
   ```html
   ![이미지 설명](/assets/images/posts_img/2026-04-25/image_name.png)
   <p align="center" style="color:gray; font-size: 0.8em;">여기에 캡션 내용을 적어주세요</p>
   ```

## 3. 새로운 태그 추가 규칙
1. 만약 `_pages/tags/` 폴더에 관련된 태그가 없다면 새로운 태그 페이지를 생성해야 합니다. 존재하지 않는 태그가 여러 개라면 각각에 대한 태그 페이지를 모두 생성해야 합니다.

2. 태그 페이지의 제목은 `tag-{영어이름}.md` 형식으로 작성합니다.

3. 태그 페이지는 markdown 형식이며, 아래 프론트매터 형식을 따릅니다.
```
---
title: "태그 1"
layout: tag
permalink: /tags/tag-1/
author_profile: true
taxonomy: 태그 1
sidebar:
  nav: "categories"
---
```

각 항목의 내용은 아래와 같습니다.
- layout, author_profile, sidebar는 위와 같이 고정합니다.
- title: 노션 페이지의 tags 프로퍼티에 존재하는 태그의 이름을 그대로 사용합니다. 큰따옴표로 감싸서 작성해야 합니다. 영어가 아닐 수 있습니다.
- permalink: title을 적절히 번역하여 `/tags/{english_title}` 형식으로 작성합니다. 예를 들어, 태그 title이 `샘플`, 이를 번역한 영어 제목이 "sample"이라면 permalink는 `/tags/sample` 입니다. permalink에는 따옴표를 두르지 않습니다.
- taxonomy: 노션 페이지의 tags 프로퍼티에 존재하는 태그의 이름을 그대로 가져옵니다. 큰따옴표를 사용하지 않습니다. 영어가 아닐 수 있습니다.

4. 만약 title과 taxonomy가 다르다면 (영어/한국어로 번역한 경우 포함) `../wholmesian.github.io/_data/tag_slugs.yml` 파일을 수정해서 두 속성을 대응시켜주어야 합니다.

## 4. 새로운 시리즈 추가 규칙
1. 만약 `../wholmesian.github.io/_pages/series/` 폴더에 관련된 시리즈가 없다면 새로운 시리즈 페이지를 생성해야 합니다.

2. 시리즈 페이지의 제목은 `series-{영어이름}.md` 형식으로 작성합니다.

3. 시리즈 페이지는 markdown 형식이며, 아래 프론트매터 형식을 따릅니다.
```
---
title: "시리즈 1"
layout: series
permalink: /series/series1/
author_profile: true
taxonomy: 시리즈 1
sidebar:
  nav: "categories"
---
```

- layout, author_profile, sidebar는 위와 같이 고정합니다.
- taxonomy: 노션 페이지의 series 프로퍼티에 존재하는 시리즈의 이름을 그대로 사용합니다. 큰따옴표를 사용하지 않습니다.
- title: taxonomy를 그대로 사용합니다. 큰따옴표를 둘러야 합니다.
- permalink: taxonomy를 적절히 번역하여 `/series/{translated-taxonomy}` 형식으로 작성합니다. 예를 들어, taxonomy가 "샘플"이라면 이를 번역한 영어 제목이 "sample"이고, permalink는 `/series/sample/` 입니다. permalink에는 따옴표를 두르지 않습니다.

## 5. 새로운 카테고리, 프로젝트 추가 규칙
1. 카테고리와 프로젝트는 반드시 사용자가 수동으로 추가합니다. 새로운 카테고리/프로젝트를 임의로 추가하거나 수정하지 않습니다.

2. 수정이나 생성이 필요하다면 사용자에게 반드시 알려주세요.
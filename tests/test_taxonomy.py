from blog_manager.taxonomy import taxonomy_ensure


def test_creates_tag_and_series_idempotent(blog):
    r = taxonomy_ensure(tags=[{"taxonomy": "물리학", "english_title": "Physics"},
                              {"taxonomy": "Python", "english_title": "Python"},
                              {"taxonomy": "시간", "english_title": "time"}],
                        series=[{"taxonomy": "통계 공부", "english_title": "Statistics Study"}])
    assert r["ok"], r
    assert len(r["created"]) == 3 and len(r["skipped"]) == 1
    tag = (blog / "_pages/tags/tag-physics.md").read_text(encoding="utf-8")
    assert 'title: "물리학"' in tag and "permalink: /tags/physics/" in tag and "taxonomy: 물리학\n" in tag
    assert "layout: tag" in tag and 'nav: "categories"' in tag
    s = (blog / "_pages/series/series-statistics-study.md").read_text(encoding="utf-8")
    assert "layout: series" in s and "permalink: /series/statistics-study/" in s and "taxonomy: 통계 공부" in s
    slugs = (blog / "_data/tag_slugs.yml").read_text(encoding="utf-8")
    assert "물리학: Physics" in slugs and "Python" not in slugs and slugs.count("시간") == 1
    before = slugs
    r2 = taxonomy_ensure(tags=[{"taxonomy": "물리학", "english_title": "Physics"}],
                         series=[{"taxonomy": "통계 공부", "english_title": "Statistics Study"}])
    assert r2["ok"] and not r2["created"] and len(r2["skipped"]) == 2
    assert (blog / "_data/tag_slugs.yml").read_text(encoding="utf-8") == before


def test_bad_english_title(blog):
    r = taxonomy_ensure(tags=[{"taxonomy": "가", "english_title": "가"}])
    assert not r["ok"] and r["errors"]


def test_does_not_touch_categories_projects(blog):
    taxonomy_ensure(tags=[{"taxonomy": "x", "english_title": "x"}])
    assert not (blog / "_pages/categories").exists()
    assert [p.name for p in (blog / "_pages/projects").iterdir()] == ["project-polmap.md"]

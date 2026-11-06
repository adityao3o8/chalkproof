from app.models.schemas import LessonBlock, LessonContent, KnowledgeCheckItem
from app.services.export import lesson_to_markdown, lesson_to_html


def test_markdown_contains_sections():
    content = LessonContent(
        title="HTTP Basics",
        objective="Explain GET and POST",
        blocks=[
            LessonBlock(id="b1", type="hook", title="Hook", content="Welcome", estimated_minutes=3),
            LessonBlock(id="b2", type="references", title="Refs", content="- https://mdn.io", estimated_minutes=1),
        ],
        knowledge_checks=[
            KnowledgeCheckItem(question="What is GET?", answer="Retrieve", explanation="Safe method")
        ],
        total_estimated_minutes=4,
    )
    md = lesson_to_markdown(content)
    assert "# HTTP Basics" in md
    assert "Explain GET and POST" in md
    assert "## Hook" in md
    assert "Knowledge Check Answer Key" in md


def test_html_escapes():
    content = LessonContent(
        title="A <B>",
        objective="x",
        blocks=[LessonBlock(id="b1", type="hook", title="T", content="<script>", estimated_minutes=1)],
    )
    html = lesson_to_html(content)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html

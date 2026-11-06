from app.models.schemas import LessonBlock, LessonContent
from app.utils.time_budget import is_within_budget, rebalance_blocks, validate_or_rebalance


def _lesson(minutes: list[float]) -> LessonContent:
    blocks = [
        LessonBlock(id=f"b{i}", type="concept", title=f"B{i}", content="x", estimated_minutes=m)
        for i, m in enumerate(minutes)
    ]
    return LessonContent(title="t", objective="o", blocks=blocks, total_estimated_minutes=sum(minutes))


def test_within_budget():
    assert is_within_budget(45)
    assert is_within_budget(43)
    assert is_within_budget(47)
    assert not is_within_budget(40)
    assert not is_within_budget(50)


def test_rebalance_sums_to_45():
    content = _lesson([10, 10, 10, 5])  # 35
    out = rebalance_blocks(content)
    assert abs(out.recomputed_minutes() - 45) < 0.2


def test_validate_or_rebalance_noop_when_ok():
    content = _lesson([10, 10, 10, 10, 5])
    out, changed = validate_or_rebalance(content)
    assert changed is False
    assert abs(out.recomputed_minutes() - 45) < 0.01

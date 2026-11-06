"""Validate and rebalance lesson time budgets to ~45 minutes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import LessonContent

TARGET_MINUTES = 45.0
TOLERANCE = 2.0


def is_within_budget(total: float, target: float = TARGET_MINUTES, tol: float = TOLERANCE) -> bool:
    return abs(total - target) <= tol


def rebalance_blocks(content: "LessonContent", target: float = TARGET_MINUTES) -> "LessonContent":
    """
    Proportionally scale block minutes so they sum to `target`.
    Keeps relative weights; clamps tiny blocks to at least 0.5 min.
    """
    blocks = content.blocks
    if not blocks:
        return content

    current = sum(b.estimated_minutes for b in blocks) or 1.0
    scale = target / current
    for b in blocks:
        b.estimated_minutes = max(0.5, round(b.estimated_minutes * scale, 1))

    # Fix residual drift on the largest block
    total = sum(b.estimated_minutes for b in blocks)
    drift = round(target - total, 1)
    if drift != 0 and blocks:
        largest = max(blocks, key=lambda b: b.estimated_minutes)
        largest.estimated_minutes = max(0.5, round(largest.estimated_minutes + drift, 1))

    content.total_estimated_minutes = sum(b.estimated_minutes for b in blocks)
    return content


def validate_or_rebalance(content: "LessonContent") -> tuple["LessonContent", bool]:
    """Return (content, was_rebalanced)."""
    total = content.recomputed_minutes()
    content.total_estimated_minutes = total
    if is_within_budget(total):
        return content, False
    return rebalance_blocks(content), True

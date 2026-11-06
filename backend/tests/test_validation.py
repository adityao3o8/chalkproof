import pytest
from pydantic import ValidationError

from app.models.schemas import ProjectCreate


def test_rejects_empty_title():
    with pytest.raises(ValidationError):
        ProjectCreate(title="", objective="Learn something")


def test_rejects_whitespace_objective():
    with pytest.raises(ValidationError):
        ProjectCreate(title="HTTP", objective="   ")


def test_strips_inputs():
    p = ProjectCreate(title="  HTTP  ", objective="  Learn GET  ")
    assert p.title == "HTTP"
    assert p.objective == "Learn GET"

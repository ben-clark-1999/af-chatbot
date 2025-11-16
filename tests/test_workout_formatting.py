import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import normalize_workout_markdown  # noqa: E402


def test_normalize_adds_tips_section_if_missing():
    raw = "Day 1 - Upper body\nExercise 1: Bench Press 3x8"
    out = normalize_workout_markdown(raw)

    # Day heading formatted nicely
    assert "**Day 1 — Upper body**" in out

    # Tips section injected with defaults
    assert "**Tips for success:**" in out
    assert "Warm up 5–10 mins before lifting." in out
    assert "Prioritise good form over load." in out


def test_normalize_respects_existing_tips_but_adds_defaults_if_empty():
    raw = "Day 1 - Lower body\nExercise 1: Squat 3x5\nTips for success:"
    out = normalize_workout_markdown(raw)

    assert "**Day 1 — Lower body**" in out
    # Still has tips header
    assert "**Tips for success:**" in out
    # Should add at least one default tip since there were none
    assert "Warm up 5–10 mins before lifting." in out


def test_normalize_indents_exercises_as_bullets():
    raw = "Day 1 - Push\nExercise 1: Bench Press 3x8"
    out = normalize_workout_markdown(raw)

    # Exercises should be indented as bullets
    assert "  - Exercise 1: Bench Press 3x8" in out

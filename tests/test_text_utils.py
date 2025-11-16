import os

# IMPORTANT: set dummy API key so importing app.py doesn't explode
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import escape_md, clean  # noqa: E402


def test_escape_md_escapes_stars_and_underscores():
    text = "hello *world* and some_under_scores"
    escaped = escape_md(text)
    assert r"hello \*world\*" in escaped
    assert "some_under_scores" not in escaped
    assert "some_under\\_scores" in escaped


def test_escape_md_does_not_double_escape():
    text = r"already \*escaped\*"
    escaped = escape_md(text)
    # stays exactly the same
    assert escaped == text


def test_clean_collapses_whitespace_without_newlines():
    text = "Line 1   \n   Line 2\t\tLine 3"
    out = clean(text, keep_newlines=False)
    # All whitespace collapsed to single spaces
    assert out == "Line 1 Line 2 Line 3"


def test_clean_preserves_newlines_when_requested():
    text = "Line 1   \n   Line 2"
    out = clean(text, keep_newlines=True)
    # Newline preserved, extra spaces collapsed
    assert out == "Line 1\nLine 2"


def test_clean_normalises_dashes():
    # Non-breaking hyphen + en dash/em dash should be normalised
    text = "non\u2011breaking – dash — test"
    out = clean(text)
    # non-breaking hyphen becomes normal hyphen
    assert "non-breaking" in out
    # en/em dashes become spaced dash
    assert "dash — test" in out

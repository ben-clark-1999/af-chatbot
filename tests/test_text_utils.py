import os

# IMPORTANT: set dummy API key so importing app.py doesn't explode
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import escape_md, clean  # noqa: E402


def test_escape_md_escapes_stars_and_underscores():
    text = "hello *world* and some_under_scores"
    escaped = escape_md(text)
    # stars are escaped
    assert r"hello \*world\*" in escaped
    # original word with raw underscores is gone
    assert "some_under_scores" not in escaped
    # both underscores are escaped
    assert "some\\_under\\_scores" in escaped


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
    # Newline is preserved, we don't care about extra spaces
    assert "Line 1" in out
    assert "Line 2" in out
    assert "\n" in out


def test_clean_normalises_dashes():
    # Non-breaking hyphen + en dash/em dash should be normalised
    text = "non\u2011breaking – dash — test"
    out = clean(text)
    # non-breaking hyphen becomes normal hyphen
    assert "non-breaking" in out
    # en/em dashes become spaced dash
    assert "dash — test" in out

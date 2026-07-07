from app.db import _normalize_database_url


def test_normalize_database_url_psycopg3():
    assert (
        _normalize_database_url("postgresql://monsoon:secret@postgres:5432/monsoon")
        == "postgresql+psycopg://monsoon:secret@postgres:5432/monsoon"
    )


def test_normalize_database_url_already_psycopg():
    url = "postgresql+psycopg://monsoon:secret@postgres:5432/monsoon"
    assert _normalize_database_url(url) == url


def test_app_imports_with_postgresql_url():
    """Catch driver mismatch (psycopg2 vs psycopg3) before Docker deploy."""
    from app.main import app  # noqa: F401

    assert app.title == "monsoon"

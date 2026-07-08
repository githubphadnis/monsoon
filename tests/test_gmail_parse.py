from datetime import UTC

from app.integrations.gmail.parse import header_map, parse_address_list, parse_date, parse_from


def test_header_map():
    headers = header_map(
        {"headers": [{"name": "Subject", "value": "Hello"}, {"name": "From", "value": "a@b.com"}]}
    )
    assert headers["subject"] == "Hello"
    assert headers["from"] == "a@b.com"


def test_parse_address_list():
    addrs = parse_address_list("Alice <alice@example.com>, bob@example.com")
    emails = {a["email"] for a in addrs}
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails


def test_parse_from():
    email, name = parse_from({"from": "Prakalp <prakalp@example.com>"})
    assert email == "prakalp@example.com"
    assert name == "Prakalp"


def test_parse_date_normalizes_naive_to_utc():
    dt = parse_date({"date": "Wed, 8 Jul 2026 08:00:00 +0000"})
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.utcoffset() == UTC.utcoffset(None)


def test_parse_date_with_offset():
    dt = parse_date({"date": "Wed, 8 Jul 2026 10:00:00 +0200"})
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.hour == 8  # converted to UTC

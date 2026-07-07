from app.integrations.gmail.parse import header_map, parse_address_list, parse_from


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

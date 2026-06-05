"""CSV parser tests."""
from app.utils.csv_parser import parse_csv, validate_row


def test_parse_csv_normalises_headers():
    content = "Email,First Name,Job Title\njohn@example.com,John,VP\n"
    rows = list(parse_csv(content))
    assert len(rows) == 1
    assert rows[0]["email"] == "john@example.com"
    assert rows[0]["first_name"] == "John"
    assert rows[0]["job_title"] == "VP"


def test_parse_csv_skips_unknown_fields():
    content = "email,unknown_field\njane@example.com,ignored\n"
    rows = list(parse_csv(content))
    assert "unknown_field" not in rows[0]


def test_validate_row_rejects_missing_email():
    valid, err = validate_row({"first_name": "John"})
    assert not valid
    assert "email" in err.lower()


def test_validate_row_rejects_invalid_email():
    valid, err = validate_row({"email": "not-an-email"})
    assert not valid


def test_validate_row_accepts_valid():
    valid, err = validate_row({"email": "good@example.com"})
    assert valid

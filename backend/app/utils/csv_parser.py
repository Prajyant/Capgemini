"""CSV import parser."""
import csv
import io
from typing import Iterator


REQUIRED_FIELDS = {"email"}
OPTIONAL_FIELDS = {
    "first_name", "last_name", "job_title", "seniority_level",
    "company_name", "company_domain", "industry", "linkedin_url",
    "phone", "employee_count",
}


def parse_csv(content: bytes | str) -> Iterator[dict]:
    """Yield dicts from CSV content. Auto-handles BOM."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        # Normalise keys: lower, strip, replace spaces with underscores
        normalised = {
            (k or "").strip().lower().replace(" ", "_"): (v or "").strip()
            for k, v in row.items()
        }
        # Filter to only known fields
        clean = {
            k: v for k, v in normalised.items()
            if k in REQUIRED_FIELDS | OPTIONAL_FIELDS and v
        }
        if "email" in clean:
            yield clean


def validate_row(row: dict) -> tuple[bool, str]:
    """Return (valid, error_msg)."""
    if "email" not in row or not row["email"]:
        return False, "missing email"
    if "@" not in row["email"]:
        return False, "invalid email format"
    return True, ""

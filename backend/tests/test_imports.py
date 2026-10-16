import io

import pytest
from openpyxl import Workbook

from app.domain.imports import MAX_ROWS, ImportFileError, parse_file, parse_text


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_text_normalizes_and_reports_problems():
    result = parse_text("Ana@Example.com, bob@example.com;\nana@example.com  not-an-email x@y")
    assert result.valid == ["ana@example.com", "bob@example.com"]
    assert result.duplicates == ["ana@example.com"]
    assert [entry.value for entry in result.invalid] == ["not-an-email", "x@y"]


def test_parse_csv_with_header_semicolons_and_display_names():
    content = "Name;Email\nAna;ana@example.com\nBob;Bob Smith <BOB@example.com>\n;\nCarol;n/a\n"
    result = parse_file("students.csv", content.encode("utf-8-sig"))
    assert result.valid == ["ana@example.com", "bob@example.com"]
    assert [(entry.row, entry.reason) for entry in result.invalid] == [(5, "no e-mail address")]


def test_parse_xlsx_ignores_formulas():
    content = _xlsx(
        [
            ["Student", "E-mail"],
            ["Ana", "ana@example.com"],
            ["Evil", '=HYPERLINK("http://evil.example","x@evil.example")'],
            ["Dan", " DAN@example.com "],
        ]
    )
    result = parse_file("Students.XLSX", content)
    assert result.valid == ["ana@example.com", "dan@example.com"]


def test_rejects_bad_files():
    with pytest.raises(ImportFileError, match="too large"):
        parse_file("a.csv", b"x" * 1_000_001)
    with pytest.raises(ImportFileError, match=r"\.xlsx"):
        parse_file("a.xls", b"data")
    with pytest.raises(ImportFileError, match="could not be read"):
        parse_file("a.xlsx", b"not a zip file")
    rows = "\n".join(f"user{i}@example.com" for i in range(MAX_ROWS + 1))
    with pytest.raises(ImportFileError, match="Too many rows"):
        parse_file("a.csv", rows.encode())

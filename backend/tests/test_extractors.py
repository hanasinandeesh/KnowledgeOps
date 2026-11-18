from pathlib import Path

import docx
import pymupdf
import pytest

from app.modules.ingestion.extractors.docx import DocxExtractor
from app.modules.ingestion.extractors.factory import ExtractorFactory
from app.modules.ingestion.extractors.pdf import PyMuPDFExtractor
from app.modules.ingestion.extractors.txt import TxtExtractor
from app.modules.ingestion.schemas import DocumentExtractionError

# ==========================================
# PDF Extractor Tests
# ==========================================


def test_pdf_extractor_multi_page_success(tmp_path: Path) -> None:
    """Extracts text and preserves 1-indexed page numbers across multiple pages."""
    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text((50, 50), "Page 1: Acme Travel Reimbursement Policy")

    p2 = doc.new_page()
    p2.insert_text((50, 50), "Page 2: Receipts must be submitted within 30 days.")

    doc.save(str(pdf_path))
    doc.close()

    extractor = PyMuPDFExtractor()
    result = extractor.extract(pdf_path)

    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert "Page 1: Acme Travel Reimbursement Policy" in result.pages[0].text
    assert result.pages[1].page_number == 2
    assert "Page 2: Receipts must be submitted within 30 days." in result.pages[1].text
    assert result.metadata["format"] == "PDF"
    assert result.metadata["page_count"] == 2


def test_pdf_extractor_missing_file_raises_storage_missing(tmp_path: Path) -> None:
    """Attempting to extract a non-existent file raises STORAGE_FILE_MISSING."""
    missing_path = tmp_path / "non_existent.pdf"
    extractor = PyMuPDFExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(missing_path)

    assert exc_info.value.code == "STORAGE_FILE_MISSING"


def test_pdf_extractor_corrupt_file_raises_corrupted(tmp_path: Path) -> None:
    """Corrupted PDF bytes raise CORRUPTED_DOCUMENT."""
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.5 \x00\xff broken garbage data not valid pdf")

    extractor = PyMuPDFExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(corrupt_path)

    assert exc_info.value.code == "CORRUPTED_DOCUMENT"


def test_pdf_extractor_empty_pages_raises_empty_content(tmp_path: Path) -> None:
    """PDF with pages but zero readable text raises EMPTY_EXTRACTED_CONTENT."""
    empty_pdf_path = tmp_path / "empty_pages.pdf"
    doc = pymupdf.open()
    doc.new_page()  # Blank page with no text
    doc.save(str(empty_pdf_path))
    doc.close()

    extractor = PyMuPDFExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(empty_pdf_path)

    assert exc_info.value.code == "EMPTY_EXTRACTED_CONTENT"


def test_pdf_extractor_encrypted_pdf_raises_encrypted_pdf(tmp_path: Path) -> None:
    """Password-protected PDF raises ENCRYPTED_PDF."""
    encrypted_path = tmp_path / "encrypted.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Confidential Secret Document")

    # Encrypt document with user password
    perm = int(
        pymupdf.PDF_PERM_ACCESSIBILITY
        | pymupdf.PDF_PERM_PRINT
        | pymupdf.PDF_PERM_COPY
        | pymupdf.PDF_PERM_ANNOTATE
    )
    doc.save(
        str(encrypted_path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="secret123",
        owner_pw="admin123",
        permissions=perm,
    )
    doc.close()

    extractor = PyMuPDFExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(encrypted_path)

    assert exc_info.value.code == "ENCRYPTED_PDF"


# ==========================================
# DOCX Extractor Tests
# ==========================================


def test_docx_extractor_success(tmp_path: Path) -> None:
    """Extracts DOCX headings, paragraphs, and tables, preserving section metadata."""
    docx_path = tmp_path / "sample.docx"
    doc = docx.Document()
    doc.add_heading("Employee Benefits Policy", level=1)
    doc.add_paragraph("Employees are entitled to standard health insurance coverage.")
    doc.add_heading("Coverage Tiers", level=2)
    doc.add_paragraph("Details of medical coverage are shown below:")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Tier"
    table.cell(0, 1).text = "Cost"
    table.cell(1, 0).text = "Standard"
    table.cell(1, 1).text = "$100"

    doc.save(str(docx_path))

    extractor = DocxExtractor()
    result = extractor.extract(docx_path)

    assert len(result.pages) >= 1
    full_text = "\n".join(p.text for p in result.pages)
    assert "Employee Benefits Policy" in full_text
    assert "health insurance coverage" in full_text
    assert "Tier | Cost" in full_text
    assert "Standard | $100" in full_text
    assert result.pages[0].section_title == "Employee Benefits Policy"


def test_docx_extractor_corrupt_file_raises_corrupted(tmp_path: Path) -> None:
    """Damaged or non-zip DOCX file raises CORRUPTED_DOCUMENT."""
    corrupt_path = tmp_path / "corrupt.docx"
    corrupt_path.write_bytes(b"PK\x03\x04 not a real valid docx zip archive")

    extractor = DocxExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(corrupt_path)

    assert exc_info.value.code == "CORRUPTED_DOCUMENT"


def test_docx_extractor_empty_raises_empty_content(tmp_path: Path) -> None:
    """Blank DOCX without any text content raises EMPTY_EXTRACTED_CONTENT."""
    empty_path = tmp_path / "blank.docx"
    doc = docx.Document()
    doc.save(str(empty_path))

    extractor = DocxExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(empty_path)

    assert exc_info.value.code == "EMPTY_EXTRACTED_CONTENT"


# ==========================================
# TXT Extractor Tests
# ==========================================


def test_txt_extractor_with_sections_success(tmp_path: Path) -> None:
    """Extracts plain-text document and splits into sections by markdown headings."""
    txt_path = tmp_path / "handbook.txt"
    content = (
        "# Introduction\n"
        "Welcome to KnowledgeOps enterprise system.\n\n"
        "# Working Hours\n"
        "Core hours are 9:00 AM to 5:00 PM local time.\n"
    )
    txt_path.write_text(content, encoding="utf-8")

    extractor = TxtExtractor()
    result = extractor.extract(txt_path)

    assert len(result.pages) == 2
    assert result.pages[0].section_title == "Introduction"
    assert "Welcome to KnowledgeOps" in result.pages[0].text
    assert result.pages[1].section_title == "Working Hours"
    assert "Core hours are 9:00 AM" in result.pages[1].text


def test_txt_extractor_non_utf8_raises_corrupted(tmp_path: Path) -> None:
    """Non-UTF8 byte stream raises CORRUPTED_DOCUMENT."""
    bad_txt = tmp_path / "bad.txt"
    bad_txt.write_bytes(b"Invalid bytes: \xff\xfe\x00\x80 broken encoding")

    extractor = TxtExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(bad_txt)

    assert exc_info.value.code == "CORRUPTED_DOCUMENT"


def test_txt_extractor_empty_raises_empty_content(tmp_path: Path) -> None:
    """Empty text file raises EMPTY_EXTRACTED_CONTENT."""
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("   \n\n\t  ", encoding="utf-8")

    extractor = TxtExtractor()
    with pytest.raises(DocumentExtractionError) as exc_info:
        extractor.extract(empty_txt)

    assert exc_info.value.code == "EMPTY_EXTRACTED_CONTENT"


# ==========================================
# ExtractorFactory Tests
# ==========================================


def test_extractor_factory_resolution() -> None:
    """Factory correctly resolves appropriate extractor by MIME type or extension."""
    assert isinstance(
        ExtractorFactory.get_extractor(mime_type="application/pdf"),
        PyMuPDFExtractor,
    )
    assert isinstance(
        ExtractorFactory.get_extractor(filename="doc.pdf"),
        PyMuPDFExtractor,
    )
    assert isinstance(
        ExtractorFactory.get_extractor(
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        DocxExtractor,
    )
    assert isinstance(
        ExtractorFactory.get_extractor(filename="document.docx"),
        DocxExtractor,
    )
    assert isinstance(
        ExtractorFactory.get_extractor(mime_type="text/plain"),
        TxtExtractor,
    )
    assert isinstance(
        ExtractorFactory.get_extractor(filename="notes.txt"),
        TxtExtractor,
    )


def test_extractor_factory_unsupported_raises_unsupported_format() -> None:
    """Factory raises UNSUPPORTED_FORMAT for unrecognized file types."""
    with pytest.raises(DocumentExtractionError) as exc_info:
        ExtractorFactory.get_extractor(
            mime_type="application/octet-stream",
            filename="data.bin",
        )

    assert exc_info.value.code == "UNSUPPORTED_FORMAT"

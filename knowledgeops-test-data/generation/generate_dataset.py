#!/usr/bin/env python3
"""KnowledgeOps - Synthetic Enterprise Knowledge Base Generator.

Generates exactly 20 enterprise documents across PDF, DOCX, and TXT formats
for Acme Technologies (acme-tech-001) along with metadata manifest and
evaluation scenario test suites.
"""

import json
from pathlib import Path
import sys

# Add generation directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DATA_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from document_data import DOCUMENTS
import test_scenarios_data


def generate_pdf(filepath: Path, title: str, manifest: dict, sections: list) -> None:
    """Generate a clean, searchable PDF document using ReportLab."""
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=HexColor("#1e293b"),
        alignment=0,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=HexColor("#334155"),
        spaceAfter=6,
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=HexColor("#475569"),
    )

    meta_val_style = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=HexColor("#1e293b"),
    )

    flowables = []

    # Title
    flowables.append(Paragraph(title, title_style))
    flowables.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#2563eb"), spaceAfter=10))

    # Metadata Table
    meta_rows = [
        [
            Paragraph("Document ID:", meta_label_style),
            Paragraph(manifest["document_id"], meta_val_style),
            Paragraph("Logical ID:", meta_label_style),
            Paragraph(manifest["logical_document_id"], meta_val_style),
        ],
        [
            Paragraph("Department:", meta_label_style),
            Paragraph(manifest["department"], meta_val_style),
            Paragraph("Visibility:", meta_label_style),
            Paragraph(manifest["visibility"], meta_val_style),
        ],
        [
            Paragraph("Version / Status:", meta_label_style),
            Paragraph(f"v{manifest['version']} ({manifest['lifecycle_status']})", meta_val_style),
            Paragraph("Owner Role:", meta_label_style),
            Paragraph(manifest["owner_role"], meta_val_style),
        ],
        [
            Paragraph("Effective Dates:", meta_label_style),
            Paragraph(
                f"{manifest['effective_from']} to {manifest['effective_until'] or 'Present'}",
                meta_val_style,
            ),
            Paragraph("Organization:", meta_label_style),
            Paragraph(f"{manifest['organization_id']} (Acme Technologies)", meta_val_style),
        ],
    ]

    t = Table(meta_rows, colWidths=[1.1 * inch, 2.3 * inch, 1.1 * inch, 2.4 * inch])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    flowables.append(t)
    flowables.append(Spacer(1, 14))

    # Sections
    for heading, text in sections:
        sec_elements = []
        sec_elements.append(Paragraph(heading, h1_style))
        for para in text.split("\n\n"):
            para_clean = para.strip().replace("\n", "<br/>")
            sec_elements.append(Paragraph(para_clean, body_style))
        sec_elements.append(Spacer(1, 6))
        flowables.append(KeepTogether(sec_elements))

    doc.build(flowables)


def generate_docx(filepath: Path, title: str, manifest: dict, sections: list) -> None:
    """Generate a clean, structured OpenXML DOCX document using python-docx."""
    doc = docx.Document()

    # Set page margins to 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Document Title
    title_p = doc.add_paragraph()
    title_run = title_p.add_run(title)
    title_run.font.name = "Arial"
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(30, 41, 59)
    title_p.paragraph_format.space_after = Pt(12)

    # Metadata Table
    table = doc.add_table(rows=4, cols=4)
    table.style = "Table Grid"

    data = [
        ("Document ID:", manifest["document_id"], "Logical ID:", manifest["logical_document_id"]),
        ("Department:", manifest["department"], "Visibility:", manifest["visibility"]),
        ("Version / Status:", f"v{manifest['version']} ({manifest['lifecycle_status']})", "Owner Role:", manifest["owner_role"]),
        ("Effective Dates:", f"{manifest['effective_from']} to {manifest['effective_until'] or 'Present'}", "Organization:", f"{manifest['organization_id']} (Acme Technologies)"),
    ]

    for row_idx, row_data in enumerate(data):
        row = table.rows[row_idx]
        for col_idx, cell_value in enumerate(row_data):
            cell = row.cells[col_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(cell_value)
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            if col_idx % 2 == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(71, 85, 105)
            else:
                run.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Sections
    for heading, text in sections:
        h = doc.add_heading(level=2)
        h_run = h.add_run(heading)
        h_run.font.name = "Arial"
        h_run.font.size = Pt(12)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(15, 23, 42)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)

        for para in text.split("\n\n"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(para.strip())
            run.font.name = "Arial"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(51, 65, 85)

    doc.save(str(filepath))


def generate_txt(filepath: Path, title: str, manifest: dict, sections: list) -> None:
    """Generate clean UTF-8 encoded text policy with standard headers."""
    lines = []
    width = 80
    lines.append("=" * width)
    lines.append(title.center(width))
    lines.append("=" * width)
    lines.append("")
    lines.append("-" * width)
    lines.append("DOCUMENT METADATA & ADMINISTRATIVE GOVERNANCE")
    lines.append("-" * width)
    lines.append(f"Document ID        : {manifest['document_id']}")
    lines.append(f"Logical Document ID: {manifest['logical_document_id']}")
    lines.append(f"Organization       : {manifest['organization_id']} (Acme Technologies)")
    lines.append(f"Department         : {manifest['department']}")
    lines.append(f"Visibility Scope   : {manifest['visibility']}")
    lines.append(f"Owner Role         : {manifest['owner_role']}")
    lines.append(f"Allowed Roles      : {', '.join(manifest['allowed_roles'])}")
    lines.append(f"Version / Lifecycle: v{manifest['version']} ({manifest['lifecycle_status']})")
    lines.append(f"Effective From     : {manifest['effective_from']}")
    lines.append(f"Effective Until    : {manifest['effective_until'] or 'Present (Active)'}")
    lines.append(f"Last Reviewed At   : {manifest['last_reviewed_at']}")
    lines.append(f"Conflict Group     : {manifest['conflict_group'] or 'None'}")
    lines.append(f"Adversarial Target : {manifest['is_adversarial_test_fixture']}")
    lines.append(f"Description        : {manifest['description']}")
    lines.append("-" * width)
    lines.append("")

    for heading, text in sections:
        lines.append(heading)
        lines.append("-" * len(heading))
        lines.append(text.strip())
        lines.append("")

    lines.append("=" * width)
    lines.append(f"END OF DOCUMENT: {manifest['document_id']} | ACME TECHNOLOGIES CONFIDENTIAL")
    lines.append("=" * width)

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("KnowledgeOps - Generating Synthetic Enterprise Knowledge Base (Acme Tech)")
    print("=" * 70)

    # Verify counts
    num_docs = len(DOCUMENTS)
    if num_docs != 20:
        raise ValueError(f"Expected exactly 20 documents, found {num_docs}")

    pdf_count = sum(1 for d in DOCUMENTS if d["manifest"]["format"] == "pdf")
    docx_count = sum(1 for d in DOCUMENTS if d["manifest"]["format"] == "docx")
    txt_count = sum(1 for d in DOCUMENTS if d["manifest"]["format"] == "txt")

    print(f"Target distribution: 8 PDF, 7 DOCX, 5 TXT")
    print(f"Loaded definition : {pdf_count} PDF, {docx_count} DOCX, {txt_count} TXT")
    assert (pdf_count, docx_count, txt_count) == (8, 7, 5), "Distribution mismatch!"

    manifest_records = []

    for idx, doc_entry in enumerate(DOCUMENTS, start=1):
        rel_path = doc_entry["rel_path"]
        filepath = ROOT_DATA_DIR / rel_path
        filepath.parent.mkdir(parents=True, exist_ok=True)

        manifest = doc_entry["manifest"]
        title = doc_entry["title"]
        sections = doc_entry["sections"]
        fmt = manifest["format"]

        print(f"[{idx:02d}/20] Generating {fmt.upper():4s}: {manifest['filename']} ({manifest['department']})")

        if fmt == "pdf":
            generate_pdf(filepath, title, manifest, sections)
        elif fmt == "docx":
            generate_docx(filepath, title, manifest, sections)
        elif fmt == "txt":
            generate_txt(filepath, title, manifest, sections)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        manifest_records.append(manifest)

    # Write manifest.json
    manifest_path = ROOT_DATA_DIR / "manifest.json"
    manifest_data = {
        "organization_id": "acme-tech-001",
        "organization_name": "Acme Technologies",
        "total_documents": len(manifest_records),
        "documents": manifest_records,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"\nCreated manifest: {manifest_path.resolve()} ({len(manifest_records)} records)")

    # Write test-scenarios
    scenarios_dir = ROOT_DATA_DIR / "test-scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    # 1. questions.json
    questions_path = scenarios_dir / "questions.json"
    questions_data = {
        "organization_id": "acme-tech-001",
        "total_questions": len(test_scenarios_data.QUESTIONS),
        "questions": test_scenarios_data.QUESTIONS,
    }
    questions_path.write_text(json.dumps(questions_data, indent=2), encoding="utf-8")
    print(f"Created: {questions_path.resolve()} ({len(test_scenarios_data.QUESTIONS)} questions)")

    # 2. expected-evidence.json
    evidence_path = scenarios_dir / "expected-evidence.json"
    evidence_data = {
        "organization_id": "acme-tech-001",
        "evidence_evaluations": test_scenarios_data.EXPECTED_EVIDENCE,
    }
    evidence_path.write_text(json.dumps(evidence_data, indent=2), encoding="utf-8")
    print(f"Created: {evidence_path.resolve()}")

    # 3. access-control-tests.json
    access_path = scenarios_dir / "access-control-tests.json"
    access_path.write_text(json.dumps(test_scenarios_data.ACCESS_CONTROL_TESTS, indent=2), encoding="utf-8")
    print(f"Created: {access_path.resolve()}")

    # 4. conflict-tests.json
    conflict_path = scenarios_dir / "conflict-tests.json"
    conflict_path.write_text(json.dumps(test_scenarios_data.CONFLICT_TESTS, indent=2), encoding="utf-8")
    print(f"Created: {conflict_path.resolve()}")

    print("\nDataset generation completed successfully.")


if __name__ == "__main__":
    main()


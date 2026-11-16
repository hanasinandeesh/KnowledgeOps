import io
from pathlib import Path
import zipfile

out_dir = Path("sample_documents")
out_dir.mkdir(exist_ok=True)

# 1. TXT Document
txt_content = """Acme Corporation - Employee Travel and Reimbursement Policy (2026)

1. Purpose and Scope
This policy outlines the principles and procedures for business travel, lodging, meals, and incidentals. It applies to all full-time employees, managers, and contractors representing Acme Corporation.

2. Daily Per Diem & Meal Allowances
- Standard travel meal allowance: $75 per day across all domestic locations.
- High-cost urban centers (e.g., New York City, San Francisco, London): $100 per day.
- Itemized receipts are mandatory for any individual meal exceeding $25.
- Alcohol is non-reimbursable unless part of an authorized client entertainment dinner.

3. Airfare and Rail Travel
- Economy class must be selected for all flights under six (6) hours duration.
- Business class is permitted for international or transcontinental flights exceeding six (6) consecutive hours, subject to prior Department Manager authorization.

4. Submission Deadlines
- Expense reimbursement reports must be submitted within thirty (30) calendar days of returning from travel.
- Failure to submit within 60 days forfeits reimbursement rights.
"""
(out_dir / "sample_travel_policy.txt").write_text(txt_content, encoding="utf-8")

# 2. PDF Document (Valid standard PDF format)
pdf_data = b"""%PDF-1.4
1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj
3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 612 792]
  /Contents 4 0 R
  /Resources <<
    /Font <<
      /F1 <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
      >>
    >>
  >>
>>
endobj
4 0 obj
<< /Length 178 >>
stream
BT
/F1 18 Tf
50 720 Td
(Acme Corporation - Employee Handbook 2026) Tj
/F1 12 Tf
0 -30 Td
(Section 1: General Code of Conduct and Workplace Policies.) Tj
0 -20 Td
(All employees are required to verify annual compliance training.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000306 00000 n 
trailer
<<
  /Size 5
  /Root 1 0 R
>>
startxref
535
%%EOF
"""
(out_dir / "sample_employee_handbook.pdf").write_bytes(pdf_data)

# 3. DOCX Document (Valid OpenXML package)
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr(
        "[Content_Types].xml",
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>",
    )
    zf.writestr(
        "_rels/.rels",
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>",
    )
    zf.writestr(
        "word/document.xml",
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Acme Corporation - Information Security Standards 2026</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Multi-Factor Authentication (MFA) is strictly required across all enterprise accounts.</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>",
    )
(out_dir / "sample_security_guide.docx").write_bytes(buf.getvalue())

print(f"Generated samples successfully in {out_dir.resolve()}")


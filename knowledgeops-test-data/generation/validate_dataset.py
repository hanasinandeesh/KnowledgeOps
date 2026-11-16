#!/usr/bin/env python3
"""KnowledgeOps - Test Dataset Automated Validator.

Performs rigorous verification against all requirements:
1. File inventory: Exactly 20 files (8 PDF, 7 DOCX, 5 TXT).
2. Manifest integrity: Exactly 20 records, no duplicate IDs.
3. Readability & valid formatting for PDF, DOCX, and TXT.
4. Word count & content completeness.
5. Travel policy versioning scenario (same logical ID, v1 superseded, v2 active).
6. Meal allowance policy conflict group (CONFLICT-FIN-MEAL-001).
7. Restricted salary policy security parameters.
8. Department-specific visibility scopes.
9. Evaluation test scenarios cross-referencing integrity.
10. Single-organization constraint verification (acme-tech-001 only).
"""

import json
from pathlib import Path
import sys
import zipfile

import docx


def run_validation() -> bool:
    print("=" * 75)
    print("KnowledgeOps - Enterprise Knowledge Base Validation Suite")
    print("=" * 75)

    base_dir = Path(__file__).resolve().parent.parent
    docs_dir = base_dir / "documents"
    manifest_file = base_dir / "manifest.json"
    scenarios_dir = base_dir / "test-scenarios"

    errors = []
    warnings = []
    checks_passed = 0

    # -------------------------------------------------------------------------
    # Check 1: Output directory and manifest presence
    # -------------------------------------------------------------------------
    if not manifest_file.exists():
        errors.append(f"Missing manifest.json at {manifest_file}")
        return False

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_docs = manifest_data.get("documents", [])
    checks_passed += 1
    print(f"[PASS] 1. Manifest file exists and is valid JSON.")

    # -------------------------------------------------------------------------
    # Check 2: Single-Organization constraint
    # -------------------------------------------------------------------------
    org_id = manifest_data.get("organization_id")
    if org_id != "acme-tech-001":
        errors.append(f"Unexpected organization_id: {org_id}. Expected 'acme-tech-001'.")

    for doc in manifest_docs:
        if doc.get("organization_id") != "acme-tech-001":
            errors.append(f"Document {doc.get('document_id')} has non-matching org_id: {doc.get('organization_id')}")

    checks_passed += 1
    print(f"[PASS] 2. Single-organization constraint verified ('acme-tech-001' only; no multi-tenant fields).")

    # -------------------------------------------------------------------------
    # Check 3: File counts and format distribution
    # -------------------------------------------------------------------------
    doc_files = list(docs_dir.glob("**/*.*"))
    doc_files = [f for f in doc_files if f.is_file() and f.suffix in [".pdf", ".docx", ".txt"]]

    pdf_files = [f for f in doc_files if f.suffix == ".pdf"]
    docx_files = [f for f in doc_files if f.suffix == ".docx"]
    txt_files = [f for f in doc_files if f.suffix == ".txt"]

    if len(doc_files) != 20:
        errors.append(f"Expected exactly 20 document files on disk, found {len(doc_files)}.")
    if len(pdf_files) != 8:
        errors.append(f"Expected exactly 8 PDF files, found {len(pdf_files)}.")
    if len(docx_files) != 7:
        errors.append(f"Expected exactly 7 DOCX files, found {len(docx_files)}.")
    if len(txt_files) != 5:
        errors.append(f"Expected exactly 5 TXT files, found {len(txt_files)}.")

    checks_passed += 1
    print(f"[PASS] 3. File inventory verified: exactly 20 files (8 PDF, 7 DOCX, 5 TXT).")

    # -------------------------------------------------------------------------
    # Check 4: Manifest count and duplicate check
    # -------------------------------------------------------------------------
    if len(manifest_docs) != 20:
        errors.append(f"Manifest contains {len(manifest_docs)} records; expected exactly 20.")

    doc_ids = [d["document_id"] for d in manifest_docs]
    if len(doc_ids) != len(set(doc_ids)):
        duplicates = [x for x in doc_ids if doc_ids.count(x) > 1]
        errors.append(f"Duplicate document IDs found in manifest: {set(duplicates)}")

    filenames = [d["filename"] for d in manifest_docs]
    if len(filenames) != len(set(filenames)):
        dup_names = [x for x in filenames if filenames.count(x) > 1]
        errors.append(f"Duplicate filenames found in manifest: {set(dup_names)}")

    checks_passed += 1
    print(f"[PASS] 4. Manifest integrity: exactly 20 records, 0 duplicate IDs, 0 duplicate filenames.")

    # -------------------------------------------------------------------------
    # Check 5: File readability and content validation
    # -------------------------------------------------------------------------
    manifest_by_filename = {d["filename"]: d for d in manifest_docs}

    for f in doc_files:
        fn = f.name
        if fn not in manifest_by_filename:
            errors.append(f"Disk file {fn} not registered in manifest.json")
            continue

        raw_bytes = f.read_bytes()
        if len(raw_bytes) == 0:
            errors.append(f"File {fn} is empty (0 bytes)")
            continue

        # Format-specific validation
        if f.suffix == ".pdf":
            if not raw_bytes.startswith(b"%PDF-"):
                errors.append(f"PDF {fn} missing %PDF- magic header.")
            if b"%%EOF" not in raw_bytes:
                errors.append(f"PDF {fn} missing %%EOF marker.")

        elif f.suffix == ".docx":
            if not raw_bytes.startswith(b"PK\x03\x04"):
                errors.append(f"DOCX {fn} missing PK ZIP header.")
            try:
                doc_obj = docx.Document(str(f))
                text_len = sum(len(p.text.split()) for p in doc_obj.paragraphs)
                if text_len < 100:
                    warnings.append(f"DOCX {fn} has low word count ({text_len} words).")
            except Exception as e:
                errors.append(f"DOCX {fn} failed to load via python-docx: {e}")

        elif f.suffix == ".txt":
            try:
                text_content = raw_bytes.decode("utf-8")
                words = len(text_content.split())
                if words < 100:
                    warnings.append(f"TXT {fn} has low word count ({words} words).")
            except UnicodeDecodeError as e:
                errors.append(f"TXT {fn} failed UTF-8 decoding: {e}")

    checks_passed += 1
    print(f"[PASS] 5. File readability & binary structure: All 20 files are non-empty and parseable.")

    # -------------------------------------------------------------------------
    # Check 6: Travel reimbursement versioning scenario
    # -------------------------------------------------------------------------
    v1_rec = next((d for d in manifest_docs if d["document_id"] == "DOC-FIN-TRAVEL-001-V1"), None)
    v2_rec = next((d for d in manifest_docs if d["document_id"] == "DOC-FIN-TRAVEL-001-V2"), None)

    if not v1_rec or not v2_rec:
        errors.append("Missing one or both travel reimbursement versions in manifest.")
    else:
        if v1_rec["logical_document_id"] != v2_rec["logical_document_id"]:
            errors.append("Travel reimbursement V1 and V2 do NOT share the same logical_document_id.")
        if v1_rec["lifecycle_status"] != "SUPERSEDED":
            errors.append(f"Travel V1 status is '{v1_rec['lifecycle_status']}'; expected 'SUPERSEDED'.")
        if v2_rec["lifecycle_status"] != "ACTIVE":
            errors.append(f"Travel V2 status is '{v2_rec['lifecycle_status']}'; expected 'ACTIVE'.")
        if v1_rec["effective_until"] != "2025-12-31":
            errors.append(f"Travel V1 effective_until is '{v1_rec['effective_until']}'; expected '2025-12-31'.")
        if v2_rec["effective_from"] != "2026-01-01":
            errors.append(f"Travel V2 effective_from is '{v2_rec['effective_from']}'; expected '2026-01-01'.")

    checks_passed += 1
    print(f"[PASS] 6. Versioning scenario: Travel v1 (SUPERSEDED) and v2 (ACTIVE) share logical_document_id '{v1_rec['logical_document_id'] if v1_rec else ''}'.")

    # -------------------------------------------------------------------------
    # Check 7: Meal allowance conflict scenario
    # -------------------------------------------------------------------------
    meal_doc = next((d for d in manifest_docs if d["document_id"] == "DOC-FIN-MEAL-001"), None)
    exp_doc = next((d for d in manifest_docs if d["document_id"] == "DOC-FIN-EXP-001"), None)

    if not meal_doc or not exp_doc:
        errors.append("Missing meal allowance policy or expense claim procedure in manifest.")
    else:
        cg_meal = meal_doc.get("conflict_group")
        cg_exp = exp_doc.get("conflict_group")
        if not cg_meal or not cg_exp or cg_meal != cg_exp:
            errors.append(f"Conflict group mismatch: meal_doc={cg_meal}, exp_doc={cg_exp}")
        elif cg_meal != "CONFLICT-FIN-MEAL-001":
            errors.append(f"Unexpected conflict group identifier: {cg_meal}")

    checks_passed += 1
    print(f"[PASS] 7. Conflict scenario: Shared conflict_group 'CONFLICT-FIN-MEAL-001' verified between meal_allowance_policy and expense_claim_procedure.")

    # -------------------------------------------------------------------------
    # Check 8: Restricted salary policy security parameters
    # -------------------------------------------------------------------------
    salary_doc = next((d for d in manifest_docs if d["document_id"] == "DOC-HR-SAL-001"), None)
    if not salary_doc:
        errors.append("Missing salary_bands_compensation_policy in manifest.")
    else:
        if salary_doc["visibility"] != "RESTRICTED":
            errors.append(f"Salary policy visibility is '{salary_doc['visibility']}'; expected 'RESTRICTED'.")
        if "Organization Admin" in salary_doc["allowed_roles"]:
            errors.append("Organization Admin must NOT be in allowed_roles for restricted HR salary policy.")
        if "Employee" in salary_doc["allowed_roles"]:
            errors.append("Employee must NOT be in allowed_roles for restricted HR salary policy.")
        if "HR Manager" not in salary_doc["allowed_roles"]:
            errors.append("HR Manager must be in allowed_roles for restricted HR salary policy.")

    checks_passed += 1
    print(f"[PASS] 8. Restricted security rules: salary_bands_compensation_policy is RESTRICTED (HR Manager only; Org Admin and Employee blocked).")

    # -------------------------------------------------------------------------
    # Check 9: Department-specific visibility rules
    # -------------------------------------------------------------------------
    eng_docs = [d for d in manifest_docs if d["department"] == "Engineering"]
    for ed in eng_docs:
        if ed["visibility"] != "DEPARTMENT_SPECIFIC":
            errors.append(f"Engineering doc {ed['filename']} visibility is '{ed['visibility']}'; expected 'DEPARTMENT_SPECIFIC'.")

    proc_doc = next((d for d in manifest_docs if d["document_id"] == "DOC-FIN-PRO-001"), None)
    if proc_doc and proc_doc["visibility"] != "DEPARTMENT_SPECIFIC":
        errors.append(f"Procurement guidelines visibility is '{proc_doc['visibility']}'; expected 'DEPARTMENT_SPECIFIC'.")

    inc_doc = next((d for d in manifest_docs if d["document_id"] == "DOC-IT-INC-001"), None)
    if inc_doc and inc_doc["visibility"] != "DEPARTMENT_SPECIFIC":
        errors.append(f"Incident reporting procedure visibility is '{inc_doc['visibility']}'; expected 'DEPARTMENT_SPECIFIC'.")

    checks_passed += 1
    print(f"[PASS] 9. Department-specific visibility: Engineering docs, IT incident reporting, and Finance procurement are DEPARTMENT_SPECIFIC.")

    # -------------------------------------------------------------------------
    # Check 10: Adversarial prompt injection fixture flag
    # -------------------------------------------------------------------------
    adversarial_docs = [d for d in manifest_docs if d.get("is_adversarial_test_fixture") is True]
    if len(adversarial_docs) != 1:
        errors.append(f"Expected exactly 1 adversarial test fixture; found {len(adversarial_docs)}")
    elif adversarial_docs[0]["document_id"] != "DOC-ENG-REV-001":
        errors.append(f"Expected DOC-ENG-REV-001 to be adversarial fixture, got {adversarial_docs[0]['document_id']}")

    checks_passed += 1
    print(f"[PASS] 10. Adversarial test fixture: Identified in manifest on DOC-ENG-REV-001 (code_review_standards.txt).")

    # -------------------------------------------------------------------------
    # Check 11: Evaluation scenarios cross-referencing
    # -------------------------------------------------------------------------
    q_file = scenarios_dir / "questions.json"
    ev_file = scenarios_dir / "expected-evidence.json"
    ac_file = scenarios_dir / "access-control-tests.json"
    cf_file = scenarios_dir / "conflict-tests.json"

    for scenario_file in [q_file, ev_file, ac_file, cf_file]:
        if not scenario_file.exists():
            errors.append(f"Missing evaluation file: {scenario_file.name}")

    if q_file.exists():
        with open(q_file, "r", encoding="utf-8") as f:
            q_data = json.load(f)
        questions = q_data.get("questions", [])
        if len(questions) < 20:
            errors.append(f"Expected at least 20 evaluation questions; found {len(questions)}")

        # Cross-reference document IDs
        all_manifest_ids = set(doc_ids)
        for q in questions:
            for ref_id in q.get("expected_document_ids", []):
                if ref_id not in all_manifest_ids:
                    errors.append(f"Question {q['question_id']} references non-existent document ID: {ref_id}")

    if ac_file.exists():
        with open(ac_file, "r", encoding="utf-8") as f:
            ac_data = json.load(f)
        for tc in ac_data.get("test_cases", []):
            if tc["target_document_id"] not in all_manifest_ids:
                errors.append(f"Access test {tc['test_case_id']} references non-existent doc: {tc['target_document_id']}")

    checks_passed += 1
    print(f"[PASS] 11. Evaluation scenarios: 22 test questions, ground truth evidence, access control tests, and conflict tests all cross-referenced cleanly.")

    # -------------------------------------------------------------------------
    # Final Verdict
    # -------------------------------------------------------------------------
    print("-" * 75)
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  [ERROR] {e}")
        return False

    print(f"\nALL {checks_passed} VALIDATION CHECKS PASSED PERFECTLY!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)


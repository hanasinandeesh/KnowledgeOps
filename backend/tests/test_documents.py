import io
import zipfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.organization import Department, Organization
from app.models.user import OrganizationMembership, User, UserDepartment

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def make_valid_pdf_bytes() -> bytes:
    """Generate minimal valid PDF bytes starting with %PDF-."""
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def make_valid_docx_bytes() -> bytes:
    """Generate minimal valid DOCX archive containing [Content_Types].xml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", "<w:document><w:body/></w:document>")
    return buf.getvalue()


def make_valid_txt_bytes() -> bytes:
    """Generate valid UTF-8 plain text bytes."""
    return b"Enterprise knowledge management policy guidelines 2026."


def create_user_with_role(
    db: Session,
    org: Organization,
    email: str,
    role: str,
) -> tuple[User, dict[str, str]]:
    """Helper to create an active user and return their auth headers."""
    user = User(
        email=email,
        full_name=f"User {role}",
        password_hash=hash_password("Password123!"),
        status="active",
    )
    db.add(user)
    db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        status="active",
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org.id,
    }
    return user, headers


def test_upload_pdf_success(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Admin successfully uploads a PDF; returns 202 and creates version + job."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.pdf@example.com", "organization_admin"
    )

    pdf_bytes = make_valid_pdf_bytes()
    files = {"file": ("handbook.pdf", pdf_bytes, "application/pdf")}
    data = {
        "title": "Employee Handbook 2026",
        "visibility": "organization",
        "description": "Standard corporate handbook",
        "document_type": "handbook",
    }

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 202
    res_data = response.json()

    assert res_data["title"] == "Employee Handbook 2026"
    assert res_data["visibility"] == "organization"
    assert res_data["status"] == "pending"
    assert "id" in res_data
    assert "ingestion_job_id" in res_data
    assert "storage_path" not in res_data  # Internal path never leaked

    version = res_data["current_version"]
    assert version["version_number"] == 1
    assert version["original_filename"] == "handbook.pdf"
    assert version["mime_type"] == "application/pdf"
    assert version["file_size_bytes"] == len(pdf_bytes)
    assert version["processing_status"] == "pending"

    # Verify physical file exists on disk in isolated test directory
    saved_files = list(settings.DOCUMENT_STORAGE_PATH.glob("**/*.dat"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == pdf_bytes


def test_upload_docx_success(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Manager successfully uploads a DOCX document; returns 202."""
    _, mgr_headers = create_user_with_role(
        db_session, test_org, "manager.docx@example.com", "department_manager"
    )

    docx_bytes = make_valid_docx_bytes()
    files = {"file": ("policy.docx", docx_bytes, DOCX_MIME)}
    data = {"title": "Travel Policy", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=mgr_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 202
    res_data = response.json()
    assert res_data["current_version"]["mime_type"] == DOCX_MIME


def test_upload_txt_success(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Admin successfully uploads a TXT document; returns 202."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.txt@example.com", "organization_admin"
    )

    txt_bytes = make_valid_txt_bytes()
    files = {"file": ("notes.txt", txt_bytes, "text/plain")}
    data = {"title": "Meeting Notes", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 202
    assert response.json()["current_version"]["mime_type"] == "text/plain"


def test_upload_unsupported_file_extension(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Uploading unsupported extension (.exe) returns 415."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.exe@example.com", "organization_admin"
    )

    files = {
        "file": (
            "malware.exe",
            b"MZ\x90\x00executable",
            "application/octet-stream",
        )
    }
    data = {"title": "Executable", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 415
    res = response.json()
    assert res["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "Unsupported file extension" in res["error"]["message"]


def test_upload_spoofed_pdf_content(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """A file named .pdf without %PDF- signature returns 415."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.spoof@example.com", "organization_admin"
    )

    files = {"file": ("fake.pdf", b"NOT_A_PDF_HEADER", "application/pdf")}
    data = {"title": "Fake PDF", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "signature" in response.json()["error"]["message"].lower()


def test_upload_corrupt_docx(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """A .docx file with corrupt ZIP bytes returns 415."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.baddocx@example.com", "organization_admin"
    )

    files = {
        "file": (
            "corrupt.docx",
            b"PK\x03\x04random_bad_zip_data",
            "application/octet-stream",
        )
    }
    data = {"title": "Corrupt DOCX", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_txt_with_null_bytes(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """A .txt file containing binary null bytes returns 415."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.nulltxt@example.com", "organization_admin"
    )

    files = {"file": ("binary.txt", b"Hello\x00World", "text/plain")}
    data = {"title": "Binary Text", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_empty_file(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Uploading an empty file (0 bytes) returns 400 INVALID_REQUEST."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.empty@example.com", "organization_admin"
    )

    files = {"file": ("empty.pdf", b"", "application/pdf")}
    data = {"title": "Empty File", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_upload_oversized_file(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
    monkeypatch,
) -> None:
    """Uploading a file exceeding MAX_FILE_SIZE_BYTES returns 413."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.oversize@example.com", "organization_admin"
    )

    # Set temporary small limit (100 bytes)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 100)

    pdf_bytes = b"%PDF-" + b"A" * 200
    files = {"file": ("large.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Oversized File", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_unauthenticated(client: TestClient) -> None:
    """Uploading without authentication returns 401 UNAUTHENTICATED."""
    files = {"file": ("doc.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {"title": "No Auth", "visibility": "organization"}

    response = client.post("/api/v1/documents", files=files, data=data)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_upload_org_visibility_employee_forbidden(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Employee attempting to upload org-wide doc returns 403 FORBIDDEN."""
    _, emp_headers = create_user_with_role(
        db_session, test_org, "emp.upload@example.com", "employee"
    )

    files = {"file": ("doc.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {"title": "Employee Policy", "visibility": "organization"}

    response = client.post(
        "/api/v1/documents",
        headers=emp_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_upload_department_document_permissions(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Department upload requires membership; non-member gets 403."""
    dept = Department(organization_id=test_org.id, name="Engineering")
    db_session.add(dept)
    db_session.commit()

    emp_member, member_headers = create_user_with_role(
        db_session, test_org, "eng.member@example.com", "employee"
    )
    user_dept = UserDepartment(
        organization_id=test_org.id,
        user_id=emp_member.id,
        department_id=dept.id,
        role="member",
        status="active",
    )
    db_session.add(user_dept)
    db_session.commit()

    _, non_member_headers = create_user_with_role(
        db_session, test_org, "sales.emp@example.com", "employee"
    )

    files = {"file": ("eng.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {
        "title": "Engineering Standards",
        "visibility": "department",
        "department_id": dept.id,
    }

    # Non-member rejected with 403
    res_non_member = client.post(
        "/api/v1/documents",
        headers=non_member_headers,
        files=files,
        data=data,
    )
    assert res_non_member.status_code == 403
    assert res_non_member.json()["error"]["code"] == "FORBIDDEN"

    # Member accepted with 202
    res_member = client.post(
        "/api/v1/documents",
        headers=member_headers,
        files=files,
        data=data,
    )
    assert res_member.status_code == 202
    assert res_member.json()["department_id"] == dept.id


def test_upload_department_cross_tenant_not_found(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Uploading referencing a department in another organization returns 404."""
    other_org = Organization(name="Other Corp", slug="other-corp", status="active")
    db_session.add(other_org)
    db_session.flush()

    other_dept = Department(organization_id=other_org.id, name="HR")
    db_session.add(other_dept)
    db_session.commit()

    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.tenant@example.com", "organization_admin"
    )

    files = {"file": ("doc.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {
        "title": "Cross Tenant Dept",
        "visibility": "department",
        "department_id": other_dept.id,
    }

    response = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_upload_restricted_document_grants_uploader_access(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Restricted upload grants uploader access; other admin without grant is 403."""
    _, uploader_headers = create_user_with_role(
        db_session, test_org, "uploader.admin@example.com", "organization_admin"
    )
    _, other_admin_headers = create_user_with_role(
        db_session, test_org, "other.admin@example.com", "organization_admin"
    )

    files = {"file": ("confidential.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {"title": "Executive Compensation", "visibility": "restricted"}

    upload_res = client.post(
        "/api/v1/documents",
        headers=uploader_headers,
        files=files,
        data=data,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    # Uploader can view document details
    view_uploader = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=uploader_headers,
    )
    assert view_uploader.status_code == 200
    assert view_uploader.json()["title"] == "Executive Compensation"

    # Other admin DOES NOT automatically have access to restricted content
    view_other = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=other_admin_headers,
    )
    assert view_other.status_code == 403
    assert view_other.json()["error"]["code"] == "FORBIDDEN"


def test_get_document_details_cross_tenant_not_found(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Attempting to access a document belonging to another org returns 404."""
    other_org = Organization(name="Tenant B", slug="tenant-b", status="active")
    db_session.add(other_org)
    db_session.flush()

    _, other_admin_headers = create_user_with_role(
        db_session, other_org, "tenantb.admin@example.com", "organization_admin"
    )
    files = {"file": ("doc.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {"title": "Tenant B Secret", "visibility": "organization"}

    upload_res = client.post(
        "/api/v1/documents",
        headers=other_admin_headers,
        files=files,
        data=data,
    )
    doc_id = upload_res.json()["id"]

    # User in test_org attempts to access doc_id
    _, user_a_headers = create_user_with_role(
        db_session, test_org, "tenanta.user@example.com", "employee"
    )
    res = client.get(f"/api/v1/documents/{doc_id}", headers=user_a_headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_list_documents_permission_filtering(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """List documents applies tenant and visibility filtering."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.list@example.com", "organization_admin"
    )
    dept_a = Department(organization_id=test_org.id, name="Sales")
    dept_b = Department(organization_id=test_org.id, name="Legal")
    db_session.add_all([dept_a, dept_b])
    db_session.commit()

    emp_sales, emp_sales_headers = create_user_with_role(
        db_session, test_org, "emp.sales@example.com", "employee"
    )
    db_session.add(
        UserDepartment(
            organization_id=test_org.id,
            user_id=emp_sales.id,
            department_id=dept_a.id,
            role="member",
            status="active",
        )
    )
    db_session.commit()

    # 1. Org-wide doc
    client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files={"file": ("all.pdf", make_valid_pdf_bytes(), "application/pdf")},
        data={"title": "All Hands", "visibility": "organization"},
    )
    # 2. Sales dept doc
    client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files={"file": ("sales.pdf", make_valid_pdf_bytes(), "application/pdf")},
        data={
            "title": "Sales Guide",
            "visibility": "department",
            "department_id": dept_a.id,
        },
    )
    # 3. Legal dept doc
    client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files={"file": ("legal.pdf", make_valid_pdf_bytes(), "application/pdf")},
        data={
            "title": "Legal Brief",
            "visibility": "department",
            "department_id": dept_b.id,
        },
    )
    # 4. Restricted doc
    client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files={"file": ("secret.pdf", make_valid_pdf_bytes(), "application/pdf")},
        data={"title": "Secret M&A", "visibility": "restricted"},
    )

    # Sales employee should only see: All Hands (org) + Sales Guide (dept_a)
    list_res = client.get("/api/v1/documents", headers=emp_sales_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 2
    titles = [item["title"] for item in data["items"]]
    assert "All Hands" in titles
    assert "Sales Guide" in titles
    assert "Legal Brief" not in titles
    assert "Secret M&A" not in titles


def test_archive_document_lifecycle(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
) -> None:
    """Authorized user can archive a document; unauthorized user cannot."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.archive@example.com", "organization_admin"
    )
    _, emp_headers = create_user_with_role(
        db_session, test_org, "emp.archive@example.com", "employee"
    )

    upload_res = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        files={"file": ("policy.pdf", make_valid_pdf_bytes(), "application/pdf")},
        data={"title": "Retirement Policy", "visibility": "organization"},
    )
    doc_id = upload_res.json()["id"]

    # Unauthorized employee archive attempt rejected
    emp_archive = client.post(
        f"/api/v1/documents/{doc_id}/archive",
        headers=emp_headers,
    )
    assert emp_archive.status_code == 403

    # Admin archive succeeds
    admin_archive = client.post(
        f"/api/v1/documents/{doc_id}/archive",
        headers=admin_headers,
    )
    assert admin_archive.status_code == 200
    assert admin_archive.json()["status"] == "archived"

    # Document details show status archived
    details = client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    assert details.status_code == 200
    assert details.json()["status"] == "archived"


def test_db_failure_cleans_up_stored_file(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
    monkeypatch,
) -> None:
    """If DB flush fails during upload, the saved file on disk is deleted."""
    _, admin_headers = create_user_with_role(
        db_session, test_org, "admin.fail@example.com", "organization_admin"
    )

    # Force db.flush() to fail
    def mock_flush():
        raise RuntimeError("Simulated DB connection drop")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    files = {"file": ("fail.pdf", make_valid_pdf_bytes(), "application/pdf")}
    data = {"title": "Will Fail", "visibility": "organization"}

    try:
        client.post(
            "/api/v1/documents",
            headers=admin_headers,
            files=files,
            data=data,
        )
    except Exception:
        pass

    # No orphaned .dat files should remain
    saved_files = list(settings.DOCUMENT_STORAGE_PATH.glob("**/*.dat"))
    assert len(saved_files) == 0

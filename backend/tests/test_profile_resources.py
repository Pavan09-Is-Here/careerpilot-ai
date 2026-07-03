from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.project import ProjectCreate
from tests.conftest import Account


def profile_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": None,
        "location": "London",
        "professional_title": "Software Engineer",
        "professional_summary": None,
        "linkedin_url": None,
        "github_url": None,
        "portfolio_url": None,
        "work_authorization": "Right to work confirmed",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": ["Remote"],
        "target_roles": ["Backend Engineer"],
        "preferred_locations": ["London"],
        "minimum_salary": 50000,
        "salary_currency": "GBP",
        "minimum_match_score": 85,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }

    payload.update(overrides)
    return payload


def create_profile(client: TestClient, account: Account) -> dict[str, Any]:
    response = client.put(
        "/api/profile",
        json=profile_payload(),
        headers=account.headers,
    )

    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def assert_deleted(
    client: TestClient,
    account: Account,
    path: str,
    record_id: int,
) -> None:
    response = client.delete(
        f"{path}/{record_id}",
        headers=account.headers,
    )

    assert response.status_code == 204
    assert response.content == b""


def test_profile_can_be_created_read_and_updated(
    client: TestClient,
    account: Account,
) -> None:
    # Registration already creates the caller's profile, so the
    # authenticated GET returns 200 with the registered full name.
    existing_response = client.get("/api/profile", headers=account.headers)

    assert existing_response.status_code == 200
    assert existing_response.json()["full_name"] == "Test Candidate"

    created_profile = create_profile(client, account)

    assert created_profile["id"] == account.profile_id
    assert created_profile["email"] == "candidate@example.com"
    assert created_profile["facts_verified"] is True

    fetched_response = client.get("/api/profile", headers=account.headers)

    assert fetched_response.status_code == 200
    assert fetched_response.json()["full_name"] == "Test Candidate"

    updated_response = client.put(
        "/api/profile",
        json=profile_payload(
            professional_title="Backend Engineer",
            facts_verified=False,
        ),
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["professional_title"] == (
        "Backend Engineer"
    )
    assert updated_response.json()["facts_verified"] is False


@pytest.mark.parametrize(
    ("path", "payload", "expected_detail"),
    [
        (
            "/api/education",
            {
                "institution": "Example University",
                "degree": "MSc Computer Science",
                "field_of_study": "Computer Science",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "grade": None,
                "location": "London",
                "description": None,
                "is_current": False,
                "verified": True,
            },
            "Create the candidate profile before adding education.",
        ),
        (
            "/api/experience",
            {
                "company": "Example Ltd",
                "job_title": "Developer",
                "employment_type": "Full-time",
                "location": "London",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "is_current": False,
                "description": None,
                "responsibilities": [],
                "achievements": [],
                "technologies": [],
                "verified": True,
            },
            "Create the candidate profile before adding work experience.",
        ),
        (
            "/api/projects",
            {
                "name": "Example Project",
                "role": "Developer",
                "project_type": "Web App",
                "description": "A practical verified project.",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "is_current": False,
                "project_url": None,
                "github_url": None,
                "technologies": ["Python"],
                "features": [],
                "achievements": [],
                "verified": True,
            },
            "Create the candidate profile before adding projects.",
        ),
        (
            "/api/skills",
            {
                "name": "Python",
                "category": "Programming Language",
                "proficiency": "Advanced",
                "years_experience": 3,
                "evidence": "Used in verified projects.",
                "is_primary": True,
                "verified": True,
            },
            "Create the candidate profile before adding skills.",
        ),
        (
            "/api/certifications",
            {
                "name": "Example Certification",
                "issuing_organization": "Example Org",
                "credential_id": None,
                "credential_url": None,
                "issue_date": "2024-01-01",
                "expiry_date": None,
                "does_not_expire": True,
                "description": None,
                "skills": ["Python"],
                "verified": True,
            },
            "Create the candidate profile before adding certifications.",
        ),
    ],
)
def test_child_records_require_authentication(
    client: TestClient,
    path: str,
    payload: dict[str, object],
    expected_detail: str,
) -> None:
    # The candidate profile now always exists for an authenticated caller,
    # so the "create the profile first" branch is unreachable while
    # authenticated. An UNAUTHENTICATED request must be rejected with 401.
    response = client.post(path, json=payload)

    assert response.status_code == 401


def test_education_crud(client: TestClient, account: Account) -> None:
    create_profile(client, account)

    payload = {
        "institution": "Example University",
        "degree": "MSc Computer Science",
        "field_of_study": "Computer Science",
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "grade": "Distinction",
        "location": "London",
        "description": "Verified coursework and dissertation.",
        "is_current": False,
        "verified": True,
    }

    created_response = client.post(
        "/api/education", json=payload, headers=account.headers
    )

    assert created_response.status_code == 201

    created = created_response.json()
    record_id = created["id"]

    assert created["candidate_profile_id"] == account.profile_id
    assert created["degree"] == "MSc Computer Science"

    list_response = client.get("/api/education", headers=account.headers)

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    updated_payload = {
        **payload,
        "degree": "MSc Artificial Intelligence",
    }
    updated_response = client.put(
        f"/api/education/{record_id}",
        json=updated_payload,
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["degree"] == (
        "MSc Artificial Intelligence"
    )

    assert_deleted(client, account, "/api/education", record_id)
    assert client.get("/api/education", headers=account.headers).json() == []


def test_experience_crud(client: TestClient, account: Account) -> None:
    create_profile(client, account)

    payload = {
        "company": "Example Ltd",
        "job_title": "Software Engineer",
        "employment_type": "Full-time",
        "location": "London",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "is_current": False,
        "description": "Verified role description.",
        "responsibilities": ["Built APIs"],
        "achievements": ["Improved release quality"],
        "technologies": ["Python", "FastAPI"],
        "verified": True,
    }

    created_response = client.post(
        "/api/experience", json=payload, headers=account.headers
    )

    assert created_response.status_code == 201

    record_id = created_response.json()["id"]

    assert client.get(
        "/api/experience", headers=account.headers
    ).json()[0]["company"] == ("Example Ltd")

    updated_response = client.put(
        f"/api/experience/{record_id}",
        json={
            **payload,
            "job_title": "Backend Engineer",
            "technologies": ["Python", "SQL"],
        },
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["job_title"] == "Backend Engineer"
    assert updated_response.json()["technologies"] == ["Python", "SQL"]

    assert_deleted(client, account, "/api/experience", record_id)
    assert client.get("/api/experience", headers=account.headers).json() == []


def test_project_crud_and_trimmed_required_text_validation(
    client: TestClient,
    account: Account,
) -> None:
    create_profile(client, account)

    with pytest.raises(ValidationError):
        ProjectCreate(
            name="  ",
            description="          ",
        )

    invalid_response = client.post(
        "/api/projects",
        json={
            "name": "  ",
            "role": None,
            "project_type": None,
            "description": "          ",
            "start_date": None,
            "end_date": None,
            "is_current": False,
            "project_url": None,
            "github_url": None,
            "technologies": [],
            "features": [],
            "achievements": [],
            "verified": False,
        },
        headers=account.headers,
    )

    assert invalid_response.status_code == 422

    payload = {
        "name": "Verified Project",
        "role": "Developer",
        "project_type": "Web App",
        "description": "A verified project with clear scope.",
        "start_date": "2024-01-01",
        "end_date": "2024-06-01",
        "is_current": False,
        "project_url": "https://example.com/project",
        "github_url": "https://github.com/example/project",
        "technologies": ["Python", "Next.js"],
        "features": ["Profile management"],
        "achievements": ["Delivered a working MVP"],
        "verified": True,
    }

    created_response = client.post(
        "/api/projects", json=payload, headers=account.headers
    )

    assert created_response.status_code == 201

    record_id = created_response.json()["id"]

    assert client.get(
        "/api/projects", headers=account.headers
    ).json()[0]["name"] == ("Verified Project")

    updated_response = client.put(
        f"/api/projects/{record_id}",
        json={
            **payload,
            "name": "Updated Verified Project",
            "achievements": ["Added persistent storage"],
        },
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["name"] == "Updated Verified Project"

    assert_deleted(client, account, "/api/projects", record_id)
    assert client.get("/api/projects", headers=account.headers).json() == []


def test_skill_crud_and_duplicate_name_check(
    client: TestClient,
    account: Account,
) -> None:
    create_profile(client, account)

    payload = {
        "name": "Python",
        "category": "Programming Language",
        "proficiency": "Advanced",
        "years_experience": 3,
        "evidence": "Used in verified projects.",
        "is_primary": True,
        "verified": True,
    }

    created_response = client.post(
        "/api/skills", json=payload, headers=account.headers
    )

    assert created_response.status_code == 201

    record_id = created_response.json()["id"]

    duplicate_response = client.post(
        "/api/skills",
        json={
            **payload,
            "name": " python ",
        },
        headers=account.headers,
    )

    assert duplicate_response.status_code == 409

    updated_response = client.put(
        f"/api/skills/{record_id}",
        json={
            **payload,
            "proficiency": "Expert",
            "years_experience": 4,
        },
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["proficiency"] == "Expert"
    assert updated_response.json()["years_experience"] == 4

    assert_deleted(client, account, "/api/skills", record_id)
    assert client.get("/api/skills", headers=account.headers).json() == []


def test_certification_crud(client: TestClient, account: Account) -> None:
    create_profile(client, account)

    payload = {
        "name": "Example Certification",
        "issuing_organization": "Example Org",
        "credential_id": "ABC-123",
        "credential_url": "https://example.com/credential",
        "issue_date": "2024-01-01",
        "expiry_date": None,
        "does_not_expire": True,
        "description": "Verified completed certification.",
        "skills": ["Python", "FastAPI"],
        "verified": True,
    }

    created_response = client.post(
        "/api/certifications",
        json=payload,
        headers=account.headers,
    )

    assert created_response.status_code == 201

    record_id = created_response.json()["id"]

    assert client.get(
        "/api/certifications", headers=account.headers
    ).json()[0]["name"] == ("Example Certification")

    updated_response = client.put(
        f"/api/certifications/{record_id}",
        json={
            **payload,
            "credential_id": "XYZ-789",
            "skills": ["Python"],
        },
        headers=account.headers,
    )

    assert updated_response.status_code == 200
    assert updated_response.json()["credential_id"] == "XYZ-789"

    assert_deleted(client, account, "/api/certifications", record_id)
    assert client.get(
        "/api/certifications", headers=account.headers
    ).json() == []

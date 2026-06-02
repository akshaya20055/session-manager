from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_start_and_get_session(client: TestClient) -> None:
    start_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-001"},
    )

    assert start_response.status_code == 201
    created = start_response.json()
    assert created["candidate_id"] == "candidate-001"
    assert created["status"] == "ACTIVE"
    assert created["started_at"] is not None
    assert created["created_at"] is not None
    assert created["updated_at"] is not None
    assert created["ended_at"] is None

    get_response = client.get(f"/api/v1/sessions/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_prevent_duplicate_active_sessions_for_candidate(client: TestClient) -> None:
    first_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-002"},
    )
    second_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-002"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["success"] is False
    assert "already has an ACTIVE" in second_response.json()["message"]


def test_update_session(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-003"},
    )
    session_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/sessions/{session_id}",
        json={"candidate_id": "candidate-003-updated"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["candidate_id"] == "candidate-003-updated"
    assert update_response.json()["status"] == "ACTIVE"


def test_pause_resume_and_end_session(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-004"},
    )
    session_id = create_response.json()["id"]

    pause_response = client.post(f"/api/v1/sessions/{session_id}/pause")
    resume_response = client.post(f"/api/v1/sessions/{session_id}/resume")
    end_response = client.post(f"/api/v1/sessions/{session_id}/end")

    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "PAUSED"
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "ACTIVE"
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "ENDED"
    assert end_response.json()["ended_at"] is not None


def test_list_sessions_with_status_filter(client: TestClient) -> None:
    active_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-005"},
    )
    ended_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-006"},
    )
    client.post(f"/api/v1/sessions/{ended_response.json()['id']}/end")

    response = client.get("/api/v1/sessions?status=ACTIVE")

    assert active_response.status_code == 201
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["status"] == "ACTIVE"
    assert sessions[0]["candidate_id"] == "candidate-005"


def test_missing_session_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/sessions/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "was not found" in response.json()["message"]


def test_invalid_uuid_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/sessions/not-a-uuid")

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "message": "Invalid UUID: session_id",
    }


def test_invalid_status_returns_422(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-007"},
    )
    session_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/sessions/{session_id}",
        json={"status": "RUNNING"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "message": "Invalid status: status",
    }


def test_empty_candidate_id_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "   "},
    )

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "message": "candidate_id cannot be empty",
    }


def test_missing_candidate_id_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/sessions/start", json={})

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "message": "Missing required field: candidate_id",
    }


def test_invalid_lifecycle_transition_returns_400(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/sessions/start",
        json={"candidate_id": "candidate-008"},
    )
    session_id = create_response.json()["id"]
    client.post(f"/api/v1/sessions/{session_id}/pause")

    response = client.post(f"/api/v1/sessions/{session_id}/pause")

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["message"] == "Only ACTIVE sessions can be paused"

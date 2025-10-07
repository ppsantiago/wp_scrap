import pytest


@pytest.mark.integration
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


@pytest.mark.integration
def test_create_comment_endpoint(client, sample_domain):
    domain, _ = sample_domain

    payload = {
        "content_type": "domain",
        "object_id": domain.id,
        "author": "api-tester",
        "content": "Comentario via API",
    }

    response = client.post("/api/comments", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["comment"]["author"] == "api-tester"
    assert data["comment"]["content"] == "Comentario via API"

    # Consultar comentarios del dominio
    res_list = client.get(f"/api/comments/entity/domain/{domain.id}")
    assert res_list.status_code == 200
    payload = res_list.json()
    assert payload["total_comments"] == 1


@pytest.mark.integration
def test_comment_search_and_statistics_api(client, sample_domain):
    domain, report = sample_domain

    create_payload = {
        "content_type": "report",
        "object_id": report.id,
        "author": "api-search",
        "content": "Comentario excelente desde API",
    }
    client.post("/api/comments", json=create_payload)

    search_response = client.get("/api/comments/search", params={"q": "excelente", "content_type": "report"})
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["total_results"] == 1

    stats_response = client.get("/api/comments/statistics", params={"content_type": "report"})
    assert stats_response.status_code == 200
    stats = stats_response.json()["statistics"]
    assert stats["total_comments"] == 1


@pytest.mark.integration
def test_comment_soft_delete_api(client, sample_domain):
    domain, _ = sample_domain

    create_payload = {
        "content_type": "domain",
        "object_id": domain.id,
        "author": "api-delete",
        "content": "Para borrar via API",
    }
    create_resp = client.post("/api/comments", json=create_payload)
    comment_id = create_resp.json()["comment"]["id"]

    delete_response = client.delete(f"/api/comments/{comment_id}", params={"soft_delete": True})
    assert delete_response.status_code == 200

    list_active = client.get(f"/api/comments/entity/domain/{domain.id}")
    assert list_active.json()["total_comments"] == 0

    list_all = client.get(f"/api/comments/entity/domain/{domain.id}", params={"include_inactive": True})
    assert list_all.json()["total_comments"] == 1

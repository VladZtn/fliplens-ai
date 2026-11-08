from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_image_accepts_png() -> None:
    response = client.post(
        "/ai/analyze-image",
        data={"title": "Apple MacBook Air M1", "description": "Used, good condition"},
        files={"image": ("macbook.png", b"fake-png-data", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_name"] == "Apple MacBook Air M1"
    assert "Received 1 image(s)" in body["summary"]


def test_analyze_image_rejects_unsupported_type() -> None:
    response = client.post(
        "/ai/analyze-image",
        data={"title": "Apple MacBook Air M1"},
        files={"image": ("notes.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 415


def test_analyze_image_requires_file() -> None:
    response = client.post(
        "/ai/analyze-image",
        data={"title": "Apple MacBook Air M1"},
    )

    assert response.status_code == 422

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_page_renders_foodfind_shell() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "FoodFind" in response.text
    assert "Nearby food discovery starts here." in response.text


import httpx

from app.main import create_app


async def test_health_check() -> None:
    """健康接口返回正常状态。"""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_in_openapi() -> None:
    """健康接口写入 OpenAPI。"""
    schema = create_app().openapi()

    assert "/health" in schema["paths"]

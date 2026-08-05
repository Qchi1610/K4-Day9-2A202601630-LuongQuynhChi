import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def verify():
    print("Testing lifespan startup and root endpoint...")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000") as client:
        res = await client.get("/api/v1/health")
        print(f"Health Response Status: {res.status_code}")
        print(f"Health Data: {res.json()}")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
    print("SUCCESS: App initialized and health check passed!")


if __name__ == "__main__":
    asyncio.run(verify())

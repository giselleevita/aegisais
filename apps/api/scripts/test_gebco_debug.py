"""Debug GEBCO WMS response."""
import httpx
import asyncio


async def main():
    url = "https://wms.gebco.net/mapserv"
    delta = 0.005
    lat, lon = 56.0, 3.0
    bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "GEBCO_LATEST",
        "QUERY_LAYERS": "GEBCO_LATEST",
        "INFO_FORMAT": "text/plain",
        "SRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": "3",
        "HEIGHT": "3",
        "X": "1",
        "Y": "1",
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print(f"Body: {resp.text[:500]}")
        print(f"URL: {resp.url}")


asyncio.run(main())

"""Try alternative GEBCO approaches."""
import httpx
import asyncio


async def main():
    url = "https://wms.gebco.net/mapserv"
    delta = 0.005
    lat, lon = 56.0, 3.0
    bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"

    # Try different layers for GetFeatureInfo
    for layer in ["GEBCO_Grid", "GEBCO_LATEST_2", "GEBCO_LATEST_SUB_ICE_TOPO"]:
        params = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetFeatureInfo",
            "LAYERS": layer,
            "QUERY_LAYERS": layer,
            "INFO_FORMAT": "text/plain",
            "SRS": "EPSG:4326",
            "BBOX": bbox,
            "WIDTH": "3",
            "HEIGHT": "3",
            "X": "1",
            "Y": "1",
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            is_error = "Exception" in resp.text
            print(f"{layer}: {resp.status_code} {'ERROR' if is_error else 'OK'} - {resp.text[:200]}")
        print()


asyncio.run(main())

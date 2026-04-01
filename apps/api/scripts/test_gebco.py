"""Quick script to test GEBCO WMS service."""
import httpx
import asyncio


async def test():
    urls = [
        "https://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv",
        "https://wms.gebco.net/mapserv",
    ]
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, params={
                    "SERVICE": "WMS",
                    "VERSION": "1.1.1",
                    "REQUEST": "GetCapabilities",
                })
                print(f"{url}: {resp.status_code} ({len(resp.text)} bytes)")
                if resp.status_code == 200:
                    if "gebco_latest" in resp.text:
                        print("  Found gebco_latest layer")
                    if "GEBCO_LATEST" in resp.text:
                        print("  Found GEBCO_LATEST layer")
                    for line in resp.text.split("\n"):
                        if "Name" in line and "gebco" in line.lower():
                            print(f"  Layer: {line.strip()}")
        except Exception as e:
            print(f"{url}: ERROR {e}")


asyncio.run(test())

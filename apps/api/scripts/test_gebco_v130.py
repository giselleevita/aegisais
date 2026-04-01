"""Try WMS 1.3.0 and different query params."""
import httpx
import asyncio


async def main():
    url = "https://wms.gebco.net/mapserv"
    lat, lon = 56.0, 3.0
    delta = 0.01

    # WMS 1.3.0 uses CRS and I/J instead of SRS and X/Y, BBOX order flips for 4326
    params_130 = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "GEBCO_LATEST",
        "QUERY_LAYERS": "GEBCO_LATEST",
        "INFO_FORMAT": "text/plain",
        "CRS": "EPSG:4326",
        "BBOX": f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}",
        "WIDTH": "3",
        "HEIGHT": "3",
        "I": "1",
        "J": "1",
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params_130)
        is_error = "Exception" in resp.text
        print(f"1.3.0 GEBCO_LATEST: {resp.status_code} {'ERROR' if is_error else 'OK'}")
        print(resp.text[:300])
        print()

    # Try GEBCO_Grid with 1.3.0
    params_130["LAYERS"] = "GEBCO_Grid"
    params_130["QUERY_LAYERS"] = "GEBCO_Grid"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params_130)
        is_error = "Exception" in resp.text
        print(f"1.3.0 GEBCO_Grid: {resp.status_code} {'ERROR' if is_error else 'OK'}")
        print(resp.text[:300])
        print()

    # Try GEBCO WCS
    wcs_params = {
        "SERVICE": "WCS",
        "VERSION": "1.0.0",
        "REQUEST": "GetCapabilities",
    }
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=wcs_params)
        print(f"WCS GetCapabilities: {resp.status_code} ({len(resp.text)} bytes)")
        if resp.status_code == 200 and "Coverage" in resp.text:
            print("  WCS is available!")
            for line in resp.text.split("\n"):
                if "name" in line.lower() and "gebco" in line.lower():
                    print(f"  {line.strip()}")


asyncio.run(main())

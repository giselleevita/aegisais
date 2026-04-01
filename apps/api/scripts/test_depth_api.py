"""Test alternative depth APIs."""
import httpx
import asyncio


async def main():
    lat, lon = 56.0, 3.0

    # Try Open Topo Data GEBCO endpoint (free, no key)
    url = f"https://api.opentopodata.org/v1/gebco2020?locations={lat},{lon}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            print(f"OpenTopoData GEBCO: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Result: {data}")
    except Exception as e:
        print(f"  Error: {e}")


asyncio.run(main())

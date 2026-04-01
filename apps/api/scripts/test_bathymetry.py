"""Quick test of bathymetry service with fixed GEBCO URL."""
import asyncio
from app.services.bathymetry import get_depth_at_position


async def main():
    depth = await get_depth_at_position(56.0, 3.0)
    print("Depth (North Sea 56N,3E):", depth)

    depth2 = await get_depth_at_position(59.0, 10.0)
    print("Depth (Skagerrak 59N,10E):", depth2)


asyncio.run(main())

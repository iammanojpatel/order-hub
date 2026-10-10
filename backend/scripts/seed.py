"""Seed realistic demo data through the public API (exercises the real code path).

Usage: uv run python scripts/seed.py [--count 500] [--base-url http://localhost:8000]
"""

import argparse
import asyncio
import random

import httpx
from dev_token import mint  # sibling script (scripts/ is on sys.path)

ADJECTIVES = ["Classic", "Organic", "Premium", "Eco", "Smart", "Vintage", "Ultra", "Urban"]
NOUNS = ["Mug", "T-Shirt", "Backpack", "Lamp", "Notebook", "Bottle", "Headphones", "Sneakers"]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    headers = {"Authorization": f"Bearer {mint()}"}
    sem = asyncio.Semaphore(20)  # bounded concurrency

    async with httpx.AsyncClient(base_url=args.base_url, headers=headers, timeout=10) as client:

        async def create(i: int) -> int:
            async with sem:
                body = {
                    "sku": f"SEED-{i:05d}",
                    "name": f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}",  # noqa: S311
                    "price_amount": f"{random.uniform(99, 9999):.2f}",  # noqa: S311
                    "currency": "INR",
                }
                r = await client.post(
                    "/api/v1/products", json=body, headers={"Idempotency-Key": body["sku"]}
                )
                return r.status_code

        codes = await asyncio.gather(*(create(i) for i in range(args.count)))
    print({c: codes.count(c) for c in set(codes)})  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())

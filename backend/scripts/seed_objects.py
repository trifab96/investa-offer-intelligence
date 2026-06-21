"""Seed the known-objects registry with a few entries.

Lets the mandatory dedup feature (4.2) be demonstrated immediately: re-uploading
an offer for one of these addresses triggers the "already known" reply path.

Run inside the backend container:
    python -m scripts.seed_objects
"""

from __future__ import annotations

import asyncio
import uuid

from app.db.models import KnownObject
from app.db.session import SessionLocal, init_db
from app.pipeline.addressing import normalize_text

# (address_raw, plz, ort, lat, lon)
SEED = [
    ("Schwanebecker Chaussee, 16321 Bernau bei Berlin", "16321", "Bernau bei Berlin", 52.6790, 13.5870),
    ("Bürgerstraße 44, 12347 Berlin", "12347", "Berlin", 52.4490, 13.4380),
    ("Wohnanlage Geesthacht, 21502 Geesthacht", "21502", "Geesthacht", 53.4360, 10.3760),
]


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        for address_raw, plz, ort, lat, lon in SEED:
            norm = normalize_text(address_raw)
            obj = KnownObject(
                id=uuid.uuid4(),
                address_raw=address_raw,
                address_norm=norm,
                plz=plz,
                ort=ort,
                lat=lat,
                lon=lon,
                dedup_key=norm,
            )
            session.add(obj)
        await session.commit()
    print(f"Seeded {len(SEED)} known objects.")


if __name__ == "__main__":
    asyncio.run(main())

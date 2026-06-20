from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

LOOKBACK_DAYS = 5


@dataclass
class MeterReading:
    zaehlpunkt: str
    daily_wh: float
    reading_date: str


def latest_daily_reading(client, zaehlpunkt: str, *, now: datetime | None = None) -> MeterReading | None:
    now = now or datetime.now()
    von = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    bis = now.strftime("%Y-%m-%d")
    data = client.get_daily_values(zaehlpunkt, von, bis)
    if not data:
        return None

    messwerte = (data.get("zaehlwerke") or [{}])[0].get("messwerte") or []
    if not messwerte:
        return None

    latest = messwerte[-1]
    return MeterReading(
        zaehlpunkt=zaehlpunkt,
        daily_wh=latest["messwert"],
        reading_date=latest["zeitBis"][:10],
    )

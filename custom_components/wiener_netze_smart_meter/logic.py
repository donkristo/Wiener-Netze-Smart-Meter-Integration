from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

LOOKBACK_DAYS = 5
API_DELAY_DAYS = 2
API_REQUEST_ERROR = "WNAPIRequestError"
INACTIVE_CUSTOMER_INTERFACE = "inactive"


@dataclass
class MeterReading:
    zaehlpunkt: str
    daily_wh: float
    reading_date: str


def _is_api_request_error(err: Exception) -> bool:
    return err.__class__.__name__ == API_REQUEST_ERROR


def is_active_zaehlpunkt(anlage: dict) -> bool:
    customer_interface = (anlage.get("idex") or {}).get("customerInterface")
    return str(customer_interface).strip().lower() != INACTIVE_CUSTOMER_INTERFACE


def _daily_window(now: datetime | None = None) -> tuple[str, str]:
    now = now or datetime.now()
    latest_available = now - timedelta(days=API_DELAY_DAYS)
    von = (latest_available - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    bis = latest_available.strftime("%Y-%m-%d")
    return von, bis


def _reading_from_payload(payload: dict, zaehlpunkt: str | None = None) -> MeterReading | None:
    zaehlpunkt = payload.get("zaehlpunkt") or zaehlpunkt
    if not zaehlpunkt:
        return None

    messwerte = (payload.get("zaehlwerke") or [{}])[0].get("messwerte") or []
    if not messwerte:
        return None

    latest = messwerte[-1]
    return MeterReading(
        zaehlpunkt=zaehlpunkt,
        daily_wh=latest["messwert"],
        reading_date=latest["zeitBis"][:10],
    )


def latest_daily_readings(client, *, now: datetime | None = None) -> dict[str, MeterReading]:
    von, bis = _daily_window(now)
    try:
        data = client.get_daily_values(None, von, bis)
    except Exception as err:
        if _is_api_request_error(err):
            return {}
        raise

    if not data:
        return {}

    payloads = data if isinstance(data, list) else [data]
    readings: dict[str, MeterReading] = {}
    for payload in payloads:
        reading = _reading_from_payload(payload)
        if reading:
            readings[reading.zaehlpunkt] = reading
    return readings


def latest_daily_reading(client, zaehlpunkt: str, *, now: datetime | None = None) -> MeterReading | None:
    von, bis = _daily_window(now)
    try:
        data = client.get_daily_values(zaehlpunkt, von, bis)
    except Exception as err:
        if _is_api_request_error(err):
            return None
        raise
    if not data:
        return None

    return _reading_from_payload(data, zaehlpunkt)


def quarter_hour_messwerte(
    client,
    zaehlpunkt: str,
    von: str | None = None,
    bis: str | None = None,
    paginate: bool = False,
    chunk_days: int = 90,
) -> list[dict]:
    try:
        data = client.get_quarter_hour_values(
            zaehlpunkt, von, bis, paginate=paginate, chunk_days=chunk_days
        )
    except Exception as err:
        if _is_api_request_error(err):
            return []
        raise
    if not data:
        return []
    return (data.get("zaehlwerke") or [{}])[0].get("messwerte") or []


def bucket_hourly(messwerte: list[dict]) -> list[tuple[datetime, float]]:
    """Sum quarter-hour Wh values into (hour_start_utc, wh) buckets, sorted by time."""
    buckets: dict[datetime, float] = defaultdict(float)
    for m in messwerte:
        start = datetime.strptime(m["zeitVon"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        hour = start.replace(minute=0, second=0, microsecond=0)
        buckets[hour] += m["messwert"]
    return sorted(buckets.items())


def parse_price_data(data: list[dict]) -> dict[datetime, float]:
    """Map hour-start (UTC) -> price_per_kwh from an EPEX Spot 'data' attribute."""
    prices: dict[datetime, float] = {}
    for entry in data or []:
        start = datetime.fromisoformat(entry["start_time"]).astimezone(timezone.utc)
        hour = start.replace(minute=0, second=0, microsecond=0)
        prices[hour] = float(entry["price_per_kwh"])
    return prices


def compute_hourly_cost(
    energy_buckets: list[tuple[datetime, float]],
    price_map: dict[datetime, float],
    *,
    start_after: datetime | None = None,
    starting_total: float = 0.0,
) -> list[tuple[datetime, float, float]]:
    """Return (hour_utc, hour_cost, cumulative_cost) for each priced energy hour.

    energy_buckets are (hour_utc, wh); price_map is {hour_utc: currency_per_kwh}.
    Hours at or before start_after, or with no known price, are skipped.
    """
    total = starting_total
    out: list[tuple[datetime, float, float]] = []
    for hour, wh in energy_buckets:
        if start_after is not None and hour <= start_after:
            continue
        price = price_map.get(hour)
        if price is None:
            # ponytail: no retro-fill of skipped hours; EPEX prices are known
            # day-ahead so a priced hour is essentially always available by the
            # time the (1-2 day lagged) energy arrives.
            continue
        cost = (wh / 1000.0) * price
        total += cost
        out.append((hour, cost, total))
    return out

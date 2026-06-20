from datetime import datetime

from logic import latest_daily_reading


class StubClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_daily_values(self, zaehlpunkt, von, bis):
        self.calls.append((zaehlpunkt, von, bis))
        return self.payload


def test_returns_latest_messwert():
    client = StubClient(
        {
            "zaehlwerke": [
                {
                    "messwerte": [
                        {"messwert": 100, "zeitBis": "2026-06-17T22:00:00.000Z"},
                        {"messwert": 200, "zeitBis": "2026-06-18T22:00:00.000Z"},
                    ]
                }
            ]
        }
    )
    reading = latest_daily_reading(client, "AT001", now=datetime(2026, 6, 19))
    assert reading.daily_wh == 200
    assert reading.reading_date == "2026-06-18"
    assert reading.zaehlpunkt == "AT001"


def test_returns_none_when_no_data():
    assert latest_daily_reading(StubClient(None), "AT001") is None
    assert latest_daily_reading(StubClient({"zaehlwerke": []}), "AT001") is None
    assert (
        latest_daily_reading(StubClient({"zaehlwerke": [{"messwerte": []}]}), "AT001")
        is None
    )


def test_uses_lookback_window():
    client = StubClient({"zaehlwerke": [{"messwerte": []}]})
    latest_daily_reading(client, "AT001", now=datetime(2026, 6, 19))
    zaehlpunkt, von, bis = client.calls[0]
    assert (zaehlpunkt, von, bis) == ("AT001", "2026-06-14", "2026-06-19")


if __name__ == "__main__":
    test_returns_latest_messwert()
    test_returns_none_when_no_data()
    test_uses_lookback_window()
    print("ok")

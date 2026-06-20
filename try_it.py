import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()

from wiener_netze_smart_meter_api import WNAPIClient


def build_client() -> WNAPIClient:
    return WNAPIClient(
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        api_key=os.environ["API_KEY"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiener Netze Smart Meter API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_anlagen = sub.add_parser("anlagen", help="List smart meter(s)")
    p_anlagen.add_argument("--zaehlpunkt", help="Specific meter identifier")

    for name, help_text in [
        ("quarter-hour", "Quarter-hourly measured values"),
        ("daily", "Daily measured values"),
        ("meter-readings", "Meter readings"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--zaehlpunkt", help="Specific meter identifier")
        p.add_argument("--von", help="Start date YYYY-MM-DD")
        p.add_argument("--bis", help="End date YYYY-MM-DD")
        p.add_argument("--paginate", action="store_true")
        p.add_argument("--chunk-days", type=int, default=90)

    args = parser.parse_args()
    client = build_client()

    if args.command == "anlagen":
        result = client.get_anlagendaten(args.zaehlpunkt)
    else:
        method = {
            "quarter-hour": client.get_quarter_hour_values,
            "daily": client.get_daily_values,
            "meter-readings": client.get_meter_readings,
        }[args.command]
        result = method(
            args.zaehlpunkt,
            args.von,
            args.bis,
            paginate=args.paginate,
            chunk_days=args.chunk_days,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

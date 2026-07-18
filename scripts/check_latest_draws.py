#!/usr/bin/env python3
"""Display the latest draw data currently stored by LottoLab.

This script reports database/API state only. It does not independently
verify draw freshness against an authoritative lottery source.
"""

from __future__ import annotations

import sys

import requests


BASE_URL = "https://lottolab.omchat.ovh/api/v1"
REQUEST_TIMEOUT_SECONDS = 15


def get_json(path: str) -> dict:
    """Fetch JSON from a LottoLab API endpoint."""
    response = requests.get(
        f"{BASE_URL}{path}",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    return response.json()


def main() -> int:
    """Display currently stored draw information."""
    print("=" * 60)
    print("LOTTOLAB STORED DRAW STATUS")
    print("=" * 60)

    try:
        data = get_json(
            "/draws/?limit=5"
        )

        draws = data.get(
            "draws",
            [],
        )

        print(
            f"\nReturned {len(draws)} draw records:"
        )

        for draw in draws:
            print(
                f"  {draw.get('draw_date')}: "
                f"{draw.get('numbers')} "
                f"({draw.get('lottery_type')})"
            )

        summary = get_json(
            "/statistics/summary"
        )

        date_range = summary.get(
            "date_range",
            {},
        )

        print(
            "\nTotal stored draws:",
            summary.get(
                "total_draws",
                0,
            ),
        )

        print(
            "Stored date range:",
            date_range.get(
                "start",
                "N/A",
            ),
            "to",
            date_range.get(
                "end",
                "N/A",
            ),
        )

        latest = summary.get(
            "latest_draw"
        )

        if latest:
            print(
                "Latest stored draw:",
                latest.get(
                    "draw_date",
                    "N/A",
                ),
                latest.get(
                    "lottery_type",
                    "",
                ),
            )

        print(
            "\nNote: this confirms LottoLab's stored "
            "data only; it does not independently verify "
            "that no newer official draw exists."
        )

        return 0

    except requests.RequestException as exc:
        print(
            f"Unable to query LottoLab API: {exc}"
        )
        return 1

    except (TypeError, ValueError) as exc:
        print(
            f"Unexpected API response: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

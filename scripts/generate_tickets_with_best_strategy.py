#!/usr/bin/env python3
"""Explain how to generate LottoLab strategy tickets safely.

Deprecated compatibility entry point.

Historical walk-forward testing found no statistically significant
evidence that Genetic, Sobol, Monte Carlo, or Hybrid strategies
outperform the Random baseline.

This script intentionally does not call the legacy simulation API,
because that endpoint currently evaluates each generated ticket
against all historical draws and therefore is not a valid predictive
backtest or ROI estimator.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Display migration guidance instead of misleading predictions."""
    print("=" * 72)
    print("LottoLab strategy generator migration notice")
    print("=" * 72)

    print(
        "\nNo strategy is currently validated as the "
        "'best strategy'."
    )

    print(
        "\nThe 500-target leakage-safe walk-forward "
        "experiment found no statistically significant "
        "strategy advantage over Random."
    )

    print(
        "\nThe legacy /api/v1/simulations endpoint should "
        "not be used to estimate predictive ROI because "
        "it evaluates tickets against historical draws "
        "using a best-ever-match methodology."
    )

    print(
        "\nUse scripts/compare_strategies_walkforward.py "
        "for research comparisons."
    )

    print(
        "\nA portfolio optimizer will replace this legacy "
        "ticket-selection workflow."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

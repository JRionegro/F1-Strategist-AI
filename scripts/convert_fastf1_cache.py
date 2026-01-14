"""Deprecated FastF1 converter placeholder (OpenF1 is the supported source)."""

from __future__ import annotations


def main() -> None:
    """Inform callers that FastF1 conversion is no longer supported."""

    raise RuntimeError(
        "FastF1 cache conversion is deprecated. Use OpenF1 fetchers instead."
    )


if __name__ == "__main__":
    main()

"""Pytest configuration and fixtures."""

import warnings
import pytest


@pytest.fixture(autouse=True)
def suppress_warnings():
    """
    Suppress known deprecation warnings.

    Filters out pandas BlockManager warnings that come from
    FastF1 internal implementation.
    """
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="pandas"
    )
    warnings.filterwarnings(
        "ignore",
        message="Passing a BlockManager to DataFrame",
        category=DeprecationWarning
    )

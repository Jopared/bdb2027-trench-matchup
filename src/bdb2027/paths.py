"""Data locations, resolved the same way locally and on Kaggle.

Override with the BDB_RAW_DIR / BDB_PROCESSED_DIR environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

KAGGLE_INPUT = Path("/kaggle/input/nfl-big-data-bowl-2027")
ON_KAGGLE = KAGGLE_INPUT.exists()

REPO_ROOT = Path(__file__).resolve().parents[2]

if ON_KAGGLE:
    _raw_default = KAGGLE_INPUT
    _processed_default = Path("/kaggle/working/processed")
else:
    _raw_default = REPO_ROOT / "data" / "raw"
    _processed_default = REPO_ROOT / "data" / "processed"

RAW_DIR = Path(os.environ.get("BDB_RAW_DIR", _raw_default))
PROCESSED_DIR = Path(os.environ.get("BDB_PROCESSED_DIR", _processed_default))
FIGURES_DIR = REPO_ROOT / "figures"

TABLES = (
    "players",
    "combine_results",
    "combine_tracking",
    "player_career_successes",
    "player_play",
    "games",
    "game_tracking_2023",
    "game_tracking_2024",
    "game_tracking_2025",
)


def raw_csv(table: str) -> Path:
    return RAW_DIR / f"{table}.csv"


def parquet(table: str) -> Path:
    return PROCESSED_DIR / f"{table}.parquet"

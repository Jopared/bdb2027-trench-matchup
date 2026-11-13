"""Shared style and paths for the figure scripts (dataviz skill: reference palette, light mode)."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

# reference palette (light): categorical slots 1-3, ink and chrome
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RED = "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
# sequential blue ramp steps 100 -> 700 (magnitude, e.g. speed)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", SEQ)
# diverging blue <-> red with gray midpoint
DIV_CMAP = LinearSegmentedColormap.from_list("div", ["#184f95", "#6da7ec", "#f0efec", "#ee8a89", "#b52f2e"])

DPI = 200


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9,
        "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
        "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "legend.frameon": False,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "lines.solid_capstyle": "round",
    })


def save(fig, name: str, df=None):
    """Write figures/<name>.png (200 dpi) and, when df is given, figures/<name>.csv."""
    fig.savefig(FIG / f"{name}.png", dpi=DPI)
    if df is not None:
        df.to_csv(FIG / f"{name}.csv", index=False)
    print("wrote", FIG / f"{name}.png")


def panel_tag(ax, tag):
    ax.text(-0.02, 1.07, tag, transform=ax.transAxes, fontsize=11, fontweight="bold", color=INK, va="bottom", ha="right")


# ---------------------------------------------------------------- results-directory helpers (F4-F6)
import argparse
import json
import re

DEFAULT_RES = PROC / "confirmatory_sim" / "201"
MDE = 0.247  # registered minimum detectable effect, log-odds per SD of the gap


def parse_results_args(desc):
    """Argument: a results directory. Two layouts are accepted.
    sim layout  : everything in one folder (confirmatory_results.json, tables/, forest_data.csv, ...).
    real layout : <dir> = reports/ holds confirmatory_results.json (tables in <dir>/confirmatory/tables) and the data products
                  live in <repo>/data/processed/confirmatory/ (detected by the presence of <dir>/confirmatory/).
    Returns (data_dir, json, is_simulated, tables_dir)."""
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("results_dir", nargs="?", default=str(DEFAULT_RES),
                    help="folder with confirmatory_results.json (default: simulated run; real run: reports)")
    a = ap.parse_args()
    d = Path(a.results_dir)
    j = json.loads((d / "confirmatory_results.json").read_text(encoding="utf-8"))
    if (d / "confirmatory").is_dir() and not (d / "forest_data.csv").exists():
        data_dir, tables_dir = PROC / "confirmatory", d / "confirmatory" / "tables"
    else:
        data_dir, tables_dir = d, d / "tables"
    return data_dir, j, j.get("mode") == "simulate", tables_dir


REAL_NAMES = {"F4": "F4_forest", "F5": "F5_surface", "F6": "F6_robustness"}


def fig_name(base, sim):
    return f"sim_{base}" if sim else REAL_NAMES.get(base, base)


def sim_tag(sim):
    return "SIMULATED (planted effect, not real data). " if sim else ""


_NUM = r"(-?\d+\.\d+)"


def parse_est(txt):
    """'0.315 [0.130, 0.514] ...' -> (0.315, 0.130, 0.514). Takes the first 'est [lo, hi]' in the string."""
    m = re.match(rf"\s*{_NUM}\s*\[\s*{_NUM}\s*,\s*{_NUM}\s*\]", str(txt))
    return tuple(float(v) for v in m.groups()) if m else (np.nan, np.nan, np.nan)


import numpy as np  # noqa: E402

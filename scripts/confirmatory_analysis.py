#!/usr/bin/env python
"""Frozen confirmatory analysis for "The athletic gap" (pre-registration: reports/preregistration.md, section 13.3).

Modes (section 13.3):
  python scripts/confirmatory_analysis.py --mode simulate --sim-beta-gap 0.0 --sim-seed 1 [--light] [--only STEP]
  python scripts/confirmatory_analysis.py --mode confirmatory [--rerun-reason "text"]

Design notes
  * Self-contained: everything that decides the analysis lives in THIS file, so SCRIPT_SHA256 covers it. The only
    project imports are bdb2027.paths and bdb2027.traits (the latter is hashed through INPUT_SHA256).
  * The path of the outcome file is referenced in exactly one function (load_sealed_outcomes), which refuses to run
    unless the mode is confirmatory and every guard has passed.
  * All Bayesian fits go through nutpie (numba backend); posterior summaries are computed in numpy.
"""
from __future__ import annotations

import os

_fl = os.environ.get("PYTENSOR_FLAGS", "")
if "cxx=" not in _fl:
    os.environ["PYTENSOR_FLAGS"] = (_fl + "," if _fl else "") + "cxx="

import argparse
import datetime as _dt
import hashlib
import importlib.metadata as _imd
import json
import math
import platform
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import scipy.sparse as sp
from scipy import stats
from scipy.special import expit, logit

from bdb2027 import paths

try:  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = Path(paths.REPO_ROOT)
PREREG_PATH = REPO_ROOT / "reports" / "preregistration.md"

# ----------------------------------------------------------------------------------------------- constants
BASE_RATE = 0.0952
GEN_B_PICK = -0.20
GEN_B_DROP = 0.58
GEN_RE_SD = 0.35
KAPPA = 1.20
SESOI = 0.10
SEED = 2027
SEED_ESC = 2028
GAP_SD_REGISTERED = 1.253          # section 5.6 / V5: observed SD of the registered gap (fixed units for permutation)
PEAK_NULL_RATE_SIM = 0.003

MEAS = ["combine_weight", "arm_length", "forty", "ten_yd_split", "short_shuttle", "three_cone", "ngs_athleticism_score"]
MSHORT = {"combine_weight": "weight", "arm_length": "arm", "forty": "forty", "ten_yd_split": "ten",
          "short_shuttle": "shuttle", "three_cone": "cone", "ngs_athleticism_score": "ngs"}
DD = [f"dd_d{d}_{b}" for d in (1, 2, 3) for b in ("short", "med", "long") if (d, b) != (1, "long")]
C_COLS = (["db1", "db2", "db3"] + DD + ["shotgun", "play_action", "s2023", "s2024", "pos_T", "pos_C", "edge",
                                         "double_team", "pre0", "pre2"])
Q_SIZE = ["d_weight", "s_weight", "d_arm", "s_arm"]
Q_REST = (["d_forty", "s_forty", "d_ten", "s_ten", "d_shuttle", "s_shuttle", "d_cone", "s_cone", "d_ngs", "s_ngs"]
          + ["f_dash_B", "f_dash_R", "f_shuttle_B", "f_shuttle_R", "f_cone_B", "f_cone_R"])
Q_COLS = Q_SIZE + Q_REST
K_COLS = ["d_lpick", "f_undr_B", "f_undr_R"]
STD_COLS = (["db1", "db2", "db3"] + [f"{p}_{MSHORT[m]}" for m in MEAS for p in ("d", "s")]
            + ["d_lpick", "s_lpick", "gap", "c_R", "c_B", "s_comp"])
SPLINE_COLS = ["db1", "db2", "db3"]
EXPECTED = {  # section 2.3 (and 9): reps, blockers, rushers, dyads, (2023, 2024, 2025), REG
    "P": dict(reps=7214, blockers=69, rushers=97, dyads=1201, seasons=(431, 1821, 4962), reg=6867),
    "PL": dict(reps=17795), "ALL": dict(reps=25009),
    "P-A": dict(reps=7720, blockers=75, rushers=97, dyads=1281, seasons=(431, 1882, 5407), reg=7297),
    "PL-A": dict(reps=18849),
    "P-B": dict(reps=8087, blockers=79, rushers=97, dyads=1342, reg=7664),
    "P-DL": dict(reps=8087, blockers=79, rushers=97, dyads=1342),
    "SA1": dict(reps=6394), "SA2": dict(reps=8924), "SA3": dict(reps=7448), "SA4": dict(reps=6643),
    "SA5": dict(reps=6867), "SA6": dict(reps=6261), "SA7": dict(reps=5326),
    "R": dict(reps=8087, blockers=79, rushers=97),
}
EXPECTED_FACTS = {  # facts about P (section 2.3)
    "E0 pairs": 27711, "E0 engaged": 8087,
    "blocker G": 3365, "blocker T": 3026, "blocker C": 823, "rusher EDGE": 3156, "rusher INTERIOR_LINE": 4058,
    "nfl DT": 2550, "nfl DE": 2513, "nfl OLB": 1888, "nfl NT": 263, "double_team": 953,
    "pre0": 114, "pre1": 6831, "pre2": 269, "down1": 2662, "down2": 2410, "down3": 1932, "down4": 210,
}
REQUIRED_INPUTS = ["data/processed/engaged_pairs.parquet", "data/processed/player_baselines.parquet",
                   "data/processed/combine_traits.parquet", "data/processed/combine_tracking.parquet",
                   "data/processed/combine_results.parquet", "src/bdb2027/traits.py", "src/bdb2027/paths.py"]
STATE = {"mode": None, "guards_passed": False}
LOGBUF: list[str] = []
T0 = time.time()


def log(msg: str = "") -> None:
    line = f"[{time.time() - T0:8.1f}s] {msg}"
    LOGBUF.append(line)
    print(line, flush=True)


# ----------------------------------------------------------------------------------------------- manifest / guards
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(text: str) -> dict:
    """Parse the freeze manifest block of section 13.1 (and the machine-readable MDE lines of section 12)."""
    i0 = text.find("### 13.1")
    i1 = text.find("### 13.2")
    block = text[i0:i1] if i0 >= 0 and i1 > i0 else ""
    man: dict = {"input_sha": {}}
    pat = re.compile(r"^\s{2,}(SCRIPT_SHA256|INPUT_SHA256 \S+|PACKAGE_VERSIONS|SAMPLER|KAPPA_GLM_SE_INFLATION|"
                     r"CALIBRATION_CONTINGENCY|PERMUTATION_CALIBRATION|FREEZE_COMMIT):\s*(.*?)\s*$", re.M)
    for key, val in pat.findall(block):
        if key.startswith("INPUT_SHA256 "):
            man["input_sha"][key.split(" ", 1)[1]] = val
        else:
            man[key] = val
    for key in ("MDE_REGISTERED_LOGODDS", "MDE_SENSA_LOGODDS"):
        m = re.search(rf"^\s*{key}:\s*([0-9.]+)\s*$", text, re.M)
        man[key] = float(m.group(1)) if m else None
    return man


def manifest_incomplete(man: dict) -> list[str]:
    """Names of required manifest fields that are missing or still say [fill (FREEZE_COMMIT is not required here)."""
    bad = []
    for key in ("SCRIPT_SHA256", "PACKAGE_VERSIONS", "KAPPA_GLM_SE_INFLATION", "CALIBRATION_CONTINGENCY",
                "PERMUTATION_CALIBRATION"):
        v = man.get(key)
        if not v or "[fill" in v:
            bad.append(key)
    if not man["input_sha"]:
        bad.append("INPUT_SHA256 (none parsed)")
    for req in REQUIRED_INPUTS:
        if req not in man["input_sha"]:
            bad.append(f"INPUT_SHA256 {req} missing")
    for p, v in man["input_sha"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", v):
            bad.append(f"INPUT_SHA256 {p}")
    if man.get("MDE_REGISTERED_LOGODDS") is None or man.get("MDE_SENSA_LOGODDS") is None:
        bad.append("MDE lines")
    cc = (man.get("CALIBRATION_CONTINGENCY") or "").strip().upper()
    if "[fill" not in cc.lower() and not (cc.startswith("ACTIVE") or cc.startswith("INACTIVE")):
        bad.append("CALIBRATION_CONTINGENCY (must start with ACTIVE or INACTIVE)")
    return bad


def installed_versions() -> dict:
    out = {"python": platform.python_version()}
    for name in ("pymc", "arviz", "pytensor", "nutpie", "numba", "statsmodels", "numpy", "pandas", "polars", "scipy"):
        out[name] = _imd.version(name)
    return out


def check_versions(man: dict) -> list[str]:
    want = {}
    for part in man["PACKAGE_VERSIONS"].split(";"):
        part = part.strip()
        if part:
            k, v = part.split(" ", 1)
            want[k] = v.strip()
    have = installed_versions()
    return [f"{k}: manifest {v}, installed {have.get(k)}" for k, v in want.items() if have.get(k) != v]


def contingency_from_manifest(man: dict) -> tuple[bool | None, str]:
    s = (man.get("CALIBRATION_CONTINGENCY") or "").strip()
    u = s.upper()
    if u.startswith("INACTIVE"):
        return False, s
    if u.startswith("ACTIVE"):
        return True, s
    return None, s


def run_guards(rerun_reason: str | None) -> dict:
    """Guards of section 13.3 for confirmatory mode. Raises SystemExit with a message on any failure. The completeness
    check comes first, so nothing is hashed while the manifest still has [fill fields."""
    if STATE["mode"] != "confirmatory":
        raise RuntimeError("guards are for confirmatory mode only")
    text = PREREG_PATH.read_text(encoding="utf-8")
    man = parse_manifest(text)
    bad = manifest_incomplete(man)
    if bad:
        raise SystemExit("GUARD FAILED: freeze manifest incomplete: " + "; ".join(bad))
    info = {"manifest": man}
    # guard 1: own hash
    mine = sha256_file(SCRIPT_PATH)
    info["sha_script"], info["sha_registered"] = mine, man["SCRIPT_SHA256"]
    if mine != man["SCRIPT_SHA256"]:
        raise SystemExit(f"GUARD 1 FAILED: script sha256 {mine} != registered {man['SCRIPT_SHA256']}")
    # guard 2: input hashes
    match = {}
    for rel, want in man["input_sha"].items():
        got = sha256_file(REPO_ROOT / rel)
        match[rel] = got == want
    info["input_match"] = match
    if not all(match.values()):
        raise SystemExit("GUARD 2 FAILED: input hash mismatch: " + ", ".join(k for k, v in match.items() if not v))
    # guard 2b: package versions
    diff = check_versions(man)
    if diff:
        raise SystemExit("GUARD 2b FAILED: package versions differ: " + "; ".join(diff))
    # guard 2c: calibration contingency
    active, raw = contingency_from_manifest(man)
    if active is None:
        raise SystemExit("GUARD 2c FAILED: CALIBRATION_CONTINGENCY is not ACTIVE/INACTIVE")
    info["contingency_active"], info["contingency_text"] = active, raw
    # guard 3: single run
    res_md = REPO_ROOT / "reports" / "confirmatory_results.md"
    info["run_dir"] = None
    if res_md.exists():
        if not rerun_reason:
            raise SystemExit("GUARD 3 FAILED: reports/confirmatory_results.md exists; use --rerun-reason")
        base = REPO_ROOT / "reports" / "confirmatory"
        n = 1
        while (base / f"run_{n:02d}").exists():
            n += 1
        info["run_dir"] = base / f"run_{n:02d}"
        dev = REPO_ROOT / "reports" / "deviations.md"
        with open(dev, "a", encoding="utf-8") as fh:
            fh.write(f"\n- {_dt.datetime.now().isoformat(timespec='seconds')} rerun run_{n:02d}: {rerun_reason}\n")
    elif rerun_reason:
        raise SystemExit("--rerun-reason given but no previous confirmatory_results.md exists")
    # guard 4: provenance
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=30).stdout.strip() or "unavailable"
    except Exception:
        head = "unavailable"
    info["git_head"] = head
    info["sha_prereg"] = sha256_file(PREREG_PATH)
    info["versions"] = installed_versions()
    info["cpu_count"] = os.cpu_count()
    info["start"] = _dt.datetime.now().isoformat(timespec="seconds")
    STATE["guards_passed"] = True
    return info


def load_sealed_outcomes() -> pd.DataFrame:
    """The ONLY place that names the outcome file. Refuses unless confirmatory mode and all guards passed."""
    if STATE["mode"] != "confirmatory" or not STATE["guards_passed"]:
        raise RuntimeError("outcome file may only be loaded in confirmatory mode after all guards passed")
    p = paths.PROCESSED_DIR / "engaged_outcomes_SEALED.parquet"
    cols = ["game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id", "pressure_allowed",
            "peak_pressure_probability_allowed", "rusher_time_to_pressure"]
    return pl.read_parquet(p, columns=cols).to_pandas()


# ----------------------------------------------------------------------------------------------- data assembly
KEYS = ["game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id"]
BASE_NUM = MEAS + ["log_pick", "draft_overall_pick", "undrafted", "draft_year"]


def load_inputs() -> dict:
    pairs = pl.read_parquet(paths.parquet("engaged_pairs")).to_pandas()
    base = pl.read_parquet(paths.parquet("player_baselines")).to_pandas().set_index("nfl_id")
    traits = pl.read_parquet(paths.parquet("combine_traits")).to_pandas().set_index("nfl_id")
    games = pl.read_parquet(paths.parquet("games")).to_pandas()
    return dict(pairs=pairs, base=base, traits=traits, games=games)


def boolf(s: pd.Series) -> np.ndarray:
    """True/False/None -> 1.0/0.0/NaN."""
    return s.map({True: 1.0, False: 0.0}).astype(float).to_numpy()


def build_frame(inp: dict) -> pd.DataFrame:
    F = inp["pairs"].copy().reset_index(drop=True)
    base = inp["base"]
    for suf, idc in (("B", "blocker_nfl_id"), ("R", "rusher_nfl_id")):
        for c in BASE_NUM:
            F[f"{c}_{suf}"] = F[idc].map(base[c]).astype(float)
        for c in ("composite", "composite_sensA", "composite_sensB"):
            F[f"{c}_{suf}"] = F[idc].map(inp["traits"][c]).astype(float)
    F["eng"] = F["engaged_primary"].astype(bool)
    F["E0"] = (F.blocker_lined_up_position.isin(["T", "G", "C"]) & (F.blocker_combine_position == "OL")
               & (F.rusher_combine_position == "DL") & F.rusher_lined_up_position.isin(["EDGE", "INTERIOR_LINE"]))
    F["shotgun_f"] = boolf(F["shotgun"])
    F["pa_f"] = boolf(F["play_action"])
    F["dt_f"] = boolf(F["double_team"])
    need = ["dropback_duration", "down", "yards_to_go", "shotgun_f", "pa_f", "pass_rushers_encountered", "season",
            "dt_f"]
    F["ctx_ok"] = F[need].notna().all(axis=1)
    return F


def double_team_variant(F: pd.DataFrame, flag: str) -> np.ndarray:
    """>= 1 OTHER pair on the same (game, play, rusher) engaged under the variant flag (self excluded)."""
    e = F[flag].astype(bool)
    cnt = e.groupby([F.game_id, F.play_id, F.rusher_nfl_id]).transform("sum")
    return ((cnt - e.astype(int)) >= 1).to_numpy().astype(float)


def harrell_rcs(x: np.ndarray, t: np.ndarray) -> list[np.ndarray]:
    """Section 5.2: db1 = x; db(j+1) for j = 1, 2 (4 knots, Harrell parametrisation)."""
    def p3(u):
        return np.clip(u, 0, None) ** 3
    t1, t2, t3, t4 = t
    out = [np.asarray(x, float)]
    for tj in (t1, t2):
        out.append((p3(x - tj) - p3(x - t3) * (t4 - tj) / (t4 - t3) + p3(x - t4) * (t3 - tj) / (t4 - t3)) / (t4 - t1) ** 2)
    return out


def side_z(F: pd.DataFrame, const_side: dict) -> dict:
    z = {}
    for m in MEAS:
        for s in ("B", "R"):
            mu, sd = const_side[(m, s)]
            z[(m, s)] = np.nan_to_num((F[f"{m}_{s}"].to_numpy(float) - mu) / sd, nan=0.0)
    return z


def raw_columns(F: pd.DataFrame, const_side: dict, knots: np.ndarray, cB: np.ndarray, cR: np.ndarray,
                dt_override: np.ndarray | None = None) -> dict:
    n = len(F)
    R: dict[str, np.ndarray] = {}
    for i, c in enumerate(harrell_rcs(F.dropback_duration.to_numpy(float), knots)):
        R[f"db{i + 1}"] = c
    dn = np.minimum(F.down.to_numpy(float), 3)
    ytg = F.yards_to_go.to_numpy(float)
    bucket = np.where(ytg <= 3, "short", np.where(ytg <= 7, "med", "long"))
    for d in (1, 2, 3):
        for b in ("short", "med", "long"):
            if (d, b) != (1, "long"):
                R[f"dd_d{d}_{b}"] = ((dn == d) & (bucket == b)).astype(float)
    R["shotgun"] = F.shotgun_f.to_numpy(float)
    R["play_action"] = F.pa_f.to_numpy(float)
    R["s2023"] = (F.season.to_numpy() == 2023).astype(float)
    R["s2024"] = (F.season.to_numpy() == 2024).astype(float)
    R["pos_T"] = (F.blocker_lined_up_position.to_numpy() == "T").astype(float)
    R["pos_C"] = (F.blocker_lined_up_position.to_numpy() == "C").astype(float)
    R["edge"] = (F.rusher_lined_up_position.to_numpy() == "EDGE").astype(float)
    R["double_team"] = F.dt_f.to_numpy(float) if dt_override is None else dt_override
    pre = F.pass_rushers_encountered.to_numpy(float)
    R["pre0"] = (pre == 0).astype(float)
    R["pre2"] = (pre >= 2).astype(float)
    z = side_z(F, const_side)
    for m in MEAS:
        R[f"d_{MSHORT[m]}"] = z[(m, "R")] - z[(m, "B")]
        R[f"s_{MSHORT[m]}"] = z[(m, "R")] + z[(m, "B")]
    R["f_dash_B"] = F.forty_B.isna().to_numpy(float)
    R["f_dash_R"] = F.forty_R.isna().to_numpy(float)
    R["f_shuttle_B"] = F.short_shuttle_B.isna().to_numpy(float)
    R["f_shuttle_R"] = F.short_shuttle_R.isna().to_numpy(float)
    R["f_cone_B"] = F.three_cone_B.isna().to_numpy(float)
    R["f_cone_R"] = F.three_cone_R.isna().to_numpy(float)
    R["d_lpick"] = F.log_pick_R.to_numpy(float) - F.log_pick_B.to_numpy(float)
    R["s_lpick"] = F.log_pick_R.to_numpy(float) + F.log_pick_B.to_numpy(float)
    R["f_undr_B"] = F.undrafted_B.to_numpy(float)
    R["f_undr_R"] = F.undrafted_R.to_numpy(float)
    R["gap"] = cR - cB
    R["c_R"] = cR.copy()
    R["c_B"] = cB.copy()
    R["s_comp"] = cR + cB
    for m in MEAS:  # rusher-side player z (S5b)
        R[f"zR_{MSHORT[m]}"] = z[(m, "R")]
    return R


class Version:
    """One composite version: composite columns, primary set, transformation constants (section 5.1) and the full
    standardised column table Xall (all pairs; NaN where undefined)."""

    def __init__(self, name: str, F: pd.DataFrame, cB: np.ndarray, cR: np.ndarray, prim: np.ndarray):
        self.name, self.cB, self.cR, self.prim = name, cB, cR, prim
        idx = np.flatnonzero(prim)
        self.side = {}
        for s, idc in (("B", "blocker_nfl_id"), ("R", "rusher_nfl_id")):
            pl_ids = pd.unique(F[idc].to_numpy()[idx])
            sub = F.iloc[idx].drop_duplicates(idc)
            for m in MEAS:
                v = sub[f"{m}_{s}"].to_numpy(float)
                self.side[(m, s)] = (float(np.nanmean(v)), float(np.nanstd(v, ddof=1)))
            self.n_players = getattr(self, "n_players", {})
            self.n_players[s] = len(pl_ids)
        self.knots = np.quantile(F.dropback_duration.to_numpy(float)[idx], [0.05, 0.35, 0.65, 0.95])
        raw = raw_columns(F, self.side, self.knots, cB, cR)
        self.std: dict[str, tuple[float, float]] = {}
        X = {}
        for c, v in raw.items():
            if c in STD_COLS:
                vv = v[idx]
                if np.isfinite(vv).any():
                    mu, sd = float(np.nanmean(vv)), float(np.nanstd(vv, ddof=1))
                    self.std[c] = (mu, sd)
                    X[c] = (v - mu) / sd
                else:
                    X[c] = np.full(len(v), np.nan)
            else:
                X[c] = v
        # Orthonormalisation of the spline block (section 5.2): Gram-Schmidt in the order db1, db2, db3 over the
        # primary-set reps, each result rescaled to SD 1 over the primary set; the 3x3 transform is a constant.
        B = np.column_stack([X["db1"], X["db2"], X["db3"]])
        Bp = B[idx]
        before = np.corrcoef(Bp.T)
        Qm, Rm = np.linalg.qr(Bp)
        sg = np.sign(np.diag(Rm))
        Rm = Rm * sg[:, None]
        self.spline_T = np.linalg.inv(Rm) * math.sqrt(len(idx) - 1.0)
        Bn = B @ self.spline_T
        after = np.corrcoef(Bn[idx].T)
        for j, c in enumerate(("db1", "db2", "db3")):
            X[c] = Bn[:, j]
        self.spline_corr = (before, after)
        log(f"spline block [{name}]: correlation before orthonormalisation {np.round(before[np.triu_indices(3, 1)], 4).tolist()} "
            f"(db1-db2, db1-db3, db2-db3); after {np.round(after[np.triu_indices(3, 1)], 6).tolist()}")
        self.X = pd.DataFrame(X)
        self.X["gap_edge"] = self.X["gap"] * self.X["edge"]
        self.X["c_R_edge"] = self.X["c_R"] * self.X["edge"]
        self.X["c_B_edge"] = self.X["c_B"] * self.X["edge"]
        # S5: blocker back displacement at 0.5 s, standardised on the primary set
        bd = F.blocker_back_disp_05s.to_numpy(float)
        mu, sd = float(np.nanmean(bd[idx])), float(np.nanstd(bd[idx], ddof=1))
        self.std["depth"] = (mu, sd)
        self.X["depth"] = (bd - mu) / sd
        self.gap_sd = self.std["gap"][1] if "gap" in self.std else float("nan")
        self.sd_lpd = self.std["d_lpick"][1]


def build_sets(F: pd.DataFrame, V: dict) -> dict:
    """Named analysis sets as boolean masks over F (section 2.3 / 9). Row dropping for context nulls is NOT applied
    here (counts are the pre-drop counts of the spec)."""
    E0, eng = F.E0.to_numpy(), F.eng.to_numpy()
    S = {}
    reg, A, B, DL = V["reg"], V["A"], V["B"], V["DL"]
    S["P"] = reg.prim.copy()
    both = lambda v: np.isfinite(v.cB) & np.isfinite(v.cR)
    S["PL"] = E0 & ~eng & both(reg)
    S["ALL"] = S["P"] | S["PL"]
    S["P-A"] = A.prim.copy()
    S["PL-A"] = E0 & ~eng & both(A)
    S["P-B"] = B.prim.copy()
    S["P-DL"] = DL.prim.copy()
    for tag, col in (("SA1", "engaged_d125"), ("SA2", "engaged_d200"), ("SA3", "engaged_k3"), ("SA4", "engaged_k6")):
        S[tag] = E0 & F[col].astype(bool).to_numpy() & both(reg)
    S["SA5"] = S["P"] & (F.season_type.to_numpy() == "REG")
    S["SA6"] = S["P"] & ~(F.double_team.to_numpy() == True)  # noqa: E712
    S["SA7"] = S["P"] & F.rusher_nfl_position.isin(["DE", "DT", "NT"]).to_numpy()
    # SA9: one pair per (game, play, blocker): smallest min_dist (ties: smallest rusher id)
    idx = np.flatnonzero(S["P"])
    sub = F.iloc[idx].sort_values(["min_dist", "rusher_nfl_id"], kind="mergesort")
    keep = sub.drop_duplicates(["game_id", "play_id", "blocker_nfl_id"]).index.to_numpy()
    m9 = np.zeros(len(F), bool)
    m9[keep] = True
    S["SA9"] = m9
    S["SA11"] = S["P"] & np.isfinite(A.cB) & np.isfinite(A.cR)
    S["SA15"] = S["P"] & ~F.forty_B.isna().to_numpy() & ~F.forty_R.isna().to_numpy()
    S["R"] = E0 & eng
    return S


def set_counts(F: pd.DataFrame, mask: np.ndarray) -> dict:
    d = F[mask]
    dy = d.groupby(["blocker_nfl_id", "rusher_nfl_id"]).ngroups
    return dict(reps=int(mask.sum()), blockers=int(d.blocker_nfl_id.nunique()), rushers=int(d.rusher_nfl_id.nunique()),
                dyads=int(dy), s2023=int((d.season == 2023).sum()), s2024=int((d.season == 2024).sum()),
                s2025=int((d.season == 2025).sum()), reg=int((d.season_type == "REG").sum()),
                ctx_dropped=int((~d.ctx_ok).sum()))


# ----------------------------------------------------------------------------------------------- design + hygiene
class Design:
    """Fixed-effect matrix of one fit (after column hygiene) and the cluster identifiers of its rows."""

    def __init__(self, Xdf: pd.DataFrame, idx: np.ndarray, F: pd.DataFrame, drops: list):
        self.names = list(Xdf.columns)
        self.X = Xdf.to_numpy(float)
        self.idx = idx
        self.drops = drops
        self.n, self.k = self.X.shape
        bl, ru = F.blocker_nfl_id.to_numpy()[idx], F.rusher_nfl_id.to_numpy()[idx]
        self.bid = pd.factorize(bl)[0]
        self.rid = pd.factorize(ru)[0]
        self.did = pd.factorize(pd.Series(bl).astype(str) + "_" + pd.Series(ru).astype(str))[0]
        self.nb, self.nr, self.nd = self.bid.max() + 1, self.rid.max() + 1, self.did.max() + 1
        self.bl_ids = pd.unique(bl)
        self.ru_ids = pd.unique(ru)

    def col(self, name: str) -> np.ndarray:
        return self.X[:, self.names.index(name)]


PROTECTED = ("gap", "c_R", "c_B", "d_lpick")


def make_design(Xall: pd.DataFrame, idx: np.ndarray, cols: list[str], F: pd.DataFrame, tag: str = "") -> Design:
    """Column hygiene (section 5.2): on the rows of the set being fitted, drop constant columns, then columns that
    exactly duplicate an earlier column. Every drop is logged. gap, c_R, c_B, d_lpick are never dropped (error)."""
    sub = Xall.iloc[idx][cols]
    keep, drops, seen = [], [], {}
    for c in cols:
        v = sub[c].to_numpy(float)
        if np.isnan(v).any():
            raise ValueError(f"{tag}: NaN in column {c} on fitted rows")
        if np.all(v == v[0]):
            if c in PROTECTED:
                raise ValueError(f"{tag}: protected column {c} is constant")
            drops.append((c, "constant"))
            continue
        key = v.tobytes()
        dup = seen.get(key)
        if dup is not None and np.array_equal(sub[dup].to_numpy(float), v):
            if c in PROTECTED:
                raise ValueError(f"{tag}: protected column {c} duplicates {dup}")
            drops.append((c, f"duplicate of {dup}"))
            continue
        seen[key] = c
        keep.append(c)
    for c, why in drops:
        log(f"column hygiene [{tag}]: dropped {c} ({why})")
    return Design(sub[keep], idx, F, drops)


# ----------------------------------------------------------------------------------------------- GLM mirror
class ClusterIdx:
    def __init__(self, bid, rid, did):
        self.n = len(bid)
        self.G = []
        for g in (bid, rid, did):
            ng = int(g.max()) + 1
            self.G.append((sp.csr_matrix((np.ones(self.n), (np.arange(self.n), g)), shape=(self.n, ng)), ng))
        self.nb, self.nr = self.G[0][1], self.G[1][1]


def psd_clip(V: np.ndarray) -> tuple[np.ndarray, bool]:
    V = (V + V.T) / 2
    w, U = np.linalg.eigh(V)
    if w.min() >= 0:
        return V, False
    return (U * np.clip(w, 0, None)) @ U.T, True


def two_way_cov(clu: ClusterIdx, X: np.ndarray, score: np.ndarray, bread: np.ndarray) -> tuple[np.ndarray, bool]:
    """Cameron-Gelbach-Miller V_b + V_r - V_d with statsmodels' default small-sample factor
    g/(g-1) * (n-1)/(n-k) for each clustering; clipped to PSD if needed."""
    n, k = X.shape
    V = np.zeros((k, k))
    for i, (G, ng) in enumerate(clu.G):
        Sg = np.asarray(G.T @ score)
        meat = (Sg.T @ Sg) * (ng / (ng - 1.0)) * ((n - 1.0) / (n - k))
        V += meat if i < 2 else -meat
    return psd_clip(bread @ V @ bread)


def irls_logit(X, y, w=None, beta0=None, maxit=60, ridge=1e-9):
    n, k = X.shape
    w = np.ones(n) if w is None else w
    if beta0 is None:
        beta = np.zeros(k)
        beta[0] = logit(np.clip(np.average(y, weights=w), 1e-4, 1 - 1e-4))
    else:
        beta = beta0.copy()
    for _ in range(maxit):
        p = expit(X @ beta)
        W = w * p * (1 - p)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(k)
        step = np.linalg.solve(H, X.T @ (w * (y - p)))
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    return beta


def fast_logit_cluster(X, y, clu: ClusterIdx, beta0=None):
    """Numpy IRLS + two-way cluster covariance (permutation draws, checks; matches statsmodels GLM)."""
    beta = irls_logit(X, y, beta0=beta0)
    p = expit(X @ beta)
    W = p * (1 - p)
    bread = np.linalg.inv(X.T @ (X * W[:, None]) + 1e-9 * np.eye(X.shape[1]))
    V, _ = two_way_cov(clu, X, X * (y - p)[:, None], bread)
    return beta, V


class GLMOut:
    def __init__(self, names, beta, V, nb, nr, n, clipped=False, converged=True):
        self.names, self.beta, self.V, self.nb, self.nr, self.n = names, np.asarray(beta), np.asarray(V), nb, nr, n
        self.G = min(nb, nr)
        self.df = self.G - 1
        self.clipped, self.converged = clipped, converged

    def lin(self, c: np.ndarray) -> dict:
        c = np.asarray(c, float)
        est = float(c @ self.beta)
        se = float(np.sqrt(max(c @ self.V @ c, 0.0)))
        tq = stats.t.ppf(0.975, self.df)
        out = dict(est=est, se=se, df=self.df, n=self.n)
        out["ci_nom"] = (est - tq * se, est + tq * se)
        out["p_nom"] = float(2 * stats.t.sf(abs(est / se), self.df)) if se > 0 else float("nan")
        sk = KAPPA * se
        out["se_kappa"] = sk
        out["ci_kappa"] = (est - tq * sk, est + tq * sk)
        out["p_kappa"] = float(2 * stats.t.sf(abs(est / sk), self.df)) if sk > 0 else float("nan")
        return out

    def term(self, name: str) -> dict:
        c = np.zeros(len(self.names))
        c[self.names.index(name)] = 1.0
        return self.lin(c)

    def combo(self, coefs: dict) -> dict:
        c = np.zeros(len(self.names))
        for k_, v in coefs.items():
            c[self.names.index(k_)] = v
        return self.lin(c)


def glm_mirror(D: Design, y: np.ndarray, family: str = "binomial", weights: np.ndarray | None = None) -> GLMOut:
    """Section 5.6: statsmodels GLM (IRLS, maxiter 100); two-way cluster-robust covariance V_b + V_r - V_d with the
    default small-sample correction; negative eigenvalues clipped to 0 if V is not PSD."""
    import statsmodels.api as sm
    X = np.column_stack([np.ones(D.n), D.X])
    fam = sm.families.Binomial() if family == "binomial" else sm.families.Gaussian()
    kw = {} if weights is None else {"freq_weights": weights}
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        mod = sm.GLM(y, X, family=fam, **kw)
        res = mod.fit(maxiter=100)
        Vs = []
        for g in (D.bid, D.rid, D.did):
            r = mod.fit(maxiter=100, start_params=res.params, cov_type="cluster", cov_kwds={"groups": g})
            Vs.append(np.asarray(r.cov_params()))
    V, clipped = psd_clip(Vs[0] + Vs[1] - Vs[2])
    conv = bool(getattr(res, "converged", True)) and not any("onverge" in str(w.message) for w in wl)
    return GLMOut(["const"] + D.names, res.params, V, D.nb, D.nr, D.n, clipped, conv)


# ----------------------------------------------------------------------------------------------- Bayesian engine
_COMPILED: dict = {}


class BSpec:
    """Specification of one Bayesian model: fixed-effect matrix, random-effect groups, family, priors."""

    def __init__(self, X, names, groups: dict, family="binomial", prior_sd: dict | None = None):
        self.X, self.names, self.groups, self.family = np.ascontiguousarray(X, float), list(names), groups, family
        sds = np.ones(len(names))
        for i, nme in enumerate(names):
            if nme in SPLINE_COLS:
                sds[i] = 2.5
        for nme, v in (prior_sd or {}).items():
            sds[self.names.index(nme)] = v
        self.sds = sds

    def key(self):
        h = hashlib.md5(self.X.tobytes())
        for nme, (idx, ng) in self.groups.items():
            h.update(nme.encode())
            h.update(np.asarray(idx).tobytes())
        h.update(self.sds.tobytes())
        h.update(self.family.encode())
        return h.hexdigest()


def get_compiled(spec: BSpec, y0: np.ndarray):
    key = spec.key()
    if key in _COMPILED:
        return _COMPILED[key]
    import nutpie
    import pymc as pm
    import pytensor.tensor as pt
    t = time.time()
    gauss = spec.family == "gaussian"
    with pm.Model() as m:
        Xd = pm.Data("X", spec.X)
        yd = pm.Data("y", y0.astype(float))
        alpha = pm.Normal("alpha", 0.0 if gauss else -2.25, 1.0 if gauss else 2.0)
        beta = pm.Normal("beta", 0.0, spec.sds, shape=int(spec.X.shape[1]))
        eta = alpha + pt.dot(Xd, beta)
        for nme, (idx, ng) in spec.groups.items():
            sig = pm.HalfNormal(f"sigma_{nme}", 1.0)
            z = pm.Normal(f"z_{nme}", 0.0, 1.0, shape=int(ng))
            eta = eta + sig * z[np.asarray(idx)]
        if gauss:
            seps = pm.HalfNormal("sigma_eps", 1.0)
            pm.Normal("obs", mu=eta, sigma=seps, observed=yd)
        else:
            pm.Bernoulli("obs", logit_p=eta, observed=yd)
        comp = nutpie.compile_pymc_model(m, backend="numba")
    log(f"compiled Bayesian model ({'gauss' if gauss else 'logit'}, n={spec.X.shape[0]}, k={spec.X.shape[1]}, "
        f"groups={list(spec.groups)}) in {time.time() - t:.0f}s")
    _COMPILED[key] = comp
    return comp


class Fit:
    """Posterior draws (flattened chains x draws) and diagnostics of one Bayesian fit."""

    def __init__(self, names, post, diag, tr, label, seconds, groups):
        self.names, self.post, self.diag, self.tr, self.label, self.seconds = names, post, diag, tr, label, seconds
        self.groups = groups  # {name: idx}
        self.B = post["beta"]
        self.D = self.B.shape[0]

    def draws(self, name: str) -> np.ndarray:
        return self.B[:, self.names.index(name)]

    def sel(self, thin):
        return np.arange(self.D) if thin is None else np.linspace(0, self.D - 1, thin).astype(int)

    def eta(self, X: np.ndarray, groups: dict | None = None, thin: int | None = None) -> np.ndarray:
        """n x D linear predictor incl. fitted random intercepts (groups: {name: row->level index})."""
        s = self.sel(thin)
        e = X @ self.B[s].T + self.post["alpha"][s][None, :]
        for nme, idx in (groups if groups is not None else self.groups).items():
            e = e + self.post[f"sigma_{nme}"][s][None, :] * self.post[f"z_{nme}"][s].T[np.asarray(idx)]
        return e


def _sample(comp, y, draws, tune, target_accept, seed):
    import nutpie
    c2 = comp.with_data(y=y.astype(float))
    cores = min(4, os.cpu_count() or 1)
    return nutpie.sample(c2, draws=draws, tune=tune, chains=4, cores=cores, seed=seed, target_accept=target_accept,
                         low_rank_modified_mass_matrix=True, progress_bar=False)


def _extract(tr):
    ds = tr["posterior"].to_dataset()
    post = {}
    for v in ds.data_vars:
        a = ds[v].values
        post[v] = a.reshape((a.shape[0] * a.shape[1],) + a.shape[2:])
    return post


def _diagnose(tr, names, key_terms):
    import arviz as az
    ds = tr["posterior"].to_dataset()
    vn = ["alpha", "beta"] + [v for v in ds.data_vars if v.startswith("sigma_")]
    rh = az.rhat(tr, var_names=vn).to_dataset()
    out = {"rhat_max": float(max(np.nanmax(rh[v].values) for v in rh.data_vars))}
    eb = az.ess(tr, var_names=["beta"], method="bulk").to_dataset()["beta"].values
    et = az.ess(tr, var_names=["beta"], method="tail").to_dataset()["beta"].values
    ii = [names.index(k) for k in key_terms]
    out["ess_bulk_min"] = float(np.min(eb[ii]))
    out["ess_tail_min"] = float(np.min(et[ii]))
    div = tr["sample_stats"].to_dataset()["diverging"].values
    out["divergences"] = int(div.sum())
    out["div_pct"] = float(100.0 * div.sum() / div.size)
    out["ok"] = bool(out["rhat_max"] <= 1.01 and out["ess_bulk_min"] >= 400 and out["ess_tail_min"] >= 400
                     and out["div_pct"] <= 0.1)
    return out


def fit_bayes(spec: BSpec, y: np.ndarray, label: str, light: bool, key_terms: list[str], escalate: bool = True) -> Fit:
    """Section 5.5. Full: 2000/2000, target_accept 0.90, seed 2027. Light: 1000/1000. Escalation once: 4000/4000,
    target_accept 0.97, seed 2028. All fits: 4 chains, nutpie numba backend."""
    comp = get_compiled(spec, y)
    t = time.time()
    draws = tune = 1000 if light else 2000
    tr = _sample(comp, y, draws, tune, 0.90, SEED)
    diag = _diagnose(tr, spec.names, key_terms)
    diag["escalated"] = False
    diag["setting"] = "light" if light else "full"
    if not diag["ok"] and escalate:
        log(f"  [{label}] convergence failed (rhat {diag['rhat_max']:.3f}, ess {diag['ess_bulk_min']:.0f}/"
            f"{diag['ess_tail_min']:.0f}, div {diag['div_pct']:.2f}%): escalating")
        first = dict(diag)
        tr = _sample(comp, y, 4000, 4000, 0.97, SEED_ESC)
        diag = _diagnose(tr, spec.names, key_terms)
        diag.update(escalated=True, first=first, setting="escalated")
    post = _extract(tr)
    secs = time.time() - t
    diag["seconds"] = secs
    log(f"  [{label}] {diag['setting']} fit {secs:.0f}s rhat {diag['rhat_max']:.4f} ess {diag['ess_bulk_min']:.0f}/"
        f"{diag['ess_tail_min']:.0f} div {diag['divergences']} ok={diag['ok']}")
    return Fit(spec.names, post, diag, tr, label, secs, {k: v[0] for k, v in spec.groups.items()})


def save_idata(fit: Fit, path: Path) -> str:
    """Section 13.3 asks for .nc via to_netcdf; falls back to a zarr store if no netCDF backend is installed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fit.tr.to_netcdf(path)
        return str(path)
    except Exception as e:
        zp = path.with_suffix(".zarr")
        try:
            fit.tr.to_zarr(zp, mode="w")
            return f"{zp} (netCDF backend unavailable: {type(e).__name__})"
        except Exception as e2:
            return f"not saved ({type(e2).__name__})"


# ----------------------------------------------------------------------------------------------- posterior post-processing
def ame_draws(fit: Fit, D: Design, term: str, thin: int = 1000) -> np.ndarray:
    """Per posterior draw: mean over rows of expit(eta + beta_term) - expit(eta), 1,000 evenly thinned draws."""
    eta = fit.eta(D.X, thin=thin)
    b = fit.B[fit.sel(thin), fit.names.index(term)]
    return (expit(eta + b[None, :]) - expit(eta)).mean(axis=0)


def base_rate_pp(beta_draws: np.ndarray) -> np.ndarray:
    return (expit(logit(BASE_RATE) + beta_draws) - BASE_RATE) * 100.0


def pick_equiv(beta_gap: np.ndarray, beta_lpd: np.ndarray, sd_lpd: float) -> dict:
    k = beta_gap / (-beta_lpd)
    delta = k * sd_lpd
    return dict(k=k, delta=delta, ratio=np.exp(delta), slots=64.0 - 64.0 / np.exp(delta))


def qsum(x: np.ndarray) -> tuple[float, float, float]:
    return float(np.median(x)), float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))


def dsum(x: np.ndarray) -> dict:
    return dict(mean=float(np.mean(x)), median=float(np.median(x)), lo=float(np.quantile(x, 0.025)),
                hi=float(np.quantile(x, 0.975)), p_pos=float(np.mean(x > 0)), p_neg=float(np.mean(x < 0)))


# ----------------------------------------------------------------------------------------------- formatting
def f3(x, d=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "not reported"
    return f"{x:.{d}f}"


def fci(m, lo, hi, d=3) -> str:
    return f"{f3(m, d)} [{f3(lo, d)}, {f3(hi, d)}]"


def bay_str(s: dict, d=3) -> str:
    return fci(s["median"], s["lo"], s["hi"], d)


def glm_str(g: dict, d=3) -> str:
    return (f"{f3(g['est'], d)} [{f3(g['ci_kappa'][0], d)}, {f3(g['ci_kappa'][1], d)}] "
            f"{{{f3(g['ci_nom'][0], d)}, {f3(g['ci_nom'][1], d)}}}")


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r.values) + " |")
    return "\n".join(out)


# ----------------------------------------------------------------------------------------------- simulation generator
def simulate_outcomes(F: pd.DataFrame, Vreg: Version, beta_gap: float, sim_seed: int) -> pd.DataFrame:
    """Section 13.3 generator: logit P = a - 0.20 d_lpick + 0.58 std(dropback) + beta_gap gap + u_b + v_q, u,v ~ N(0, 0.35^2)
    crossed, a solved so that the mean rate on P is 0.0952. Gap effect on engaged_primary pairs only (placebo rows
    carry no gap effect). Uses default_rng(sim_seed). Also returns a Gaussian outcome (S3a) and an independent draw
    of the same logistic model (S3b, as a rusher time_to_pressure column)."""
    from scipy.optimize import brentq
    rng = np.random.default_rng(sim_seed)
    n = len(F)
    pick = np.nan_to_num(Vreg.X["d_lpick"].to_numpy(float))
    drop = Vreg.X["db1"].to_numpy(float)
    gap = np.nan_to_num(Vreg.X["gap"].to_numpy(float)) * F.eng.to_numpy(float)
    bl = F.blocker_nfl_id.to_numpy()
    ru = F.rusher_nfl_id.to_numpy()
    bu, bi = np.unique(bl, return_inverse=True)
    ru_u, ri = np.unique(ru, return_inverse=True)
    lp0 = GEN_B_PICK * pick + GEN_B_DROP * drop + beta_gap * gap
    P = np.flatnonzero(Vreg.prim)
    LP = []
    for _ in range(300):
        ub, ur = rng.normal(0, GEN_RE_SD, len(bu)), rng.normal(0, GEN_RE_SD, len(ru_u))
        LP.append(lp0[P] + ub[bi[P]] + ur[ri[P]])
    LP = np.array(LP)
    a = brentq(lambda t: expit(LP + t).mean() - BASE_RATE, -10, 5)
    ub, ur = rng.normal(0, GEN_RE_SD, len(bu)), rng.normal(0, GEN_RE_SD, len(ru_u))
    lp = a + lp0 + ub[bi] + ur[ri]
    y = (rng.random(n) < expit(lp)).astype(float)
    y2 = (rng.random(n) < expit(lp)).astype(float)
    ub3, ur3 = rng.normal(0, 0.2, len(bu)), rng.normal(0, 0.2, len(ru_u))
    z3 = beta_gap * gap + ub3[bi] + ur3[ri] + rng.normal(0, 0.9, n)
    peak = np.clip(0.25 + 0.20 * z3, 0.0, 1.0)
    peak[rng.random(n) < PEAK_NULL_RATE_SIM] = np.nan
    out = F[KEYS].copy()
    out["pressure_allowed"] = y
    out["peak_pressure_probability_allowed"] = peak
    out["rusher_time_to_pressure"] = np.where(y2 > 0, 1.0, np.nan)
    out.attrs["intercept"] = float(a)
    return out


# ----------------------------------------------------------------------------------------------- k5 composites (SA13)
def build_k5_composites() -> pd.Series:
    """O3 and D1 recomputed with 5-frame smoothing via traits.evaluate_trait(tid, reps, cr, k=5); z within position x
    draft year as in build_composites; composite = that z (registered components, no re-gating)."""
    from bdb2027 import traits as T
    cr = T.load_combine_results()
    reps = {"mirror": T.load_reps(T.DRILLS["mirror"]), "rush": T.load_reps(T.DRILLS["rush"])}
    out = cr[cr.combine_position.isin(["OL", "DL"])][["nfl_id", "combine_position", "draft_year"]].set_index("nfl_id")
    comp = pd.Series(np.nan, index=out.index)
    for tid, side in (("O3", "OL"), ("D1", "DL")):
        res = T.evaluate_trait(tid, reps, cr, 5, pop=None)
        P = res["player"]
        df = out[out.combine_position == side][["draft_year"]].join(P[["value"]])
        z = T.z_within(df.assign(c=df["value"]), "c", ["draft_year"]) * T.TRAITS[tid].orient
        comp.loc[df.index] = z
    return comp


# ----------------------------------------------------------------------------------------------- PC1
def pc1_compute(tab: pd.DataFrame) -> dict:
    """V1/PC1: logit of pressure_allowed on const + z(rusher pick - blocker pick) + z(rusher weight - blocker weight)
    + dropback_duration (seconds); z over the supplied rows; SE clustered by blocker."""
    import statsmodels.api as sm
    dp = (tab.pick_R - tab.pick_B).astype(float)
    dw = (tab.w_R - tab.w_B).astype(float)
    X = pd.DataFrame({"const": 1.0, "z_dpick": (dp - dp.mean()) / dp.std(), "z_dwt": (dw - dw.mean()) / dw.std(),
                      "dropback_duration": tab.dropback.astype(float)})
    res = sm.Logit(tab.y.astype(int), X).fit(disp=0, cov_type="cluster",
                                             cov_kwds={"groups": pd.factorize(tab.blocker)[0]})
    return dict(n=int(len(tab)), events=int(tab.y.sum()), pick=float(res.params["z_dpick"]),
                pick_se=float(res.bse["z_dpick"]), wt=float(res.params["z_dwt"]), wt_se=float(res.bse["z_dwt"]),
                drop=float(res.params["dropback_duration"]), drop_se=float(res.bse["dropback_duration"]))


def pc1_status(r: dict) -> bool:
    return bool(r["events"] == 787 and abs(r["pick"] - (-0.204)) <= 0.003 and abs(r["drop"] - 0.577) <= 0.003)


# ----------------------------------------------------------------------------------------------- verdicts
def categorize(lo: float, hi: float) -> str:
    if lo > 0:
        return "Supported"
    if hi < 0:
        return "Opposite"
    return "Inconclusive"


# ----------------------------------------------------------------------------------------------- analysis object
class ModelRec:
    def __init__(self, name):
        self.name = name
        self.D = None
        self.y = None
        self.glm = None
        self.bayes: Fit | None = None
        self.meta = {}
        self.fallback = False
        self.not_converged = False


class AnalysisBase:
    def __init__(self, mode, sim_beta=0.0, sim_seed=1, light=False, out_root: Path | None = None, man=None,
                 guard=None, save_idata_files=True):
        self.mode, self.sim_beta, self.sim_seed, self.light_all = mode, sim_beta, sim_seed, light
        self.out_root = out_root
        self.rep_root = out_root
        self.table_root = None
        self.perm_n = 2000
        self.escalate = True
        self.man = man if man is not None else parse_manifest(PREREG_PATH.read_text(encoding="utf-8"))
        self.guard = guard
        self.save_idata_files = save_idata_files and out_root is not None
        self.models: dict[str, ModelRec] = {}
        self.R: dict = {"mode": mode}
        self.tabs: dict[str, pd.DataFrame] = {}
        self.status = "RUNNING"
        self.t_start = time.time()
        self.mde_reg = self.man.get("MDE_REGISTERED_LOGODDS") or 0.247
        self.mde_A = self.man.get("MDE_SENSA_LOGODDS") or 0.234
        act, txt = contingency_from_manifest(self.man)
        self.contingency_text = txt
        self.contingency_defined = act is not None
        self.contingency_active = bool(act) if act is not None else False   # simulate mode: manifest still unfilled
        self.dropped_cols: dict[str, list] = {}
        self.timings: dict[str, float] = {}

    # ---------------------------------------------------------------- io
    def dump(self):
        if self.rep_root is None:
            return
        self.rep_root.mkdir(parents=True, exist_ok=True)

        def conv(o):
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                return None if not np.isfinite(o) else float(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            if isinstance(o, (pd.DataFrame,)):
                return o.to_dict(orient="records")
            if isinstance(o, (Path,)):
                return str(o)
            return str(o)
        (self.rep_root / "confirmatory_results.json").write_text(json.dumps(self.R, default=conv, indent=1),
                                                                 encoding="utf-8")

    def table(self, name: str, df: pd.DataFrame):
        self.tabs[name] = df
        self.R.setdefault("tables", {})[name] = df.to_dict(orient="records")
        troot = self.table_root if self.table_root is not None else (self.rep_root / "tables" if self.rep_root is not None else None)
        if troot is not None:
            troot.mkdir(parents=True, exist_ok=True)
            df.to_csv(troot / f"{name}.csv", index=False)

    def flush_log(self):
        if self.out_root is not None:
            self.out_root.mkdir(parents=True, exist_ok=True)
            (self.out_root / "run_log.txt").write_text("\n".join(LOGBUF), encoding="utf-8")

    # ---------------------------------------------------------------- build
    def prepare(self, with_k5=True):
        t = time.time()
        self.inp = load_inputs()
        F = build_frame(self.inp)
        self.F = F
        E0, eng = F.E0.to_numpy(), F.eng.to_numpy()

        def mk(name, cb, cr, need_b=True):
            cB = F[cb].to_numpy(float) if cb else np.full(len(F), np.nan)
            cR = F[cr].to_numpy(float)
            prim = E0 & eng & np.isfinite(cR) & (np.isfinite(cB) if need_b else True)
            return Version(name, F, cB, cR, prim)
        self.V = {"reg": mk("reg", "composite_B", "composite_R"),
                  "A": mk("A", "composite_sensA_B", "composite_sensA_R"),
                  "B": mk("B", "composite_sensB_B", "composite_sensB_R"),
                  "DL": mk("DL", None, "composite_R", False)}
        if with_k5:
            k5 = build_k5_composites()
            cB = F.blocker_nfl_id.map(k5).to_numpy(float)
            cR = F.rusher_nfl_id.map(k5).to_numpy(float)
            prim = E0 & eng & np.isfinite(cR) & np.isfinite(cB)
            self.V["k5"] = Version("k5", F, cB, cR, prim)
        self.S = build_sets(F, self.V)
        if with_k5:
            self.S["SA13"] = self.V["k5"].prim.copy()
        self.timings["prepare"] = time.time() - t
        log(f"prepare: frame {F.shape}, versions {list(self.V)}, sets {len(self.S)} in {time.time() - t:.1f}s")

    def set_label(self, k):
        return {"R": "R (E0 & engaged_primary)"}.get(k, k)

    def v0_structural(self) -> tuple[pd.DataFrame, bool, list]:
        """Recompute the section 2.3 counts (outcome-free) and compare with the spec."""
        F = self.F
        rows, bad = [], []
        order = ["P", "PL", "ALL", "P-A", "PL-A", "P-B", "P-DL", "SA1", "SA2", "SA3", "SA4", "SA5", "SA6", "SA7", "SA9",
                 "SA11", "SA13", "SA15", "R"]
        for k in order:
            if k not in self.S:
                continue
            c = set_counts(F, self.S[k])
            exp = EXPECTED.get(k, {})
            for fld in ("reps", "blockers", "rushers", "dyads", "reg"):
                if fld in exp and c[fld] != exp[fld]:
                    bad.append(f"{k}.{fld}: got {c[fld]} expected {exp[fld]}")
            if "seasons" in exp and (c["s2023"], c["s2024"], c["s2025"]) != exp["seasons"]:
                bad.append(f"{k}.seasons: got {(c['s2023'], c['s2024'], c['s2025'])} expected {exp['seasons']}")
            rows.append((k, c))
        p = F[self.S["P"]]
        facts = {"E0 pairs": int(F.E0.sum()), "E0 engaged": int((F.E0 & F.eng).sum()),
                 "blocker G": int((p.blocker_lined_up_position == "G").sum()),
                 "blocker T": int((p.blocker_lined_up_position == "T").sum()),
                 "blocker C": int((p.blocker_lined_up_position == "C").sum()),
                 "rusher EDGE": int((p.rusher_lined_up_position == "EDGE").sum()),
                 "rusher INTERIOR_LINE": int((p.rusher_lined_up_position == "INTERIOR_LINE").sum()),
                 "nfl DT": int((p.rusher_nfl_position == "DT").sum()), "nfl DE": int((p.rusher_nfl_position == "DE").sum()),
                 "nfl OLB": int((p.rusher_nfl_position == "OLB").sum()), "nfl NT": int((p.rusher_nfl_position == "NT").sum()),
                 "double_team": int(p.double_team.sum()), "pre0": int((p.pass_rushers_encountered == 0).sum()),
                 "pre1": int((p.pass_rushers_encountered == 1).sum()), "pre2": int((p.pass_rushers_encountered == 2).sum()),
                 "down1": int((p.down == 1).sum()), "down2": int((p.down == 2).sum()), "down3": int((p.down == 3).sum()),
                 "down4": int((p.down == 4).sum())}
        for k, v in EXPECTED_FACTS.items():
            if facts[k] != v:
                bad.append(f"fact {k}: got {facts[k]} expected {v}")
        if not (p.play_nullified_by_penalty == "N").all():
            bad.append("play_nullified_by_penalty not all N in P")
        self.R["facts"] = facts
        gsd = self.V["reg"].gap_sd
        if abs(gsd - 1.253) > 0.0006:
            bad.append(f"gap SD {gsd:.4f} != 1.253")
        self.R["constants"] = dict(gap_sd=gsd, sd_lpd=self.V["reg"].sd_lpd,
                                   raw_pick_diff_sd=float((F.draft_overall_pick_R - F.draft_overall_pick_B)[self.S["P"]].std()),
                                   gap_sd_A=self.V["A"].gap_sd, gap_sd_B=self.V["B"].gap_sd,
                                   corr_composites_P=float(np.corrcoef(p.composite_R, p.composite_B)[0, 1]),
                                   knots=self.V["reg"].knots.tolist(), dropback_mean=float(p.dropback_duration.mean()),
                                   dropback_sd=float(p.dropback_duration.std()))
        return rows, bad

    def r1_table(self, rows) -> pd.DataFrame:
        out = []
        for k, c in rows:
            out.append({"Set": self.set_label(k), "Reps": c["reps"], "Pressures": "", "Rate": "",
                        "Blockers": c["blockers"], "Rushers": c["rushers"], "Dyads": c["dyads"],
                        "2023 / 2024 / 2025": f"{c['s2023']} / {c['s2024']} / {c['s2025']}", "REG": c["reg"],
                        "Rows dropped (reason)": (f"{c['ctx_dropped']} (null context covariate)" if c["ctx_dropped"] else "0")})
        return pd.DataFrame(out)

    # ---------------------------------------------------------------- outcomes
    def attach_outcomes(self, Y: pd.DataFrame):
        """1:1 inner join on the four keys; asserts no rows are lost or duplicated."""
        F = self.F
        if Y.duplicated(KEYS).any():
            raise AssertionError("outcome keys not unique")
        m = F[KEYS].merge(Y, on=KEYS, how="left", validate="1:1", indicator=True)
        if len(m) != len(F) or (m["_merge"] != "both").any() or len(Y) != len(F):
            raise AssertionError(f"outcome join not 1:1: pairs {len(F)}, outcomes {len(Y)}, matched "
                                 f"{(m['_merge'] == 'both').sum()}")
        F["y_press"] = m["pressure_allowed"].astype(float).to_numpy()
        F["y_peak"] = m["peak_pressure_probability_allowed"].astype(float).to_numpy()
        F["y_rp"] = m["rusher_time_to_pressure"].notna().to_numpy().astype(float)
        F["y_eng"] = F.eng.to_numpy().astype(float)

    def load_outcomes(self):
        if self.mode == "simulate":
            Y = simulate_outcomes(self.F, self.V["reg"], self.sim_beta, self.sim_seed)
            self.sim_intercept = Y.attrs.get("intercept")
        else:
            Y = load_sealed_outcomes()
        self.attach_outcomes(Y)

    def v0_outcomes(self) -> list:
        bad = []
        P = self.S["P"]
        if self.F.y_press[P].isna().any():
            bad.append(f"{int(self.F.y_press[P].isna().sum())} null pressure_allowed on P")
        return bad

    # ---------------------------------------------------------------- PC1
    def pc1(self) -> dict:
        F = self.F
        m = F.eng.to_numpy()
        d = F[m]
        tab = pd.DataFrame({"pick_R": d.draft_overall_pick_R, "pick_B": d.draft_overall_pick_B, "w_R": d.combine_weight_R,
                            "w_B": d.combine_weight_B, "dropback": d.dropback_duration, "blocker": d.blocker_nfl_id,
                            "y": d.y_press})
        tab = tab.dropna()
        r = pc1_compute(tab)
        r["n_pairs"] = int(m.sum())
        r["pass"] = pc1_status(r)
        return r

    # ---------------------------------------------------------------- model fitting
    def y_of(self, yk: str) -> np.ndarray:
        return {"press": self.F.y_press, "peak": self.F.y_peak, "rp": self.F.y_rp, "eng": self.F.y_eng}[yk].to_numpy(float)

    def fit_model(self, name, ver, setname, cols, *, family="binomial", yk="press", key=("gap",), groups=("B", "R"),
                  light=False, bayes=True, mask=None, Xover=None, prior_sd=None, weights=None, glm=True,
                  tag=None) -> ModelRec:
        t0 = time.time()
        V = self.V[ver]
        Xall = V.X if Xover is None else Xover
        base = self.S[setname] if mask is None else mask
        yall = self.y_of(yk)
        n0 = int(base.sum())
        ok = base & self.F.ctx_ok.to_numpy()
        n_ctx = n0 - int(ok.sum())
        ok2 = ok & np.isfinite(yall)
        n_y = int(ok.sum()) - int(ok2.sum())
        fin = np.isfinite(Xall[cols].to_numpy(float)).all(axis=1)
        ok3 = ok2 & fin
        n_x = int(ok2.sum()) - int(ok3.sum())
        idx = np.flatnonzero(ok3)
        rec = ModelRec(name)
        rec.D = make_design(Xall, idx, cols, self.F, tag=name)
        self.dropped_cols[name] = rec.D.drops
        y = yall[idx]
        meta = dict(n_set=n0, dropped_ctx=n_ctx, dropped_y_null=n_y, dropped_x_null=n_x, n=len(idx), ver=ver,
                    set=setname, family=family, outcome=yk)
        if family == "gaussian":
            meta["ybar"], meta["ysd"] = float(y.mean()), float(y.std(ddof=1))
            y = (y - meta["ybar"]) / meta["ysd"]
        rec.y, rec.meta = y, meta
        rec.meta["blockers"], rec.meta["rushers"] = int(rec.D.nb), int(rec.D.nr)
        if glm:
            rec.glm = glm_mirror(rec.D, y, family, weights)
        if bayes:
            gd = {}
            if "B" in groups:
                gd["B"] = (rec.D.bid, rec.D.nb)
            if "R" in groups:
                gd["R"] = (rec.D.rid, rec.D.nr)
            if "D" in groups:
                gd["D"] = (rec.D.did, rec.D.nd)
            spec = BSpec(rec.D.X, rec.D.names, gd, family, prior_sd)
            kt = [k for k in key if k in rec.D.names] or [rec.D.names[0]]
            use_light = light or self.light_all
            rec.bayes = fit_bayes(spec, y, tag or name, use_light, kt, escalate=self.escalate)
            rec.meta["light"] = use_light
            if not rec.bayes.diag["ok"]:
                if use_light:
                    rec.not_converged = True
                else:
                    rec.fallback = True
            if self.save_idata_files:
                rec.meta["idata_path"] = save_idata(rec.bayes, self.out_root / f"idata_{name}.nc")
        rec.meta["seconds"] = time.time() - t0
        self.timings[f"model:{name}"] = rec.meta["seconds"]
        return rec

    def model(self, name, **over) -> ModelRec:
        if name in self.models:
            return self.models[name]
        M1c = C_COLS + Q_COLS + ["gap"]
        defs = {
            "M0": dict(ver="reg", setname="P", cols=C_COLS + Q_SIZE + ["gap"]),
            "M1": dict(ver="reg", setname="P", cols=M1c),
            "M2": dict(ver="reg", setname="P", cols=C_COLS + Q_COLS + K_COLS + ["gap"], key=("gap", "d_lpick")),
            "M1-A": dict(ver="A", setname="P-A", cols=M1c),
            "M2-A": dict(ver="A", setname="P-A", cols=C_COLS + Q_COLS + K_COLS + ["gap"], key=("gap", "d_lpick")),
            "M1-S1": dict(ver="reg", setname="P", cols=C_COLS + Q_COLS + ["c_R", "c_B"], key=("c_R", "c_B")),
            "M1-S2": dict(ver="reg", setname="P", cols=C_COLS + Q_COLS + ["gap", "gap_edge"], key=("gap", "gap_edge")),
            "M1-S3a": dict(ver="reg", setname="P", cols=M1c, family="gaussian", yk="peak"),
            "M1-S3b": dict(ver="reg", setname="P", cols=M1c, yk="rp"),
            "M1-PL": dict(ver="reg", setname="PL", cols=M1c),
            "M2-PL": dict(ver="reg", setname="PL", cols=C_COLS + Q_COLS + K_COLS + ["gap"], key=("gap", "d_lpick")),
            "M1-S2s": dict(ver="reg", setname="P", cols=C_COLS + Q_COLS + ["c_R", "c_B", "c_R_edge", "c_B_edge"],
                           key=("c_R", "c_B", "c_R_edge", "c_B_edge"), light=True),
            "R": dict(ver="reg", setname="R", cols=C_COLS, key=("edge",), light=True),
            "S5a": dict(ver="reg", setname="P", cols=C_COLS + ["depth"], key=("depth",), groups=("B",), light=True),
            "S5b": dict(ver="reg", setname="P",
                        cols=C_COLS + ["depth", "c_R"] + [f"zR_{MSHORT[m]}" for m in MEAS] + ["f_dash_R", "f_shuttle_R", "f_cone_R"],
                        key=("depth", "c_R"), light=True),
        }
        d = dict(defs[name])
        d.update(over)
        log(f"fitting {name}")
        rec = self.fit_model(name, **d)
        self.models[name] = rec
        return rec

    # ---------------------------------------------------------------- gap statistics
    def decision(self, rec: ModelRec, term="gap") -> dict:
        s = dsum(rec.bayes.draws(term))
        lo, hi, basis = s["lo"], s["hi"], "bayes"
        if rec.fallback:
            g = rec.glm.term(term)
            lo, hi, basis = g["ci_kappa"][0], g["ci_kappa"][1], "glm_fallback"
        return dict(summary=s, lo=lo, hi=hi, basis=basis, category=categorize(lo, hi))

    def units(self, rec: ModelRec, ver: str, term="gap", pe_lpd=None, pe_sd=None) -> dict:
        """Section 6.2 units for a gap estimate (logit models)."""
        b = rec.bayes.draws(term)
        gsd = self.V[ver].gap_sd
        out = dict(logodds=dsum(b), per_z=dsum(b / gsd), p_lt_sesoi=float(np.mean(b < SESOI)))
        ame = ame_draws(rec.bayes, rec.D, term)
        out["ame_pp"] = dsum(ame * 100.0)
        lo, hi = out["ame_pp"]["lo"], out["ame_pp"]["hi"]
        out["reps_per_extra"] = (dict(median=100.0 / out["ame_pp"]["median"], lo=100.0 / hi, hi=100.0 / lo)
                                 if (lo > 0 or hi < 0) else None)
        out["base_rate_pp"] = dsum(base_rate_pp(b))
        out["pe"] = None
        if pe_lpd is not None:
            nmin = min(len(b), len(pe_lpd))
            pe = pick_equiv(b[:nmin], pe_lpd[:nmin], pe_sd)
            out["pe"] = {k: dsum(v) for k, v in pe.items()}
        return out


# ----------------------------------------------------------------------------------------------- steps 5-12
class AnalysisSteps(AnalysisBase):
    # ---------------------------------------------------------------- steps 5-7: primary, M2/M0, verdict
    def lpd_source(self, which: str):
        """Draft-pick unit (section 6.2 item 3): (beta_lpd draws, SD_lpd) or (None, None) if PC2 failed."""
        if not self.R.get("pc2", {}).get("pass"):
            return None, None
        if which == "reg":
            return self.models["M2"].bayes.draws("d_lpick"), self.V["reg"].sd_lpd
        return self.models["M2-A"].bayes.draws("d_lpick"), self.V["A"].sd_lpd

    def record_units(self, name: str, ver: str):
        rec = self.model(name)
        own = name.startswith("M2")
        if name == "M2-A":
            lpd, sd = self.lpd_source("A")
        else:
            lpd, sd = self.lpd_source("reg")
        if lpd is None and name in ("M2", "M2-A"):
            pass
        u = self.units(rec, ver, "gap", lpd, sd)
        dec = self.decision(rec, "gap")
        g = rec.glm.term("gap")
        self.R.setdefault("units", {})[name] = u
        self.R.setdefault("decision", {})[name] = dict(category=dec["category"], lo=dec["lo"], hi=dec["hi"], basis=dec["basis"])
        self.R.setdefault("glm_gap", {})[name] = g
        self.R.setdefault("conv", {})[name] = dict(rec.bayes.diag, fallback=rec.fallback, not_converged=rec.not_converged,
                                                   light=rec.meta.get("light"))
        return u

    def step_primary(self):
        t = time.time()
        log("step 5: M1 (Bayesian + GLM)")
        self.model("M1")
        self.R["meta_M1"] = self.models["M1"].meta
        log("step 6: M2 (PC2) and M0")
        m2 = self.model("M2")
        dec = self.decision(m2, "d_lpick")
        s = dsum(m2.bayes.draws("d_lpick"))
        self.R["pc2"] = dict(summary=s, interval_hi=dec["hi"], interval_lo=dec["lo"], **{"pass": bool(dec["hi"] < 0)})
        self.model("M0")
        for nm in ("M1", "M2", "M0"):
            self.record_units(nm, "reg")
        self.R["sigma"] = {nm: {k: dsum(self.models[nm].bayes.post[f"sigma_{k}"]) for k in ("B", "R")} for nm in ("M1", "M2", "M0")}
        self.timings["primary"] = time.time() - t
        log("step 7: provisional H1 verdict")
        self.provisional_verdict()
        self.dump()

    def provisional_verdict(self):
        d = self.R["decision"]["M1"]
        self.R["h1_provisional"] = dict(category=d["category"], basis=d["basis"], lo=d["lo"], hi=d["hi"])
        log(f"  H1 (Bayesian interval, before qualifiers/contingency): {d['category']} [{d['lo']:.3f}, {d['hi']:.3f}]")

    # ---------------------------------------------------------------- step 8: secondaries
    def sec_row(self, sid, model, estimand, expected, summ, glm, n, cat=""):
        return dict(ID=sid, Model=model, Estimand=estimand, Expected=expected, bayes=summ, glm=glm, n=n, Category=cat)

    def step_secondaries(self):
        t = time.time()
        rows = []
        # H2, M0 from the primary step
        self.model("M2")
        self.model("M0")
        for nm in ("M2", "M0"):
            if nm not in self.R.get("units", {}):
                self.record_units(nm, "reg")
        rows.append(self.sec_row("H2", "M2", "gap", "+", self.R["units"]["M2"]["logodds"], self.R["glm_gap"]["M2"],
                                 self.models["M2"].D.n, self.R["decision"]["M2"]["category"]))
        rows.append(self.sec_row("M0", "M0", "gap", "+", self.R["units"]["M0"]["logodds"], self.R["glm_gap"]["M0"],
                                 self.models["M0"].D.n))
        # S0
        for nm in ("M1-A", "M2-A"):
            self.model(nm)
        self.model("M2-A")
        self.record_units("M2-A", "A")
        self.record_units("M1-A", "A")
        rows.append(self.sec_row("S0", "M1-A", "gap", "+", self.R["units"]["M1-A"]["logodds"], self.R["glm_gap"]["M1-A"],
                                 self.models["M1-A"].D.n, self.R["decision"]["M1-A"]["category"]))
        rows.append(self.sec_row("S0", "M2-A", "gap", "+", self.R["units"]["M2-A"]["logodds"], self.R["glm_gap"]["M2-A"],
                                 self.models["M2-A"].D.n, self.R["decision"]["M2-A"]["category"]))
        # S1
        m = self.model("M1-S1")
        bR, bB = m.bayes.draws("c_R"), m.bayes.draws("c_B")
        rows.append(self.sec_row("S1", "M1-S1", "c_R", "+", dsum(bR), m.glm.term("c_R"), m.D.n))
        rows.append(self.sec_row("S1", "M1-S1", "c_B", "-", dsum(bB), m.glm.term("c_B"), m.D.n))
        rows.append(self.sec_row("S1", "M1-S1", "c_R + c_B", "none", dsum(bR + bB), m.glm.combo({"c_R": 1, "c_B": 1}), m.D.n))
        self.R["conv"]["M1-S1"] = dict(m.bayes.diag, fallback=m.fallback, not_converged=m.not_converged)
        # S2
        m = self.model("M1-S2")
        bi, bg = m.bayes.draws("gap_edge"), m.bayes.draws("gap")
        rows.append(self.sec_row("S2", "M1-S2", "gap x edge", "+", dsum(bi), m.glm.term("gap_edge"), m.D.n))
        rows.append(self.sec_row("S2", "M1-S2", "gap (interior)", ">=0", dsum(bg), m.glm.term("gap"), m.D.n))
        rows.append(self.sec_row("S2", "M1-S2", "gap (edge)", "+", dsum(bg + bi), m.glm.combo({"gap": 1, "gap_edge": 1}), m.D.n))
        self.R["conv"]["M1-S2"] = dict(m.bayes.diag, fallback=m.fallback, not_converged=m.not_converged)
        # S3a (percentage points of peak pressure probability per SD of gap)
        m = self.model("M1-S3a")
        sc = m.meta["ysd"] * 100.0
        b = m.bayes.draws("gap") * sc
        g = m.glm.term("gap")
        gs = dict(g)
        for key in ("est", "se", "se_kappa"):
            gs[key] = g[key] * sc
        for key in ("ci_nom", "ci_kappa"):
            gs[key] = (g[key][0] * sc, g[key][1] * sc)
        rows.append(self.sec_row("S3a", "M1-S3a", "gap, pp of peak pressure probability", "+", dsum(b), gs, m.D.n))
        self.R["s3a_meta"] = dict(m.meta, null_count=m.meta["dropped_y_null"])
        self.R["conv"]["M1-S3a"] = dict(m.bayes.diag, fallback=m.fallback, not_converged=m.not_converged)
        # S3b
        m = self.model("M1-S3b")
        rows.append(self.sec_row("S3b", "M1-S3b", "gap", "+", dsum(m.bayes.draws("gap")), m.glm.term("gap"), m.D.n))
        self.R["s3b_meta"] = dict(m.meta, events=int(m.y.sum()))
        self.R["conv"]["M1-S3b"] = dict(m.bayes.diag, fallback=m.fallback, not_converged=m.not_converged)
        # S5
        ma, mb = self.model("S5a"), self.model("S5b")
        ba, bb = ma.bayes.draws("depth"), mb.bayes.draws("depth")
        share = 1.0 - float(np.median(bb)) / float(np.median(ba))
        rows.append(self.sec_row("S5", "S5a", "beta_depth", "+", dsum(ba), ma.glm.term("depth"), ma.D.n))
        rows.append(self.sec_row("S5", "S5b", "beta_depth", "none", dsum(bb), mb.glm.term("depth"), mb.D.n))
        rows.append(self.sec_row("S5", "S5a/S5b", "share = 1 - med(S5b)/med(S5a)", "+", {"point": share}, None, ma.D.n))
        self.R["s5"] = dict(share=share, dropped_null_depth=ma.meta["dropped_x_null"])
        for nm in ("S5a", "S5b"):
            self.R["conv"][nm] = dict(self.models[nm].bayes.diag, not_converged=self.models[nm].not_converged)
        self.R["secondaries"] = rows
        self.timings["secondaries"] = time.time() - t
        self.dump()

    # ---------------------------------------------------------------- step 9: V5 permutation, V6 placebo, V7, V8
    def step_permutation(self, nperm=2000, rng_seed=SEED, save=True):
        t = time.time()
        m1 = self.model("M1")
        D = m1.D
        F = self.F
        V = self.V["reg"]
        g_obs = m1.glm.term("gap")
        t_obs = g_obs["est"] / g_obs["se"]
        idx = D.idx
        side_info = {}
        for s, ids, idc, cm in (("B", D.bl_ids, "blocker_nfl_id", "composite_B"), ("R", D.ru_ids, "rusher_nfl_id", "composite_R")):
            sub = F.iloc[idx].drop_duplicates(idc).set_index(idc).loc[ids]
            cols = [np.nan_to_num((sub[f"{m}_{s}"].to_numpy(float) - V.side[(m, s)][0]) / V.side[(m, s)][1]) for m in MEAS]
            cols += [sub["forty_" + s].isna().to_numpy(float), sub["short_shuttle_" + s].isna().to_numpy(float),
                     sub["three_cone_" + s].isna().to_numpy(float)]
            Z = np.column_stack([np.ones(len(sub))] + cols)
            keep = [0] + [j for j in range(1, Z.shape[1]) if np.ptp(Z[:, j]) > 0]
            Z = Z[:, keep]
            comp = sub[cm].to_numpy(float)
            coef = np.linalg.lstsq(Z, comp, rcond=None)[0]
            fit = Z @ coef
            res = comp - fit
            side_info[s] = dict(fit=fit, res=res, cls=sub["draft_year_" + s].to_numpy())
        clu = ClusterIdx(D.bid, D.rid, D.did)
        X = np.column_stack([np.ones(D.n), D.X])
        gi = D.names.index("gap") + 1
        beta0 = m1.glm.beta.copy()
        y = m1.y
        rng = np.random.default_rng(rng_seed)
        bs, ts = np.empty(nperm), np.empty(nperm)
        # sanity: the numpy engine reproduces the statsmodels mirror on the observed data
        b_chk, V_chk = fast_logit_cluster(X, y, clu)
        self.R["engine_check"] = dict(max_abs_beta_diff=float(np.abs(b_chk - m1.glm.beta).max()),
                                      se_gap_diff=float(abs(np.sqrt(V_chk[gi, gi]) - g_obs["se"])))
        for k in range(nperm):
            comp = {}
            for s in ("B", "R"):
                inf = side_info[s]
                e = inf["res"].copy()
                for c in np.unique(inf["cls"]):
                    mm = np.flatnonzero(inf["cls"] == c)
                    e[mm] = inf["res"][mm][rng.permutation(len(mm))]
                comp[s] = inf["fit"] + e
            gstar = (comp["R"][D.rid] - comp["B"][D.bid]) / GAP_SD_REGISTERED
            X[:, gi] = gstar
            b, Vm = fast_logit_cluster(X, y, clu, beta0=beta0)
            bs[k], ts[k] = b[gi], b[gi] / np.sqrt(Vm[gi, gi])
        p2 = (1 + np.sum(np.abs(ts) >= abs(t_obs))) / (nperm + 1)
        p1 = (1 + np.sum(ts >= t_obs)) / (nperm + 1)
        pc = (1 + np.sum(np.abs(bs) >= abs(g_obs["est"]))) / (nperm + 1)
        res = dict(nperm=nperm, beta_obs=g_obs["est"], t_obs=t_obs, p_two=p2, p_one=p1, p_coef=pc,
                   null_mean=float(bs.mean()), null_sd=float(bs.std(ddof=1)),
                   null_lo=float(np.quantile(bs, 0.025)), null_hi=float(np.quantile(bs, 0.975)),
                   tnull_mean=float(ts.mean()), tnull_sd=float(ts.std(ddof=1)), seconds=time.time() - t)
        if save and self.out_root is not None:
            pd.DataFrame({"k": np.arange(1, nperm + 1), "beta_star": bs, "t_star": ts}).to_csv(
                self.out_root / "permutation_null.csv", index=False)
        self.R["perm"] = res
        log(f"V5 permutation: t_obs {t_obs:.3f}, p two-sided {p2:.4f} ({nperm} perms, {res['seconds']:.0f}s)")
        return res

    def step_placebo(self):
        m1, m2 = self.model("M1"), self.model("M2")
        p1, p2 = self.model("M1-PL"), self.model("M2-PL")
        med = lambda r, t: float(np.median(r.bayes.draws(t)))
        res = dict(
            n_PL=p1.D.n, bayes_gap_PL=dsum(p1.bayes.draws("gap")), glm_gap_PL=p1.glm.term("gap"),
            ratio_gap=med(p1, "gap") / med(m1, "gap"),
            beta_lpd_PL=dsum(p2.bayes.draws("d_lpick")), ratio_pick=med(p2, "d_lpick") / med(m2, "d_lpick"),
            glm_lpd_PL=p2.glm.term("d_lpick"))
        for nm in ("M1-PL", "M2-PL"):
            r = self.models[nm]
            self.R.setdefault("conv", {})[nm] = dict(r.bayes.diag, fallback=r.fallback, not_converged=r.not_converged)
        self.R["placebo"] = res
        return res

    # ---- grouped CV (V7/V8)
    @staticmethod
    def _fit_pred(X, y, tr, te, cols):
        Xtr = X[tr][:, cols]
        keep = [j for j in range(Xtr.shape[1]) if np.ptp(Xtr[:, j]) > 0]
        A = np.column_stack([np.ones(tr.sum()), Xtr[:, keep]])
        beta = irls_logit(A, y[tr])
        B = np.column_stack([np.ones(te.sum()), X[te][:, cols][:, keep]])
        return np.clip(expit(B @ beta), 1e-6, 1 - 1e-6)

    def cv_setup(self):
        if hasattr(self, "_cv"):
            return self._cv
        allc = C_COLS + Q_COLS + K_COLS + ["gap", "s_comp"]
        idx = np.flatnonzero(self.S["P"] & self.F.ctx_ok.to_numpy() & np.isfinite(self.F.y_press.to_numpy()))
        D = make_design(self.V["reg"].X, idx, allc, self.F, tag="CV")
        nm = D.names
        have = lambda L: [c for c in L if c in nm]
        sets = {"I0": have(C_COLS),
                "I1": have(C_COLS + Q_SIZE + K_COLS)}
        sets["I2"] = sets["I1"] + have(Q_REST)
        sets["I3"] = sets["I1"] + have(["gap", "s_comp"])
        sets["I4"] = sets["I2"] + have(["gap", "s_comp"])
        cols = {k: [nm.index(c) for c in v] for k, v in sets.items()}
        self._cv = dict(D=D, y=self.F.y_press.to_numpy()[idx], cols=cols, names=sets, idx=idx)
        return self._cv

    def step_cv(self, reps=20, save=True):
        t = time.time()
        cv = self.cv_setup()
        D, y, cols = cv["D"], cv["y"], cv["cols"]
        X = D.X
        res = {k: {"ll": [], "brier": []} for k in cols}
        preds = []
        for r in range(reps):
            rng = np.random.default_rng(SEED + r)
            gb = np.empty(D.nb, int)
            gr = np.empty(D.nr, int)
            for arr, nn in ((gb, D.nb), (gr, D.nr)):
                perm = rng.permutation(nn)
                for gi_, part in enumerate(np.array_split(perm, 3)):
                    arr[part] = gi_
            rb, rr = gb[D.bid], gr[D.rid]
            P = {k: np.full(D.n, np.nan) for k in cols}
            for i in range(3):
                for j in range(3):
                    te = (rb == i) & (rr == j)
                    tr = (rb != i) & (rr != j)
                    if te.sum() == 0:
                        continue
                    for k, cc in cols.items():
                        P[k][te] = self._fit_pred(X, y, tr, te, cc)
            for k in cols:
                p = P[k]
                res[k]["ll"].append(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))))
                res[k]["brier"].append(float(np.mean((y - p) ** 2)))
                if save:
                    preds.append(pd.DataFrame({"rep": r, "set": k, "row": np.arange(D.n), "p": p}))
        if save and self.out_root is not None:
            pd.concat(preds).to_parquet(self.out_root / "cv_predictions.parquet", index=False)

        def delta(a, b):
            d = (np.array(res[a]["ll"]) - np.array(res[b]["ll"])) * 1000.0
            return dict(mean=float(d.mean()), lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975)),
                        share_neg=float(np.mean(d < 0)))
        out = dict(sets={k: dict(ll=float(np.mean(v["ll"])), brier=float(np.mean(v["brier"])), n_cols=len(cols[k]))
                         for k, v in res.items()},
                   d42=delta("I4", "I2"), d31=delta("I3", "I1"), d21=delta("I2", "I1"), reps=reps, n=int(D.n),
                   seconds=time.time() - t)
        self.R["cv"] = out
        log(f"V7 CV done in {out['seconds']:.0f}s: dLL(I4-I2) {out['d42']['mean']:.3f} millinats")
        return out

    def _ll(self, y, p):
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    def step_v8(self):
        cv = self.cv_setup()
        D, y, cols = cv["D"], cv["y"], cv["cols"]
        F = self.F
        idx = cv["idx"]
        X = D.X
        dyB, dyR = F.draft_year_B.to_numpy()[idx], F.draft_year_R.to_numpy()[idx]
        season = F.season.to_numpy()[idx]
        loco, loso = [], []
        for c in (2023, 2024, 2025):
            te = (dyB == c) | (dyR == c)
            tr = (dyB != c) & (dyR != c)
            p2 = self._fit_pred(X, y, tr, te, cols["I2"])
            p4 = self._fit_pred(X, y, tr, te, cols["I4"])
            l2, l4 = self._ll(y[te], p2), self._ll(y[te], p4)
            loco.append(dict(unit=f"class {c}", n_test=int(te.sum()), n_train=int(tr.sum()), LL_I2=l2, LL_I4=l4,
                             dLL_millinats=(l4 - l2) * 1000.0))
        season_cols = [D.names.index(c) for c in ("s2023", "s2024") if c in D.names]
        for s in (2023, 2024, 2025):
            te = season == s
            tr = season != s
            c2 = [j for j in cols["I2"] if j not in season_cols]
            c4 = [j for j in cols["I4"] if j not in season_cols]
            p2 = self._fit_pred(X, y, tr, te, c2)
            p4 = self._fit_pred(X, y, tr, te, c4)
            l2, l4 = self._ll(y[te], p2), self._ll(y[te], p4)
            loso.append(dict(unit=f"season {s}", n_test=int(te.sum()), n_train=int(tr.sum()), LL_I2=l2, LL_I4=l4,
                             dLL_millinats=(l4 - l2) * 1000.0))
        by = []
        M1c = [c for c in C_COLS + Q_COLS + ["gap"] if c not in ("s2023", "s2024")]
        for s in (2023, 2024, 2025):
            ii = np.flatnonzero(self.S["P"] & self.F.ctx_ok.to_numpy() & (F.season.to_numpy() == s))
            Ds = make_design(self.V["reg"].X, ii, M1c, F, tag=f"M1-season{s}")
            g = glm_mirror(Ds, self.F.y_press.to_numpy()[ii]).term("gap")
            by.append(dict(season=s, n=int(Ds.n), est=g["est"], ci_kappa=g["ci_kappa"], ci_nom=g["ci_nom"],
                           flag="imprecise (431 reps)" if s == 2023 else ""))
        self.R["v8"] = dict(loco=loco, loso=loso, by_season=by)

    # ---------------------------------------------------------------- step 10: sensitivities
    def step_sensitivities(self):
        t = time.time()
        F = self.F
        M1c = C_COLS + Q_COLS + ["gap"]
        m1 = self.model("M1")
        sens = {}

        def run(sid, desc, **kw):
            log(f"sensitivity {sid}")
            rec = self.fit_model(sid, light=True, key=kw.pop("key", ("gap",)), **kw)
            self.models[sid] = rec
            tgt = kw.get("target", "gap")
            return rec
        # SA1-SA4 (double_team recomputed under the variant)
        for sid, flag, desc in (("SA1", "engaged_d125", "1.25 yd / 4 frames"), ("SA2", "engaged_d200", "2.0 yd / 4 frames"),
                                ("SA3", "engaged_k3", "1.5 yd / 3 frames"), ("SA4", "engaged_k6", "1.5 yd / 6 frames")):
            Xo = self.V["reg"].X.copy()
            Xo["double_team"] = double_team_variant(F, flag)
            rec = self.fit_model(sid, "reg", sid, M1c, light=True, Xover=Xo)
            sens[sid] = (desc + " (double-team flag recomputed)", rec, "gap", None)
        specs = [("SA5", "REG only", dict(setname="SA5")), ("SA6", "Exclude double teams", dict(setname="SA6")),
                 ("SA7", "Rushers with NFL position DE/DT/NT", dict(setname="SA7")),
                 ("SA9", "One pair per (game, play, blocker), smallest min_dist", dict(setname="SA9")),
                 ("SA15", "Complete cases for the dash (both players have a forty)", dict(setname="SA15"))]
        for sid, desc, kw in specs:
            sens[sid] = (desc, self.fit_model(sid, "reg", kw["setname"], M1c, light=True), "gap", None)
        # SA8 dyad-equal weights, GLM only
        D1 = m1.D
        nd = np.bincount(D1.did)[D1.did].astype(float)
        N, Dn = D1.n, D1.nd
        w = (N / Dn) / nd
        rec8 = self.fit_model("SA8", "reg", "P", M1c, bayes=False, weights=w)
        sens["SA8"] = ("Dyad-equal weighting w = (N / D) / n_dyad (GLM only)", rec8, "gap", None)
        sens["SA10"] = ("Composite B", self.fit_model("SA10", "B", "P-B", M1c, light=True), "gap", None)
        sens["SA11"] = ("Composite A on the rows of P (common sample)", self.fit_model("SA11", "A", "SA11", M1c, light=True), "gap", None)
        sens["SA12"] = ("DL-only: rusher composite replaces gap",
                        self.fit_model("SA12", "DL", "P-DL", C_COLS + Q_COLS + ["c_R"], light=True, key=("c_R",)), "c_R", None)
        if "k5" in self.V:
            sens["SA13"] = ("5-frame smoothing composites (O3, D1 at k=5)", self.fit_model("SA13", "k5", "SA13", M1c, light=True), "gap", None)
        sens["SA14"] = ("No dropback spline",
                        self.fit_model("SA14", "reg", "P", [c for c in M1c if c not in SPLINE_COLS], light=True), "gap", None)
        sens["SA16"] = ("M2 plus s_lpick (pick asymmetry)",
                        self.fit_model("SA16", "reg", "P", C_COLS + Q_COLS + K_COLS + ["s_lpick", "gap"], light=True,
                                       key=("gap", "d_lpick")), "gap", "M2")
        sens["SA17"] = ("M1 plus dyad random intercept",
                        self.fit_model("SA17", "reg", "P", M1c, light=True, groups=("B", "R", "D"), glm=False), "gap", None)
        for sd in (0.5, 2.5):
            nm = f"SA18_{sd}"
            sens[nm] = (f"beta_gap prior Normal(0, {sd})",
                        self.fit_model(nm, "reg", "P", M1c, light=True, prior_sd={"gap": sd}, glm=False), "gap", None)
        for k, (d, r, tg, ref) in sens.items():
            self.models[k] = r
        self.sens_def = sens
        self.timings["sensitivities"] = time.time() - t
        self.dump()

    def discordance(self):
        """Section 9 rule, using posterior medians (GLM estimate for SA8)."""
        h1 = self.R["h1_final"]["category"] if "h1_final" in self.R else self.R["h1_provisional"]["category"]
        m1 = self.models["M1"]
        m1_med = float(np.median(m1.bayes.draws("gap")))
        m1_glm = m1.glm.term("gap")["est"]
        m2_med = float(np.median(self.models["M2"].bayes.draws("gap")))
        rows = []
        for sid, (desc, rec, tgt, ref) in self.sens_def.items():
            if sid.startswith("SA18_") or sid == "SA17" or sid == "SA8" or rec.bayes is not None:
                pass
            if rec.bayes is not None:
                d = dsum(rec.bayes.draws(tgt))
                est, lo, hi = d["median"], d["lo"], d["hi"]
                refv = m2_med if ref == "M2" else m1_med
            else:
                g = rec.glm.term(tgt)
                est, lo, hi = g["est"], g["ci_kappa"][0], g["ci_kappa"][1]
                refv = m1_glm
            if h1 in ("Supported", "Opposite"):
                disc = (np.sign(est) != np.sign(refv)) or (abs(est) < 0.5 * abs(refv))
            else:
                disc = lo > 0 or hi < 0
            rows.append(dict(id=sid, desc=desc, est=est, lo=lo, hi=hi, ref=refv, discordant=bool(disc), rec=rec))
        return rows

    # ---------------------------------------------------------------- step 11: selection
    def step_selection(self):
        t = time.time()
        F, inp = self.F, self.inp
        tr, base = inp["traits"], inp["base"]
        V = self.V["reg"]
        rng = np.random.default_rng(SEED)
        P = self.S["P"]
        inP_B, inP_R = set(F.blocker_nfl_id[P]), set(F.rusher_nfl_id[P])
        out = {"sc1": []}
        pops = {}
        for side, comb, inP in (("OL", "OL", inP_B), ("DL", "DL", inP_R)):
            ids = tr.index[(tr.combine_position == side) & tr.composite.notna()]
            pops[side] = (ids, inP)
            ins = np.array([i in inP for i in ids])
            for var, series in (("composite", tr.composite), ("log_pick", base.log_pick), ("ngs_athleticism_score", base.ngs_athleticism_score)):
                v = series.reindex(ids).to_numpy(float)
                a, b = v[ins], v[~ins]
                diff = float(np.nanmean(a) - np.nanmean(b))
                bs = []
                for _ in range(2000):
                    ra, rb = rng.choice(a, len(a)), rng.choice(b, len(b))
                    bs.append(np.nanmean(ra) - np.nanmean(rb))
                ks = stats.ks_2samp(a[np.isfinite(a)], b[np.isfinite(b)])
                out["sc1"].append(dict(side=side, var=var, n_in=int(ins.sum()), n_out=int((~ins).sum()), diff=diff,
                                       lo=float(np.quantile(bs, 0.025)), hi=float(np.quantile(bs, 0.975)), ks_p=float(ks.pvalue)))
        eng_bl = set(F.blocker_nfl_id[F.E0 & F.eng])
        excl = sorted(eng_bl - inP_B)
        a = base.loc[sorted(inP_B)]
        b = base.loc[excl]
        out["sc1_excluded"] = dict(
            n_excluded=len(excl), n_reps=int((F.E0 & F.eng & F.blocker_nfl_id.isin(excl)).sum()),
            log_pick=(float(b.log_pick.mean()), float(a.log_pick.mean())),
            ngs=(float(b.ngs_athleticism_score.mean()), float(a.ngs_athleticism_score.mean())),
            miss_forty=(float(b.forty.isna().mean() * 100), float(a.forty.isna().mean() * 100)))
        # SC2
        c2 = [c for c in C_COLS if c != "double_team"] + Q_COLS + ["gap"]
        rec2 = self.fit_model("SC2", "reg", "ALL", c2, yk="eng", bayes=False)
        g2 = rec2.glm.term("gap")
        out["sc2"] = dict(glm=g2, flagged=bool(g2["ci_kappa"][0] > 0 or g2["ci_kappa"][1] < 0), n=rec2.D.n)
        # SC3 (all pairs)
        Xo = V.X.copy()
        Xo["eng"] = F.eng.to_numpy().astype(float)
        Xo["gap_x_eng"] = np.nan_to_num(Xo["gap"].to_numpy()) * Xo["eng"]
        ra = self.fit_model("SC3a", "reg", "ALL", C_COLS + Q_COLS + ["eng", "gap"], bayes=False, Xover=Xo)
        rb = self.fit_model("SC3b", "reg", "ALL", C_COLS + Q_COLS + ["eng", "gap", "gap_x_eng"], bayes=False, Xover=Xo)
        out["sc3a"] = dict(gap=ra.glm.term("gap"), eng=ra.glm.term("eng"), n=ra.D.n)
        out["sc3b"] = dict(gap=rb.glm.term("gap"), eng=rb.glm.term("eng"), inter=rb.glm.term("gap_x_eng"), n=rb.D.n)
        # SC4 inverse-probability weights
        import statsmodels.api as sm
        wmap = {}
        for side, (ids, inP) in pops.items():
            d = base.loc[ids]
            yin = np.array([i in inP for i in ids]).astype(float)
            Z = pd.DataFrame({"const": 1.0, "log_pick": d.log_pick.to_numpy(float), "undrafted": d.undrafted.astype(float).to_numpy(),
                              "ngs": d.ngs_athleticism_score.to_numpy(float), "c2024": (d.draft_year == 2024).astype(float).to_numpy(),
                              "c2025": (d.draft_year == 2025).astype(float).to_numpy()}, index=ids)
            try:
                ph = sm.Logit(yin, Z).fit(disp=0, maxiter=200).predict(Z).to_numpy()
            except Exception:
                ph = np.full(len(ids), yin.mean())
            w = yin.mean() / np.clip(ph, 1e-6, None)
            inm = yin.astype(bool)
            lo_, hi_ = np.quantile(w[inm], [0.01, 0.99])
            w = np.clip(w, lo_, hi_)
            wmap.update({(side, i): wi for i, wi in zip(ids, w)})
        m1 = self.model("M1")
        wB = np.array([wmap[("OL", i)] for i in m1.D.bl_ids])[m1.D.bid]
        wR = np.array([wmap[("DL", i)] for i in m1.D.ru_ids])[m1.D.rid]
        wr = wB * wR
        wr = wr / wr.mean()
        rec4 = self.fit_model("SC4", "reg", "P", C_COLS + Q_COLS + ["gap"], bayes=False, weights=wr)
        out["sc4"] = dict(glm=rec4.glm.term("gap"), n=rec4.D.n, w_min=float(wr.min()), w_max=float(wr.max()))
        self.R["selection"] = out
        self.timings["selection"] = time.time() - t
        self.dump()

    # ---------------------------------------------------------------- step 12: ratings and surface
    def step_ratings(self):
        t = time.time()
        rec = self.model("R")
        post = rec.bayes.post
        D = rec.D
        F = self.F
        ub = post["sigma_B"][:, None] * post["z_B"]
        vq = post["sigma_R"][:, None] * post["z_R"]
        rows = []
        for side, ids, bid, draws, sgn in (("blocker", D.bl_ids, D.bid, ub, -1.0), ("rusher", D.ru_ids, D.rid, vq, 1.0)):
            cnt = np.bincount(bid, minlength=len(ids))
            for j, pid in enumerate(ids):
                x = sgn * draws[:, j]
                rows.append(dict(nfl_id=int(pid), side=side, reps=int(cnt[j]), rating_mean=float(x.mean()), rating_sd=float(x.std(ddof=1)),
                                 q05=float(np.quantile(x, 0.05)), q95=float(np.quantile(x, 0.95))))
        rat = pd.DataFrame(rows)
        if self.out_root is not None:
            rat.to_csv(self.out_root / "player_ratings.csv", index=False)
        self.R["ratings"] = rat.to_dict(orient="records")
        self.R["sigma"]["R"] = {k: dsum(post[f"sigma_{k}"]) for k in ("B", "R")}
        self.R["conv"]["R"] = dict(rec.bayes.diag, not_converged=rec.not_converged)
        self.tabs["ratings"] = rat
        # S2s surface
        rec = self.model("M1-S2s")
        D = rec.D
        V = self.V["reg"]
        grid = np.round(np.arange(-2.0, 2.0001, 0.25), 2)
        nd = 500
        sel = rec.bayes.sel(nd)
        B = rec.bayes.B[sel]
        al = rec.bayes.post["alpha"][sel]
        nm = D.names
        comp_cols = ["c_R", "c_B", "c_R_edge", "c_B_edge"]
        oth = [j for j, c in enumerate(nm) if c not in comp_cols]
        eta0 = D.X[:, oth] @ B[:, oth].T + al[None, :]
        bR, bB = B[:, nm.index("c_R")], B[:, nm.index("c_B")]
        bRe, bBe = B[:, nm.index("c_R_edge")], B[:, nm.index("c_B_edge")]
        muR, sdR = V.std["c_R"]
        muB, sdB = V.std["c_B"]
        edge = D.col("edge")
        recs = []
        for e in (0, 1):
            E = eta0[edge == e]
            for a in grid:
                a_s = (a - muR) / sdR
                for b in grid:
                    b_s = (b - muB) / sdB
                    delta = bR * a_s + bB * b_s + e * (bRe * a_s + bBe * b_s)
                    p = expit(E + delta[None, :]).mean(axis=0)
                    recs.append(dict(edge=e, c_R_z=a, c_B_z=b, median=float(np.median(p)), lo90=float(np.quantile(p, 0.05)),
                                     hi90=float(np.quantile(p, 0.95))))
        sf = pd.DataFrame(recs)
        if self.out_root is not None:
            sf.to_csv(self.out_root / "surface_S2s.csv", index=False)
        self.R["surface"] = dict(rows=len(sf), draws=nd, p_min=float(sf["median"].min()), p_max=float(sf["median"].max()))
        self.R["conv"]["M1-S2s"] = dict(rec.bayes.diag, not_converged=rec.not_converged)
        self.timings["ratings_surface"] = time.time() - t
        self.dump()


# ----------------------------------------------------------------------------------------------- steps 13: final outputs
class Analysis(AnalysisSteps):
    # ---------------------------------------------------------------- qualifiers and final label
    def finalize_verdict(self):
        dec = self.R["decision"]["M1"]
        cat_b = dec["category"]
        g = self.R["glm_gap"]["M1"]
        perm = self.R.get("perm")
        pl = self.R.get("placebo")
        sc = self.R.get("selection")
        applicable = cat_b in ("Supported", "Opposite")
        sign = 1 if cat_b == "Supported" else -1
        q = {}
        lo_k, hi_k = g["ci_kappa"]
        if applicable:
            ok1 = (lo_k > 0) if sign > 0 else (hi_k < 0)
            q["Q1"] = dict(status="pass" if ok1 else "fail", value=f"kappa-calibrated CI [{lo_k:.3f}, {hi_k:.3f}]")
        else:
            q["Q1"] = dict(status="n/a", value=f"kappa-calibrated CI [{lo_k:.3f}, {hi_k:.3f}] (verdict is not Supported/Opposite)")
        if perm is not None:
            q["Q2"] = dict(status="pass" if perm["p_two"] < 0.05 else "fail", value=f"p = {perm['p_two']:.4f}")
        else:
            q["Q2"] = dict(status="not run", value="")
        if pl is not None and applicable:
            q["Q3"] = dict(status="pass" if pl["ratio_gap"] <= 0.5 else "fail", value=f"ratio = {pl['ratio_gap']:.3f}")
        elif pl is not None:
            q["Q3"] = dict(status="n/a", value=f"ratio = {pl['ratio_gap']:.3f} (verdict is not Supported/Opposite)")
        else:
            q["Q3"] = dict(status="not run", value="")
        disc = []
        if hasattr(self, "sens_def"):
            self.R["h1_final"] = dict(category=cat_b)   # discordance rule uses the Bayesian category
            drows = self.discordance()
            disc = [r["id"] for r in drows if r["discordant"]]
            self.R["discordance"] = [{k: v for k, v in r.items() if k != "rec"} for r in drows]
            q["Q4"] = dict(status="pass" if not disc else "fail", value=("none" if not disc else "discordant: " + ", ".join(disc)))
        else:
            q["Q4"] = dict(status="not run", value="")
        if sc is not None:
            fl = sc["sc2"]["flagged"]
            if not fl:
                q["Q5"] = dict(status="pass", value="SC2 not flagged")
            else:
                same = np.sign(sc["sc3a"]["gap"]["est"]) == np.sign(self.R["units"]["M1"]["logodds"]["median"])
                q["Q5"] = dict(status="pass" if same else "fail",
                               value=f"SC2 flagged; SC3a gap {sc['sc3a']['gap']['est']:.3f} ({'same' if same else 'opposite'} sign as M1)")
        else:
            q["Q5"] = dict(status="not run", value="")
        # calibration contingency (section 6.3)
        cat, downgraded = cat_b, False
        if self.contingency_active and cat_b in ("Supported", "Opposite") and q["Q2"]["status"] != "pass":
            cat, downgraded = "Inconclusive", True
        if cat in ("Supported", "Opposite"):
            failing = [k for k in ("Q1", "Q2", "Q3") if q[k]["status"] == "fail"]
            label = f"{cat} (robust)" if not failing else f"{cat} (qualified: {', '.join(failing)})"
        else:
            label = "Inconclusive"
            if downgraded:
                label += " (calibration contingency ACTIVE: Bayesian interval excluded 0 but Q2 failed)"
        named = [f"{k} failed ({q[k]['value']})" for k in ("Q4", "Q5") if q[k]["status"] == "fail"]
        if named:
            label += "; " + "; ".join(named)
        self.R["h1_final"] = dict(category=cat, bayes_category=cat_b, downgraded=downgraded, label=label, q=q,
                                  contingency_active=self.contingency_active, discordant=disc,
                                  contingency_text=self.contingency_text, basis=dec["basis"])
        return self.R["h1_final"]

    def verdict_sentence(self) -> str:
        h = self.R["h1_final"]
        u = self.R["units"]["M1"]
        m1 = self.models["M1"]
        dec = self.R["decision"]["M1"]
        n = m1.D.n
        nB, nR = m1.D.nb, m1.D.nr
        if dec["basis"] == "glm_fallback":
            g = self.R["glm_gap"]["M1"]
            beta, lo, hi = g["est"], g["ci_kappa"][0], g["ci_kappa"][1]
        else:
            beta, lo, hi = u["logodds"]["median"], u["logodds"]["lo"], u["logodds"]["hi"]
        pe = u["pe"]
        kclause = f", equivalent to {pe['k']['median']:.2f} SDs of draft-pick difference" if pe else ""
        ame = u["ame_pp"]["median"]
        tail = ("beyond both players' size, stopwatch times and NGS athleticism score")
        if h["category"] == "Supported":
            s = (f"On {n} engaged NFL pass-protection reps ({nB} blockers, {nR} rushers), each 1-SD increase in the "
                 f"Combine-tracked athletic gap (rusher minus blocker) raised the odds of a pressure by {beta:.3f} log-odds "
                 f"[{lo:.3f}, {hi:.3f}], about {ame:.2f} percentage points per rep{kclause}, {tail}. Label: {h['label']}.")
        elif h["category"] == "Opposite":
            s = (f"On {n} engaged NFL pass-protection reps ({nB} blockers, {nR} rushers), the athletic gap (rusher minus "
                 f"blocker) went with *less* pressure: {beta:.3f} [{lo:.3f}, {hi:.3f}] log-odds per SD of the gap, about "
                 f"{ame:.2f} percentage points per rep{kclause}, {tail}. Label: {h['label']}.")
        else:
            slots = f"; {u['pe']['slots']['hi']:.1f} draft slots at pick 64" if pe else ""
            s = (f"On {n} engaged reps, the athletic gap's effect beyond size, stopwatch and NGS athleticism was "
                 f"{beta:.3f} [{lo:.3f}, {hi:.3f}] log-odds per SD. The data are compatible with no effect and rule out "
                 f"effects larger than {hi:.3f} (about {u['ame_pp']['hi']:.2f} percentage points per rep{slots}); the "
                 f"design's MDE was {self.mde_reg:.3f}. P(effect < half the draft-pick effect) = {u['p_lt_sesoi']:.3f}. "
                 f"Label: {h['label']}.")
        d2 = self.R["decision"]["M2"]
        b2 = self.R["units"]["M2"]["logodds"]
        s += (f" With draft slot also controlled (pre-registered secondary): {d2['category']}, {b2['median']:.3f} "
              f"[{b2['lo']:.3f}, {b2['hi']:.3f}].")
        dA = self.R["decision"]["M1-A"]
        bA = self.R["units"]["M1-A"]["logodds"]
        s += (f" With the 40-yard acceleration shape added to the composite (pre-registered secondary S0): "
              f"{dA['category']}, {bA['median']:.3f} [{bA['lo']:.3f}, {bA['hi']:.3f}].")
        notes = []
        for nm, c in self.R.get("conv", {}).items():
            if c.get("fallback"):
                notes.append(f"the Bayesian fit of {nm} did not converge after escalation, so the GLM mirror with the kappa-calibrated interval is its decision basis")
        if not self.R["pc2"]["pass"]:
            notes.append("PC2 failed (the draft-pick coefficient in M2 is not entirely below 0), so no draft-pick equivalents are reported")
        if h.get("discordant"):
            notes.append("discordant sensitivities: " + ", ".join(h["discordant"]))
        if notes:
            s += " Note: " + "; ".join(notes) + "."
        return s

    # ---------------------------------------------------------------- report tables
    def build_tables(self, partial=False):
        R = self.R
        rows = []
        # R1 with pressures
        r1 = self.tabs.get("R1")
        if r1 is not None and hasattr(self.F, "y_press") and "y_press" in self.F:
            r1 = r1.copy()
            order = [k for k in ["P", "PL", "ALL", "P-A", "PL-A", "P-B", "P-DL", "SA1", "SA2", "SA3", "SA4", "SA5", "SA6",
                                 "SA7", "SA9", "SA11", "SA13", "SA15", "R"] if k in self.S]
            pr, rt = [], []
            for k in order:
                m = self.S[k]
                y = self.F.y_press[m]
                pr.append(int(np.nansum(y)))
                rt.append(round(float(np.nanmean(y)), 4))
            r1["Pressures"], r1["Rate"] = pr, rt
            self.table("R1", r1)
        # R2 decisive checks
        c2 = []
        v0 = R["v0"]
        c2.append(dict(Check="V0 counts and join", Expected="Section 2.3", Observed=v0["text"], Status=v0["status"]))
        if "pc1" in R:
            p = R["pc1"]
            ps = "PASS" if p["pass"] else ("STOP" if self.mode == "confirmatory" else "n/a in simulate mode")
            c2.append(dict(Check="PC1 events", Expected="787", Observed=str(p["events"]), Status=""))
            c2.append(dict(Check="PC1 pick coefficient", Expected="-0.204 +/- 0.003",
                           Observed=f"{p['pick']:.4f} (SE {p['pick_se']:.4f})", Status=ps))
            c2.append(dict(Check="PC1 dropback coefficient", Expected="0.577 +/- 0.003", Observed=f"{p['drop']:.4f}", Status=ps))
        if "pc2" in R:
            s = R["pc2"]["summary"]
            c2.append(dict(Check="PC2 M2 d_lpick", Expected="95% interval < 0",
                           Observed=f"{s['median']:.3f} [{s['lo']:.3f}, {s['hi']:.3f}]",
                           Status="PASS" if R["pc2"]["pass"] else "FAIL -> no PE"))
        for nm in ["M0", "M1", "M2", "M1-A", "M2-A", "M1-S1", "M1-S2", "M1-S3a", "M1-S3b", "M1-PL", "M2-PL"]:
            c = R.get("conv", {}).get(nm)
            if not c:
                continue
            st = "ok" if c["ok"] else ("FALLBACK to GLM mirror" if c.get("fallback") else "not converged")
            if c.get("light"):
                st += " (light setting)"
            c2.append(dict(Check=f"Convergence {nm}", Expected="R-hat <= 1.01, ESS >= 400, divergences <= 0.1%",
                           Observed=f"max R-hat {c['rhat_max']:.4f}, min ESS bulk/tail {c['ess_bulk_min']:.0f}/{c['ess_tail_min']:.0f}, "
                                    f"divergences {c['divergences']}, escalated {'y' if c['escalated'] else 'n'}", Status=st))
        k100 = self.man.get("CALIBRATION_CONTINGENCY") or ""
        mk = re.search(r"(\d+)\s+of\s+100", k100)
        if mk:
            kk = int(mk.group(1))
            c2.append(dict(Check="Pre-freeze Bayesian calibration (T1)", Expected="<= 9 of 100 null intervals exclude 0",
                           Observed=f"{kk} of 100; coverage {1 - kk / 100:.2f}",
                           Status=f"contingency {'ACTIVE' if self.contingency_active else 'INACTIVE'}"))
        else:
            c2.append(dict(Check="Pre-freeze Bayesian calibration (T1)", Expected="<= 9 of 100 null intervals exclude 0",
                           Observed="manifest field not filled (simulate mode)", Status="contingency " + ("ACTIVE" if self.contingency_active else "INACTIVE (default in simulate mode)")))
        kp = self.man.get("PERMUTATION_CALIBRATION") or ""
        mp = re.search(r"(\d+)\s+of\s+50", kp)
        if mp:
            kk = int(mp.group(1))
            c2.append(dict(Check="Pre-freeze permutation calibration (T1b)", Expected="<= 5 of 50 with p < 0.05",
                           Observed=f"{kk} of 50", Status="ok" if kk <= 5 else "Q2 was anti-conservative in simulation"))
        else:
            c2.append(dict(Check="Pre-freeze permutation calibration (T1b)", Expected="<= 5 of 50 with p < 0.05",
                           Observed="manifest field not filled (simulate mode)", Status=""))
        self.table("R2", pd.DataFrame(c2))
        if partial or "units" not in R:
            return
        # R3
        u, g = R["units"]["M1"], R["glm_gap"]["M1"]
        lo_ = lambda d: f"[{d['lo']:.3f}, {d['hi']:.3f}]"
        h = R["h1_final"]
        q = h["q"]
        r3 = [("beta_gap, log-odds per SD of gap: Bayes", f"mean {u['logodds']['mean']:.3f}, median {u['logodds']['median']:.3f} {lo_(u['logodds'])}"),
              ("beta_gap per composite-z unit", f"{u['per_z']['median']:.3f} {lo_(u['per_z'])}"),
              ("P(beta_gap > 0); P(beta_gap < 0.10)", f"{u['logodds']['p_pos']:.3f}; {u['p_lt_sesoi']:.3f}"),
              ("GLM mirror", f"{g['est']:.3f}; kappa-calibrated [{g['ci_kappa'][0]:.3f}, {g['ci_kappa'][1]:.3f}], p {g['p_kappa']:.4f}; "
                             f"nominal [{g['ci_nom'][0]:.3f}, {g['ci_nom'][1]:.3f}], SE {g['se']:.4f}, t df {g['df']}, p {g['p_nom']:.4f}"),
              ("AME, percentage points per rep (+1 SD gap)", f"{u['ame_pp']['median']:.3f} {lo_(u['ame_pp'])}"),
              ("Extra pressures per 100 engaged reps", f"{u['ame_pp']['median']:.3f} {lo_(u['ame_pp'])}"),
              ("Reps per extra pressure", (f"{u['reps_per_extra']['median']:.1f} [{u['reps_per_extra']['lo']:.1f}, {u['reps_per_extra']['hi']:.1f}]"
                                           if u["reps_per_extra"] else "not reported")),
              ("Base-rate pp change (power-simulation convention)", f"{u['base_rate_pp']['median']:.3f} {lo_(u['base_rate_pp'])}")]
        if u["pe"]:
            r3 += [("Pick-difference SDs per gap SD (k)", f"{u['pe']['k']['median']:.3f} {lo_(u['pe']['k'])}"),
                   ("Pick ratio exp(delta); slots at pick 64", f"{u['pe']['ratio']['median']:.3f} {lo_(u['pe']['ratio'])}; "
                                                              f"{u['pe']['slots']['median']:.2f} {lo_(u['pe']['slots'])}")]
        else:
            r3 += [("Pick-difference SDs per gap SD (k)", "not reported (PC2 failed)"),
                   ("Pick ratio exp(delta); slots at pick 64", "not reported (PC2 failed)")]
        mde_pp = (expit(logit(BASE_RATE) + self.mde_reg) - BASE_RATE) * 100
        r3.append(("MDE (section 12), log-odds / pp / pick-difference SDs", f"{self.mde_reg:.3f} / {mde_pp:.2f} / {self.mde_reg / 0.20:.2f}"))
        r3.append(("Verdict category", f"{h['category']}" + (f" (Bayesian interval: {h['bayes_category']})" if h["downgraded"] else "")
                   + f"; decision basis: {R['decision']['M1']['basis']}"))
        for k, nm in (("Q1", "Q1 GLM mirror agrees"), ("Q2", "Q2 Freedman-Lane permutation p"), ("Q3", "Q3 placebo ratio"),
                      ("Q4", "Q4 discordant sensitivities"), ("Q5", "Q5 selection")):
            r3.append((nm, f"{q[k]['status']}: {q[k]['value']}"))
        r3.append(("Final label", h["label"]))
        self.table("R3", pd.DataFrame(r3, columns=["Quantity", "Value"]))
        # R4
        r4 = []
        for nm in ("M0", "M1", "M2"):
            rec = self.models[nm]
            uu = R["units"][nm]
            gg = R["glm_gap"][nm]
            r4.append(dict(Model=nm, Term="gap", **{"Bayes median [95%]": bay_str(uu["logodds"]), "GLM [95% CI]": glm_str(gg),
                           "Pick-equivalent k [95%]": (bay_str(uu["pe"]["k"]) if uu["pe"] else "not reported")}))
        for nm in ("M1", "M2"):
            rec = self.models[nm]
            for t in rec.D.names:
                if t == "gap" or t.startswith("db") or t.startswith("dd_") or t in ("shotgun", "play_action", "s2023", "s2024", "pos_T", "pos_C", "edge", "double_team", "pre0", "pre2"):
                    continue
                r4.append(dict(Model=nm, Term=t, **{"Bayes median [95%]": bay_str(dsum(rec.bayes.draws(t))),
                                                    "GLM [95% CI]": glm_str(rec.glm.term(t)), "Pick-equivalent k [95%]": ""}))
            for k in ("B", "R"):
                r4.append(dict(Model=nm, Term=f"sigma_{k}", **{"Bayes median [95%]": bay_str(dsum(rec.bayes.post[f"sigma_{k}"])),
                                                              "GLM [95% CI]": "", "Pick-equivalent k [95%]": ""}))
        for nm in ("M1-A", "M2-A"):
            uu = R["units"][nm]
            r4.append(dict(Model=nm, Term="gap", **{"Bayes median [95%]": bay_str(uu["logodds"]), "GLM [95% CI]": glm_str(R["glm_gap"][nm]),
                           "Pick-equivalent k [95%]": (bay_str(uu["pe"]["k"]) if uu["pe"] else "not reported")}))
        self.table("R4", pd.DataFrame(r4))
        # forest data
        fr = []
        for nm in ("M0", "M1", "M2", "M1-A", "M2-A"):
            s = R["units"][nm]["logodds"]
            fr.append(dict(model=nm, term="gap", estimate=s["median"], lo=s["lo"], hi=s["hi"], kind="bayes"))
            gg = R["glm_gap"][nm]
            fr.append(dict(model=nm, term="gap", estimate=gg["est"], lo=gg["ci_kappa"][0], hi=gg["ci_kappa"][1], kind="glm_kappa"))
        for r_ in R.get("secondaries", []):
            if r_["bayes"] and "median" in r_["bayes"] and r_["ID"] in ("S1", "S2", "S3a", "S3b", "S5"):
                fr.append(dict(model=r_["Model"], term=r_["Estimand"], estimate=r_["bayes"]["median"], lo=r_["bayes"]["lo"],
                               hi=r_["bayes"]["hi"], kind="bayes"))
        self.tabs["forest"] = pd.DataFrame(fr)
        if self.out_root is not None:
            self.tabs["forest"].to_csv(self.out_root / "forest_data.csv", index=False)
        # R5
        r5 = []
        for r_ in R.get("secondaries", []):
            b = r_["bayes"]
            if "point" in b:
                bs, pd_ = f"{b['point']:.3f} (point estimate)", ""
            else:
                bs = bay_str(b)
                e = r_["Expected"]
                pd_ = f"{b['p_pos']:.3f}" if e in ("+", ">=0") else (f"{b['p_neg']:.3f}" if e == "-" else "")
            r5.append({"ID": r_["ID"], "Model": r_["Model"], "Estimand": r_["Estimand"], "Expected": r_["Expected"],
                       "Bayes median [95%]": bs, "P(expected direction)": pd_,
                       "GLM [95% CI]": glm_str(r_["glm"]) if r_["glm"] else "", "n": r_["n"], "Category (H2, S0 only)": r_["Category"]})
        self.table("R5", pd.DataFrame(r5))
        # R6
        pm_ = R["perm"]
        pl = R["placebo"]
        qq = h["q"]["Q3"]["status"]
        r6 = [("Observed GLM beta_gap (M1)", f"{pm_['beta_obs']:.4f} (t = {pm_['t_obs']:.3f})"),
              ("Null distribution of beta*: mean, SD, 2.5% / 97.5%", f"{pm_['null_mean']:.4f}, {pm_['null_sd']:.4f}, {pm_['null_lo']:.4f} / {pm_['null_hi']:.4f}"),
              ("Permutation p, two-sided / one-sided (studentized)", f"{pm_['p_two']:.4f} / {pm_['p_one']:.4f}"),
              ("Permutation p, coefficient-based two-sided", f"{pm_['p_coef']:.4f}"),
              ("Placebo M1-PL beta_gap: Bayes / GLM", f"{bay_str(pl['bayes_gap_PL'])} / {glm_str(pl['glm_gap_PL'])}"),
              ("ratio_gap (PL / P)", f"{pl['ratio_gap']:.3f} -> Q3 {qq}"),
              ("Pick calibration: M2-PL beta_lpd, ratio_pick", f"{bay_str(pl['beta_lpd_PL'])}, {pl['ratio_pick']:.3f} (C3 reference about 0.37)")]
        self.table("R6", pd.DataFrame(r6, columns=["Statistic", "Value"]))
        # R7
        cv = R["cv"]
        r7 = [dict(Table="information sets", Item=k, **{"Mean log loss": round(v["ll"], 5), "Mean Brier": round(v["brier"], 6), "Columns": v["n_cols"]})
              for k, v in cv["sets"].items()]
        for nm, k in (("I4 - I2 (tracking beyond club measures and pick)", "d42"), ("I3 - I1 (tracking beyond pick and size)", "d31"),
                      ("I2 - I1 (stopwatch beyond pick and size, reference)", "d21")):
            d = cv[k]
            r7.append(dict(Table="contrast", Item=nm, **{"Mean log loss": f"{d['mean']:.3f} millinats/rep",
                                                          "Mean Brier": f"[{d['lo']:.3f}, {d['hi']:.3f}] over repetitions",
                                                          "Columns": f"share < 0: {d['share_neg']:.2f}"}))
        for t_, key in (("leave-one-class-out", "loco"), ("leave-one-season-out", "loso")):
            for r_ in R["v8"][key]:
                r7.append(dict(Table=t_, Item=r_["unit"], **{"Mean log loss": f"n test {r_['n_test']}; LL(I2) {r_['LL_I2']:.5f}; LL(I4) {r_['LL_I4']:.5f}",
                                                             "Mean Brier": f"dLL {r_['dLL_millinats']:.3f} millinats", "Columns": ""}))
        for r_ in R["v8"]["by_season"]:
            r7.append(dict(Table="by-season GLM M1", Item=str(r_["season"]),
                           **{"Mean log loss": f"beta_gap {r_['est']:.3f} [{r_['ci_kappa'][0]:.3f}, {r_['ci_kappa'][1]:.3f}]",
                              "Mean Brier": f"n {r_['n']}", "Columns": r_["flag"]}))
        self.table("R7", pd.DataFrame(r7))
        # R8
        r8 = []
        disc = {d["id"]: d["discordant"] for d in R.get("discordance", [])}
        for sid, (desc, rec, tgt, ref) in self.sens_def.items():
            gg = rec.glm.term(tgt) if rec.glm is not None else None
            if rec.glm is None:   # SA17 / SA18: GLM mirror is identical to M1's
                gg = R["glm_gap"]["M1"]
            bb = bay_str(dsum(rec.bayes.draws(tgt))) if rec.bayes is not None else "(GLM only)"
            if rec.bayes is not None and rec.not_converged:
                bb += " (not converged)"
            r8.append({"ID": sid, "Description": desc, "Reps": rec.D.n, "Blockers / rushers": f"{rec.D.nb} / {rec.D.nr}",
                       "GLM beta_gap [95% CI]": glm_str(gg), "Bayes beta_gap [95%]": bb, "Discordant?": "yes" if disc.get(sid) else "no"})
        self.table("R8", pd.DataFrame(r8))
        # R9
        s = R["selection"]
        r9 = []
        for r_ in s["sc1"]:
            r9.append(("SC1 " + r_["var"] + " " + r_["side"] + ", in-P vs out-of-P",
                       f"n {r_['n_in']}/{r_['n_out']}; mean difference {r_['diff']:.3f} [{r_['lo']:.3f}, {r_['hi']:.3f}]; KS p {r_['ks_p']:.3f}"))
        e = s["sc1_excluded"]
        r9.append(("SC1 the excluded engaged blockers vs the included", f"{e['n_excluded']} blockers, {e['n_reps']} engaged reps; mean log pick {e['log_pick'][0]:.3f} vs {e['log_pick'][1]:.3f}; "
                   f"NGS {e['ngs'][0]:.1f} vs {e['ngs'][1]:.1f}; % missing forty {e['miss_forty'][0]:.1f} vs {e['miss_forty'][1]:.1f}"))
        g2 = s["sc2"]["glm"]
        r9.append(("SC2 gap -> engaged: GLM [95% CI]", f"{glm_str(g2)} (n {s['sc2']['n']}) -> {'flagged' if s['sc2']['flagged'] else 'not flagged'}"))
        a, b = s["sc3a"], s["sc3b"]
        r9.append(("SC3a all-pairs gap", f"{glm_str(a['gap'])}; engaged_primary {glm_str(a['eng'])} (n {a['n']})"))
        r9.append(("SC3b gap, engaged, gap x engaged", f"{glm_str(b['gap'])}; {glm_str(b['eng'])}; {glm_str(b['inter'])}"))
        r9.append(("SC4 IPW-weighted M1 gap", f"{glm_str(s['sc4']['glm'])} (weights {s['sc4']['w_min']:.2f}-{s['sc4']['w_max']:.2f})"))
        self.table("R9", pd.DataFrame(r9, columns=["Check", "Result"]))
        # R10
        r10 = []
        for nm in ("M1", "M2", "R"):
            for k in ("B", "R"):
                r10.append(dict(Item=f"{nm} sigma_{k}", Value=bay_str(R["sigma"][nm][k]) if nm in R["sigma"] else ""))
        rat = self.tabs["ratings"]
        for side in ("blocker", "rusher"):
            sub = rat[rat.side == side].sort_values("rating_mean", ascending=False)
            for lab, part in (("top 10", sub.head(10)), ("bottom 10", sub.tail(10))):
                for _, r_ in part.iterrows():
                    r10.append(dict(Item=f"{side} {lab}: nfl_id {r_.nfl_id} ({r_.reps} reps)",
                                    Value=f"{r_.rating_mean:.3f} [{r_.q05:.3f}, {r_.q95:.3f}] (90%)"))
        self.table("R10", pd.DataFrame(r10))

    # ---------------------------------------------------------------- markdown
    def write_md(self, partial=False):
        R = self.R
        L = []
        L.append("# Confirmatory results" + (" (SIMULATED OUTCOMES: pipeline test, not a result)" if self.mode == "simulate" else ""))
        L.append("")
        L.append("Filled by `scripts/confirmatory_analysis.py`; nothing in this file is written by hand.")
        L.append("")
        # R0
        L.append("## R0 Run manifest\n")
        g = self.guard or {}
        vers = installed_versions()
        sha_now = sha256_file(SCRIPT_PATH)
        match = g.get("input_match")
        r0 = [("Script SHA-256 (computed / registered)", f"{g.get('sha_script', sha_now)} / {g.get('sha_registered', self.man.get('SCRIPT_SHA256'))}"),
              ("preregistration.md SHA-256", g.get("sha_prereg", sha256_file(PREREG_PATH))),
              ("Git HEAD", g.get("git_head", "not recorded in simulate mode")),
              ("Input hashes match", ("; ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in match.items()) if match else "not checked in simulate mode")),
              ("Versions", ", ".join(f"{k} {vers[k]}" for k in ("python", "pymc", "arviz", "pytensor", "statsmodels", "numpy", "pandas", "polars"))),
              ("Start / end / CPUs", f"{g.get('start', _dt.datetime.fromtimestamp(self.t_start).isoformat(timespec='seconds'))} / "
                                     f"{_dt.datetime.now().isoformat(timespec='seconds')} / {os.cpu_count()} (cores used per fit: {min(4, os.cpu_count() or 1)})"),
              ("Status", self.status + (f" (simulate: beta_gap {self.sim_beta}, seed {self.sim_seed}{', light' if self.light_all else ''})" if self.mode == "simulate" else ""))]
        L.append(md_table(pd.DataFrame(r0, columns=["Item", "Value"])))
        L.append("")
        for key, title in (("R1", "R1 Analysis sets"), ("R2", "R2 Decisive checks")):
            if key in self.tabs:
                L.append(f"## {title}\n")
                L.append(md_table(self.tabs[key]))
                L.append("")
                if key == "R1":
                    c = R.get("constants", {})
                    L.append(f"Gap SD (registered, P): {c.get('gap_sd', float('nan')):.4f}; SD_lpd: {c.get('sd_lpd', float('nan')):.4f}; "
                             f"SD of the raw pick difference: {c.get('raw_pick_diff_sd', float('nan')):.1f} picks.\n")
                    dc = [dict(Model=k, **{"Dropped columns": "; ".join(f"{a} ({b})" for a, b in v) or "none"}) for k, v in self.dropped_cols.items()]
                    if dc:
                        L.append("Dropped columns per model (column hygiene):\n")
                        L.append(md_table(pd.DataFrame(dc)))
                        L.append("")
        if not partial and "R3" in self.tabs:
            titles = {"R3": "R3 Primary result (H1, M1, registered composite, set P)", "R4": "R4 Information ladder and forest data",
                      "R5": "R5 Secondaries", "R6": "R6 Permutation and placebo", "R7": "R7 Out-of-sample", "R8": "R8 Sensitivities",
                      "R9": "R9 Selection", "R10": "R10 Variance components and ratings"}
            for k in ("R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"):
                L.append(f"## {titles[k]}\n")
                L.append(md_table(self.tabs[k]))
                L.append("")
                if k == "R5":
                    L.append("Secondary results carry no confirmatory claim; with about 10 secondary intervals, about one in 20 would exclude 0 by chance if every effect were null.\n")
            L.append("## R11 Verdict sentence\n")
            L.append(self.verdict_sentence())
            L.append("")
        text = "\n".join(L)
        if self.rep_root is not None:
            self.rep_root.mkdir(parents=True, exist_ok=True)
            (self.rep_root / "confirmatory_results.md").write_text(text, encoding="utf-8")
        return text

    # ---------------------------------------------------------------- driver
    def step_build(self):
        self.prepare()
        rows, bad = self.v0_structural()
        self.R["v0_struct_mismatches"] = bad
        self.table("R1", self.r1_table(rows))
        # design summary
        ds = {}
        for nm, cols in (("M1", C_COLS + Q_COLS + ["gap"]), ("M2", C_COLS + Q_COLS + K_COLS + ["gap"]), ("M0", C_COLS + Q_SIZE + ["gap"])):
            idx = np.flatnonzero(self.S["P"] & self.F.ctx_ok.to_numpy())
            D = make_design(self.V["reg"].X, idx, cols, self.F, tag="design-" + nm)
            ds[nm] = dict(n_slopes=D.k, n=D.n, drops=D.drops)
        self.R["design_summary"] = ds
        if bad:
            self.R["v0"] = dict(status="STOP", text="; ".join(bad))
            log("V0 structural mismatches: " + "; ".join(bad))
            return False
        self.R["v0"] = dict(status="PASS", text=f"all section 2.3 counts match ({len(rows)} sets, {len(EXPECTED_FACTS)} facts)")
        self.dump()
        return True

    def step_outcomes(self):
        self.load_outcomes()
        bad = self.v0_outcomes()
        if bad:
            self.R["v0"] = dict(status="STOP", text="; ".join(bad))
            return False
        self.R["v0"]["text"] += "; outcome join 1:1 (no rows lost or duplicated); no nulls in pressure_allowed on P"
        return True

    def stop(self, why):
        self.status = f"STOP at {why}"
        self.build_tables(partial=True)
        self.write_md(partial=True)
        self.dump()
        self.flush_log()

    def run(self, only: str | None = None):
        t0 = time.time()
        STEPS = ["build", "outcomes", "pc1", "m1", "m2", "verdict", "secondaries", "v5", "v6", "v7", "v8", "sens", "selection",
                 "ratings", "final"]
        if only is not None and only not in STEPS:
            raise SystemExit(f"--only must be one of {STEPS}")
        want = lambda s: only is None or only == s
        log("step 2: build sets, constants and columns")
        if not self.step_build():
            self.stop("V0")
            return 2
        log("step 3: outcomes and V0")
        if not self.step_outcomes():
            self.stop("V0")
            return 2
        log("step 4: PC1")
        pc = self.pc1()
        self.R["pc1"] = pc
        log(f"  PC1: events {pc['events']}, pick {pc['pick']:.4f}, dropback {pc['drop']:.4f}, pass={pc['pass']}")
        if not pc["pass"] and self.mode == "confirmatory":
            self.stop("PC1")
            return 3
        if want("pc1") and only == "pc1":
            self.dump()
            return 0
        if only in (None, "m1", "m2", "verdict", "final"):
            self.step_primary()
        if only in (None, "secondaries", "final"):
            self.step_secondaries()
        if only in (None, "v5", "final"):
            log("step 9: V5 permutation")
            self.step_permutation(2000 if self.mode == "confirmatory" else self.perm_n)
        if only in (None, "v6", "final"):
            log("step 9: V6 placebo")
            self.step_placebo()
        if only in (None, "v7", "final"):
            log("step 9: V7 CV")
            self.step_cv()
        if only in (None, "v8", "final"):
            log("step 9: V8")
            self.step_v8()
        self.dump()
        if only in (None, "sens", "final"):
            log("step 10: sensitivities")
            self.step_sensitivities()
        if only in (None, "selection", "final"):
            log("step 11: selection")
            self.step_selection()
        if only in (None, "ratings", "final"):
            log("step 12: ratings and surface")
            self.step_ratings()
        if only in (None, "final"):
            log("step 13: final outputs")
            self.status = "COMPLETE"
            self.finalize_verdict()
            self.build_tables()
            self.R["verdict_sentence"] = self.verdict_sentence()
            self.R["timings"] = dict(self.timings, total=time.time() - self.t_start)
            self.write_md()
            self.dump()
        self.flush_log()
        log(f"done in {time.time() - t0:.0f}s")
        return 0


# ----------------------------------------------------------------------------------------------- command line
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["simulate", "confirmatory"], required=True)
    ap.add_argument("--sim-beta-gap", type=float, default=None)
    ap.add_argument("--sim-seed", type=int, default=None)
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args(argv)
    STATE["mode"] = a.mode
    if a.mode == "simulate":
        if a.rerun_reason:
            ap.error("--rerun-reason is for confirmatory mode only")
        beta = 0.0 if a.sim_beta_gap is None else a.sim_beta_gap
        seed = 1 if a.sim_seed is None else a.sim_seed
        root = REPO_ROOT / "data" / "processed" / "confirmatory_sim" / str(seed)
        A = Analysis("simulate", beta, seed, a.light, out_root=root)
        A.rep_root = root
        A.perm_n = 199 if a.light else 2000
        log(f"simulate mode: beta_gap {beta}, seed {seed}, light {a.light}, out {root}")
        rc = A.run(a.only)
        return rc
    # confirmatory
    if a.sim_beta_gap is not None or a.sim_seed is not None or a.light or a.only:
        ap.error("confirmatory mode accepts no options other than --rerun-reason")
    guard = run_guards(a.rerun_reason)
    log("guards passed: " + json.dumps({k: v for k, v in guard.items() if k in ("sha_script", "sha_prereg", "git_head", "start")}))
    run_dir = guard["run_dir"]
    rep_root = run_dir if run_dir is not None else REPO_ROOT / "reports"
    data_root = (REPO_ROOT / "data" / "processed" / "confirmatory" / (run_dir.name if run_dir is not None else ""))
    A = Analysis("confirmatory", out_root=data_root, man=guard["manifest"], guard=guard)
    A.rep_root = rep_root
    A.perm_n = 2000
    # tables and the json go to the reports tree; data products to the git-ignored data tree
    A.table_root = (REPO_ROOT / "reports" / "confirmatory" / "tables") if run_dir is None else run_dir / "tables"
    return A.run(None)


if __name__ == "__main__":
    sys.exit(main())

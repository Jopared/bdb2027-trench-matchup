#!/usr/bin/env python
"""Pre-freeze acceptance tests T1-T6 (+T1b) for scripts/confirmatory_analysis.py (pre-registration section 13.3).

Simulate mode only. Never touches the outcome file: T5 instruments every file-open call and asserts that.
Usage (from the repo root):
  .venv\\Scripts\\python.exe scripts\\confirmatory_script_tests.py t5 t6 t2 t4 t1 t1b report [--workers 7]
Each test appends its result to data/processed/confirmatory_sim/test_results.json; `report` renders
reports/confirmatory_script_tests.md from that file.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "confirmatory_analysis.py"
SIMROOT = ROOT / "data" / "processed" / "confirmatory_sim"
RESULTS = SIMROOT / "test_results.json"
REPORT = ROOT / "reports" / "confirmatory_script_tests.md"
PY = sys.executable


def load_ca():
    spec = importlib.util.spec_from_file_location("confirmatory_analysis", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["confirmatory_analysis"] = m
    spec.loader.exec_module(m)
    m.STATE["mode"] = "simulate"
    return m


def read_results() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}


def save_result(key: str, val: dict):
    SIMROOT.mkdir(parents=True, exist_ok=True)
    r = read_results()
    r[key] = val
    RESULTS.write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


# ------------------------------------------------------------------------------------------------ worker functions
_A = {}


def _analysis(escalate=None):
    if escalate is None:
        escalate = os.environ.get("T_ESCALATE", "1") == "1"
    if "A" not in _A:
        ca = load_ca()
        A = ca.Analysis("simulate", out_root=None, save_idata_files=False)
        A.escalate = escalate
        A.prepare(with_k5=False)
        _A["ca"], _A["A"] = ca, A
    return _A["ca"], _A["A"]


def _reset_outcomes(A, ca, seed, beta):
    A.sim_seed, A.sim_beta = seed, beta
    A.models.clear()
    A.dropped_cols.clear()
    A.load_outcomes()


def worker_t1(args):
    seed, beta, light = args
    ca, A = _analysis()
    t = time.time()
    _reset_outcomes(A, ca, seed, beta)
    A.light_all = light
    m1 = A.model("M1")
    b = m1.bayes.draws("gap")
    s = ca.dsum(b)
    g = m1.glm.term("gap")
    tq = ca.stats.t.ppf(0.975, g["df"])
    out = dict(seed=seed, median=s["median"], mean=s["mean"], lo=s["lo"], hi=s["hi"], excl0=bool(s["lo"] > 0 or s["hi"] < 0),
               covers_true=bool(s["lo"] <= beta <= s["hi"]), glm_est=g["est"], glm_se=g["se"],
               glm_nom_wald_z=bool(abs(g["est"] / g["se"]) > 1.959964), glm_nom_t=bool(abs(g["est"] / g["se"]) > tq),
               glm_kappa_t=bool(g["ci_kappa"][0] > 0 or g["ci_kappa"][1] < 0), diag=m1.bayes.diag, seconds=time.time() - t)
    return out


def worker_t2(args):
    seed, beta = args
    ca, A = _analysis()
    t = time.time()
    A.light_all = True
    _reset_outcomes(A, ca, seed, beta)
    m1 = A.model("M1")
    m2 = A.model("M2")
    s1, s2 = ca.dsum(m1.bayes.draws("gap")), ca.dsum(m2.bayes.draws("d_lpick"))
    s2g = ca.dsum(m2.bayes.draws("gap"))
    return dict(seed=seed, m1=s1, m2_lpd=s2, m2_gap=s2g, covers=bool(s1["lo"] <= beta <= s1["hi"]),
                diag1=m1.bayes.diag, diag2=m2.bayes.diag, seconds=time.time() - t)


def worker_t1b(args):
    seed, nperm = args
    ca, A = _analysis()
    _reset_outcomes(A, ca, seed, 0.0)
    # M1 GLM mirror only (no Bayesian fit needed for the permutation test)
    rec = A.fit_model("M1", "reg", "P", ca.C_COLS + ca.Q_COLS + ["gap"], bayes=False)
    A.models["M1"] = rec
    t = time.time()
    r = A.step_permutation(nperm, rng_seed=seed, save=False)
    return dict(seed=seed, p_two=r["p_two"], p_one=r["p_one"], t_obs=r["t_obs"], seconds=time.time() - t)


def run_pool(fn, argl, workers):
    out = []
    t = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(fn, argl)):
            out.append(r)
            print(f"  {fn.__name__} {i + 1}/{len(argl)} done ({time.time() - t:.0f}s)", flush=True)
    return out


# ------------------------------------------------------------------------------------------------ tests
def test_t5():
    """Sealed-file isolation: static check + instrumented simulate run; the sealed file is never touched."""
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and ("SEALED" in node.value or "engaged_outcomes" in node.value):
            hits.append(node.lineno)
    func_ranges = {n.name: (n.lineno, n.end_lineno) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    lo, hi = func_ranges["load_sealed_outcomes"]
    static_ok = bool(hits) and all(lo <= h <= hi for h in hits)
    mentions = [i + 1 for i, l in enumerate(src.splitlines()) if "SEALED" in l or "engaged_outcomes" in l]
    # dynamic: instrument open() and parquet readers
    ca = load_ca()
    seen = []
    real_open, real_io_open = builtins.open, io.open

    def rec(p):
        seen.append(str(p))

    def fake_open(file, *a, **k):
        rec(file)
        return real_open(file, *a, **k)
    builtins.open = fake_open
    import polars as pl
    real_rp, real_sp = pl.read_parquet, pl.scan_parquet
    pl.read_parquet = lambda p, *a, **k: (rec(p), real_rp(p, *a, **k))[1]
    pl.scan_parquet = lambda p, *a, **k: (rec(p), real_sp(p, *a, **k))[1]
    real_pd = pd.read_parquet
    pd.read_parquet = lambda p, *a, **k: (rec(p), real_pd(p, *a, **k))[1]
    real_path_open = Path.open
    Path.open = lambda self, *a, **k: (rec(self), real_path_open(self, *a, **k))[1]
    real_rb = Path.read_bytes
    Path.read_bytes = lambda self: (rec(self), real_rb(self))[1]
    real_rt = Path.read_text
    Path.read_text = lambda self, *a, **k: (rec(self), real_rt(self, *a, **k))[1]
    calls = {"n": 0}
    real_lso = ca.load_sealed_outcomes

    def counting():
        calls["n"] += 1
        return real_lso()
    ca.load_sealed_outcomes = counting
    raised = None
    try:
        A = ca.Analysis("simulate", sim_beta=0.0, sim_seed=1, out_root=None, save_idata_files=False)
        A.prepare(with_k5=True)
        A.load_outcomes()
        A.pc1()
        try:
            ca.load_sealed_outcomes()          # must refuse in simulate mode before touching the path
        except RuntimeError as e:
            raised = str(e)
        ca.STATE["guards_passed"] = True        # even with guards "passed", the mode check must refuse
        try:
            ca.load_sealed_outcomes()
            raised2 = None
        except RuntimeError as e:
            raised2 = str(e)
        ca.STATE["guards_passed"] = False
    finally:
        builtins.open = real_open
        pl.read_parquet, pl.scan_parquet = real_rp, real_sp
        pd.read_parquet = real_pd
        Path.open, Path.read_bytes, Path.read_text = real_path_open, real_rb, real_rt
    touched = [s for s in seen if "SEALED" in s or "engaged_outcomes" in s]
    ok = static_ok and not touched and calls["n"] == 2 and raised is not None and raised2 is not None
    res = dict(passed=bool(ok), static_ok=static_ok, mention_lines=mentions, n_open_calls_recorded=len(seen),
               sealed_paths_touched=touched, load_sealed_calls=calls["n"], refused_in_simulate=raised,
               refused_with_guards_flag=raised2)
    # confirmatory-mode guard parser on a synthetic manifest (confirmatory mode itself is never executed)
    man_text = (ROOT / "reports" / "preregistration.md").read_text(encoding="utf-8")
    man = ca.parse_manifest(man_text)
    res["manifest_incomplete_fields_now"] = ca.manifest_incomplete(man)
    filled = man_text.replace("[fill: sha256 of scripts/confirmatory_analysis.py]", "0" * 64)
    man2 = ca.parse_manifest(filled)
    res["guard_refuses_unfilled_manifest"] = bool(ca.manifest_incomplete(man))
    fake = """### 13.1
    SCRIPT_SHA256: %s
    INPUT_SHA256 data/processed/x.parquet: %s
    INPUT_SHA256 data/processed/engaged_pairs.parquet: %s
    INPUT_SHA256 data/processed/player_baselines.parquet: %s
    INPUT_SHA256 data/processed/combine_traits.parquet: %s
    INPUT_SHA256 data/processed/combine_tracking.parquet: %s
    INPUT_SHA256 data/processed/combine_results.parquet: %s
    INPUT_SHA256 src/bdb2027/traits.py: %s
    INPUT_SHA256 src/bdb2027/paths.py: %s
    PACKAGE_VERSIONS: python 3.12.10
    KAPPA_GLM_SE_INFLATION: 1.20
    CALIBRATION_CONTINGENCY: INACTIVE, 3 of 100 null intervals excluded 0
    PERMUTATION_CALIBRATION: 2 of 50 null datasets with permutation p < 0.05
    MDE_REGISTERED_LOGODDS: 0.247
    MDE_SENSA_LOGODDS: 0.234
### 13.2
""" % ("a" * 64, *(["b" * 64] * 8))
    mf = ca.parse_manifest(fake)
    res["guard_accepts_complete_synthetic_manifest"] = (ca.manifest_incomplete(mf) == [])
    res["passed"] = bool(res["passed"] and res["guard_refuses_unfilled_manifest"] and res["guard_accepts_complete_synthetic_manifest"])
    save_result("T5", res)
    return res


def test_t6():
    ca = load_ca()
    rng = np.random.default_rng(6)
    n, nb = 400_000, 120
    blocker = rng.integers(0, nb, n)
    dpick = rng.normal(0, 96, n)
    dwt = rng.normal(0, 25, n)
    drop = np.clip(rng.gamma(6, 0.5, n), 0.6, 14)
    zp = (dpick - dpick.mean()) / dpick.std(ddof=1)
    zw = (dwt - dwt.mean()) / dwt.std(ddof=1)
    true = dict(pick=-0.204, wt=-0.214, drop=0.577)
    lp = -3.2 + true["pick"] * zp + true["wt"] * zw + true["drop"] * drop
    y = (rng.random(n) < ca.expit(lp)).astype(int)
    tab = pd.DataFrame(dict(pick_R=dpick, pick_B=0.0, w_R=dwt, w_B=0.0, dropback=drop, blocker=blocker, y=y))
    r = ca.pc1_compute(tab)
    # independent implementation: numpy IRLS + one-way cluster sandwich with the statsmodels small-sample factor
    X = np.column_stack([np.ones(n), zp, zw, drop])
    beta = ca.irls_logit(X, y.astype(float))
    p = ca.expit(X @ beta)
    bread = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    S = X * (y - p)[:, None]
    Sg = np.zeros((nb, 4))
    np.add.at(Sg, blocker, S)
    meat = Sg.T @ Sg * (nb / (nb - 1.0)) * ((n - 1.0) / (n - 4))
    se = np.sqrt(np.diag(bread @ meat @ bread))
    close = dict(pick=abs(r["pick"] - beta[1]), wt=abs(r["wt"] - beta[2]), drop=abs(r["drop"] - beta[3]),
                 se_pick=abs(r["pick_se"] - se[1]), se_drop=abs(r["drop_se"] - se[3]))
    recovered = dict(pick=abs(r["pick"] - true["pick"]), wt=abs(r["wt"] - true["wt"]), drop=abs(r["drop"] - true["drop"]))
    # the pass rule on boundary values
    rule = [ca.pc1_status(dict(events=787, pick=-0.204, drop=0.577)), ca.pc1_status(dict(events=787, pick=-0.2069, drop=0.5799)),
            not ca.pc1_status(dict(events=786, pick=-0.204, drop=0.577)), not ca.pc1_status(dict(events=787, pick=-0.2075, drop=0.577)),
            not ca.pc1_status(dict(events=787, pick=-0.204, drop=0.5805))]
    ok = max(close.values()) < 1e-6 and max(recovered.values()) < 0.02 and all(rule)
    res = dict(passed=bool(ok), n=n, estimated=dict(pick=r["pick"], wt=r["wt"], drop=r["drop"], pick_se=r["pick_se"]),
               truth=true, max_abs_diff_vs_independent_implementation=max(close.values()), recovery_error=recovered,
               pass_rule_checks=rule)
    save_result("T6", res)
    return res


def test_t2(workers):
    seeds = list(range(101, 106))
    t = time.time()
    out = run_pool(worker_t2, [(s, 0.25) for s in seeds], min(workers, 5))
    m1 = [o["m1"]["median"] for o in out]
    m2 = [o["m2_lpd"]["median"] for o in out]
    cover = sum(o["covers"] for o in out)
    t2_ok = abs(np.mean(m1) - 0.25) <= 0.08 and cover >= 4
    t3_ok = abs(np.mean(m2) - (-0.20)) <= 0.08
    res2 = dict(passed=bool(t2_ok), mean_estimate=float(np.mean(m1)), estimates=m1, intervals=[(o["m1"]["lo"], o["m1"]["hi"]) for o in out],
                covered=int(cover), setting="light (1000/1000)" + ("" if os.environ.get("T_ESCALATE", "1") == "1" else ", escalation disabled"), seconds=time.time() - t,
                diag=[{k: o["diag1"][k] for k in ("rhat_max", "ess_bulk_min", "ess_tail_min", "divergences", "ok")} for o in out])
    res3 = dict(passed=bool(t3_ok), mean_estimate=float(np.mean(m2)), estimates=m2,
                intervals=[(o["m2_lpd"]["lo"], o["m2_lpd"]["hi"]) for o in out],
                m2_gap_estimates=[o["m2_gap"]["median"] for o in out])
    save_result("T2", res2)
    save_result("T3", res3)
    return res2, res3


def test_t4(light=False):
    seed = 201
    t = time.time()
    cmd = [PY, str(SCRIPT), "--mode", "simulate", "--sim-seed", str(seed), "--sim-beta-gap", "0.25"] + (["--light"] if light else [])
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    secs = time.time() - t
    root = SIMROOT / str(seed)
    problems = []
    tables = {}
    for k in range(1, 11):
        f = root / "tables" / f"R{k}.csv"
        if not f.exists():
            problems.append(f"missing R{k}.csv")
            continue
        df = pd.read_csv(f, keep_default_na=False)
        tables[f"R{k}"] = df.shape
        bad = df.apply(lambda c: c.astype(str).str.contains(r"\bnan\b|\bNaN\b|\binf\b", regex=True)).sum().sum()
        empt = int(((df == "").sum()).sum())
        if bad:
            problems.append(f"R{k}: {int(bad)} nan/inf cells")
        tables[f"R{k}"] = dict(shape=df.shape, nan_cells=int(bad), empty_cells=empt)
    md = root / "confirmatory_results.md"
    if not md.exists():
        problems.append("missing md")
    else:
        txt = md.read_text(encoding="utf-8")
        for k in range(0, 12):
            if f"## R{k} " not in txt and k > 0:
                problems.append(f"md lacks R{k}")
        if "nan" in txt.replace("finance", "").lower().split():
            problems.append("md contains bare nan")
    ok = p.returncode == 0 and not problems and (root / "confirmatory_results.json").exists()
    res = dict(passed=bool(ok), returncode=p.returncode, seconds=secs, light=light, problems=problems, tables=tables,
               stderr_tail=p.stderr[-1500:], stdout_tail=p.stdout[-1500:], out=str(root))
    save_result("T4", res)
    return res


def test_t1(workers, n=100, light=True):
    t = time.time()
    out = run_pool(worker_t1, [(s, 0.0, light) for s in range(1, n + 1)], workers)
    k = sum(o["excl0"] for o in out)
    res = dict(n=n, k_excl0=int(k), coverage=float(1 - k / n), contingency="ACTIVE" if k >= 10 else "INACTIVE",
               k_pos=int(sum(o["lo"] > 0 for o in out)), k_neg=int(sum(o["hi"] < 0 for o in out)),
               glm_nominal_wald_z=int(sum(o["glm_nom_wald_z"] for o in out)), glm_nominal_t=int(sum(o["glm_nom_t"] for o in out)),
               glm_kappa=int(sum(o["glm_kappa_t"] for o in out)),
               mean_estimate=float(np.mean([o["median"] for o in out])), sd_estimate=float(np.std([o["median"] for o in out], ddof=1)),
               mean_posterior_sd=float(np.mean([(o["hi"] - o["lo"]) / 3.92 for o in out])),
               mean_glm_se=float(np.mean([o["glm_se"] for o in out])),
               n_not_converged=int(sum(not o["diag"]["ok"] for o in out)),
               n_rhat_gt_1_01=int(sum(o["diag"]["rhat_max"] > 1.01 for o in out)),
               n_ess_lt_400=int(sum(min(o["diag"]["ess_bulk_min"], o["diag"]["ess_tail_min"]) < 400 for o in out)),
               n_divergent_fits=int(sum(o["diag"]["divergences"] > 0 for o in out)),
               max_rhat=float(max(o["diag"]["rhat_max"] for o in out)),
               sampler_seconds_mean=float(np.mean([o["diag"]["seconds"] for o in out])),
               fit_seconds_mean=float(np.mean([o["seconds"] for o in out])),
               wall_seconds=time.time() - t, workers=workers,
               setting=("light (1000/1000, 4 chains)" if light else "full") + (", with the section 5.5 escalation" if os.environ.get("T_ESCALATE", "1") == "1" else ", escalation disabled"), per_seed=out)
    save_result("T1", res)
    return res


def test_t1b(workers, n=50, nperm=199):
    t = time.time()
    out = run_pool(worker_t1b, [(s, nperm) for s in range(1, n + 1)], workers)
    k = sum(o["p_two"] < 0.05 for o in out)
    res = dict(n=n, nperm=nperm, k_p_lt_005=int(k), anti_conservative=bool(k >= 6),
               mean_perm_seconds=float(np.mean([o["seconds"] for o in out])), wall_seconds=time.time() - t,
               p_values=[o["p_two"] for o in out])
    save_result("T1b", res)
    return res


# ------------------------------------------------------------------------------------------------ report
def render_report():
    r = read_results()
    L = ["# Confirmatory script: pre-freeze acceptance tests (simulate mode only)", "",
         "Script under test: `scripts/confirmatory_analysis.py`. Test driver: `scripts/confirmatory_script_tests.py`. "
         "Every outcome here is simulated; the outcome file was not opened (T5). "
         f"Script SHA-256 at report time: `{__import__('hashlib').sha256(SCRIPT.read_bytes()).hexdigest()}`.", ""]
    L += ["| Test | Result |", "|---|---|"]
    names = {"T1": "Bayesian null calibration", "T1b": "Permutation calibration", "T2": "Planted effect 0.25, M1",
             "T3": "Planted effect, M2 d_lpick", "T4": "End-to-end simulate run", "T5": "Sealed-file isolation",
             "T6": "PC1 code path"}
    for k in ("T1", "T1b", "T2", "T3", "T4", "T5", "T6"):
        if k not in r:
            L.append(f"| {k} {names[k]} | not run |")
            continue
        v = r[k]
        if k == "T1":
            s = f"k = {v['k_excl0']} of {v['n']} null intervals exclude 0 -> CALIBRATION_CONTINGENCY: {v['contingency']}"
        elif k == "T1b":
            s = f"{v['k_p_lt_005']} of {v['n']} with p < 0.05 -> {'anti-conservative (>= 6)' if v['anti_conservative'] else 'ok (<= 5)'}"
        else:
            s = "PASS" if v["passed"] else "FAIL"
        L.append(f"| {k} {names[k]} | {s} |")
    L.append("")
    if "T1" in r:
        v = r["T1"]
        L += ["## T1 Bayesian null calibration", "",
              f"Setting: {v['setting']}; {v['n']} null datasets (beta_gap = 0, sim seeds 1-{v['n']}, P design, M1 as in confirmatory mode "
              f"(`target_accept` 0.90, seed 2027), {v['workers']} fits in parallel, 4 chains each).", "",
              "| Quantity | Value |", "|---|---|",
              f"| Intervals excluding 0 (either direction) | **{v['k_excl0']} of {v['n']}** (positive {v['k_pos']}, negative {v['k_neg']}) |",
              f"| Coverage of the true value 0 | {v['coverage']:.2f} |",
              f"| Contingency | **{v['contingency']}** (ACTIVE if k >= 10) |",
              f"| GLM mirror, rejections at nominal Wald z (information only) | {v['glm_nominal_wald_z']} of {v['n']} |",
              f"| GLM mirror, rejections with t(G-1) reference (nominal) | {v['glm_nominal_t']} of {v['n']} |",
              f"| GLM mirror, rejections kappa-calibrated (kappa 1.20, t reference) | {v['glm_kappa']} of {v['n']} |",
              f"| Mean / SD of Bayesian posterior median over datasets | {v['mean_estimate']:.4f} / {v['sd_estimate']:.4f} |",
              f"| Mean posterior SD (width/3.92) vs mean GLM two-way SE | {v['mean_posterior_sd']:.4f} vs {v['mean_glm_se']:.4f} |",
              f"| Fits failing the section 5.5 criteria (any of R-hat, ESS, divergences) | {v['n_not_converged']} of {v['n']} (R-hat > 1.01: {v['n_rhat_gt_1_01']}, ESS < 400: {v['n_ess_lt_400']}, any divergence: {v['n_divergent_fits']}; max R-hat {v['max_rhat']:.3f}) |",
              f"| Timing | mean sampling time per fit {v['sampler_seconds_mean']:.0f}s; mean per-dataset time {v['fit_seconds_mean']:.0f}s; wall {v['wall_seconds'] / 60:.1f} min |", ""]
    if "T1b" in r:
        v = r["T1b"]
        L += ["## T1b Permutation calibration", "",
              f"First {v['n']} null datasets (seeds 1-{v['n']}), studentized Freedman-Lane test, {v['nperm']} permutations each, "
              f"`default_rng(sim_seed)`. **{v['k_p_lt_005']} of {v['n']}** have two-sided p < 0.05 "
              f"(P(>= 6 of 50) = 0.04 under nominal size). Mean time per test {v['mean_perm_seconds']:.1f}s; wall {v['wall_seconds'] / 60:.1f} min.", ""]
    for k in ("T2", "T3"):
        if k in r:
            v = r[k]
            L += [f"## {k} {names[k]}", "",
                  f"Seeds 101-105, beta_gap = 0.25. Estimates (posterior medians): {', '.join(f'{x:.3f}' for x in v['estimates'])}; mean {v['mean_estimate']:.3f}. "
                  + (f"Intervals cover 0.25 in {v['covered']} of 5. Setting: {v['setting']}. " if k == "T2" else "Target -0.20 +/- 0.08. ")
                  + f"**{'PASS' if v['passed'] else 'FAIL'}**.", ""]
    if "T4" in r:
        v = r["T4"]
        L += ["## T4 End-to-end simulate run", "",
              f"`--mode simulate --sim-seed 201 --sim-beta-gap 0.25{' --light' if v['light'] else ''}`: return code {v['returncode']}, "
              f"runtime {v['seconds'] / 60:.1f} min, problems: {v['problems'] or 'none'}. Outputs in `{v['out']}`. "
              f"**{'PASS' if v['passed'] else 'FAIL'}**.", "", "| Table | rows x cols | NaN cells | empty cells |", "|---|---|---|---|"]
        for t_, d in v["tables"].items():
            if isinstance(d, dict):
                L.append(f"| {t_} | {d['shape'][0]} x {d['shape'][1]} | {d['nan_cells']} | {d['empty_cells']} |")
        L.append("")
    if "T5" in r:
        v = r["T5"]
        L += ["## T5 Sealed-file isolation", "",
              f"Static: the outcome file name occurs on source lines {v['mention_lines']}, all inside `load_sealed_outcomes` ({v['static_ok']}). "
              f"Dynamic: `open`, `Path.open/read_bytes/read_text`, `polars.read_parquet/scan_parquet`, `pandas.read_parquet` instrumented around a simulate "
              f"build + outcome generation + PC1 ({v['n_open_calls_recorded']} file-open calls recorded, none naming the outcome file: {not v['sealed_paths_touched']}); "
              f"`load_sealed_outcomes` called twice on purpose in simulate mode (once with the guard flag forced True) and refused both times before any file access "
              f"({v['load_sealed_calls']} calls, refusals: {bool(v['refused_in_simulate'])}, {bool(v['refused_with_guards_flag'])}). "
              f"The guard parser refuses the current manifest (fields still open: {v['manifest_incomplete_fields_now']}) and accepts a complete synthetic manifest. "
              f"Confirmatory mode was never executed. **{'PASS' if v['passed'] else 'FAIL'}**.", ""]
    if "T6" in r:
        v = r["T6"]
        L += ["## T6 PC1 code path", "",
              f"Synthetic table (n = {v['n']:,}) built from logit with pick -0.204, weight -0.214, dropback +0.577. Recovered: pick {v['estimated']['pick']:.4f}, "
              f"weight {v['estimated']['wt']:.4f}, dropback {v['estimated']['drop']:.4f}. Maximum absolute difference to an independent numpy IRLS + one-way "
              f"cluster-sandwich implementation: {v['max_abs_diff_vs_independent_implementation']:.2e}. Pass-rule boundary checks: {v['pass_rule_checks']}. "
              f"**{'PASS' if v['passed'] else 'FAIL'}**. PC1 on the real outcomes cannot be run before freeze.", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    return REPORT


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--light-t4", action="store_true")
    a = ap.parse_args()
    for t in a.tests:
        t0 = time.time()
        if t == "t5":
            r = test_t5()
        elif t == "t6":
            r = test_t6()
        elif t == "t2":
            r = test_t2(a.workers)
        elif t == "t4":
            r = test_t4(a.light_t4)
        elif t == "t1":
            r = test_t1(a.workers, a.n)
        elif t == "t1b":
            r = test_t1b(a.workers)
        elif t == "report":
            r = render_report()
        else:
            raise SystemExit("unknown test " + t)
        short = {k: v for k, v in r.items() if k not in ("per_seed", "stdout_tail", "stderr_tail")} if isinstance(r, dict) else r
        print(f"== {t} ({time.time() - t0:.0f}s):", json.dumps(short, default=str)[:1500], flush=True)

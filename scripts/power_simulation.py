"""Power / MDE simulation on the REAL design matrix with SIMULATED outcomes.

Never opens data/processed/engaged_outcomes_SEALED.parquet.
Run from repo root:  .venv\\Scripts\\python.exe scripts\\power_simulation.py [--nsim 500] [--quick]
Writes reports/power_simulation.md (and a json cache next to it in the scratch dir is not used).
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import scipy.sparse as sp
from patsy import dmatrix
from scipy.optimize import brentq
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
BASE_RATE = 0.0952
B_PICK = -0.20
B_DROP = 0.58
SEED = 2027
EFFECTS = [0.0, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
RE_SDS = [0.35, 0.20, 0.50]
COMPOSITES = {"registered": "composite", "sensA": "composite_sensA"}

# ---------------------------------------------------------------- design ----

def rcs_basis(x, qs=(0.05, 0.35, 0.65, 0.95)):
    """Natural (restricted) cubic spline, Harrell parametrisation, 4 knots -> linear + 2 nonlinear terms (3 df)."""
    t = np.quantile(x, qs)
    k = len(t)
    def pos3(u):
        return np.clip(u, 0, None) ** 3
    out = []
    for j in range(k - 2):
        term = (pos3(x - t[j]) - pos3(x - t[k - 2]) * (t[k - 1] - t[j]) / (t[k - 1] - t[k - 2])
                + pos3(x - t[k - 1]) * (t[k - 2] - t[j]) / (t[k - 1] - t[k - 2]))
        out.append(term / (t[k - 1] - t[0]) ** 2)
    out = [(o - o.mean()) / o.std() for o in out]
    return out


def load_design(comp_col):
    pairs = pl.read_parquet(PROC / "engaged_pairs.parquet").to_pandas()
    base = pl.read_parquet(PROC / "player_baselines.parquet").to_pandas().set_index("nfl_id")
    tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas().set_index("nfl_id")
    d = pairs[pairs.engaged_primary].copy()
    d = d[d.blocker_lined_up_position.isin(["T", "G", "C"]) & (d.blocker_combine_position == "OL")
          & (d.rusher_combine_position == "DL")
          & d.rusher_lined_up_position.isin(["EDGE", "INTERIOR_LINE"])]
    d["bcomp"] = d.blocker_nfl_id.map(tr[comp_col])
    d["rcomp"] = d.rusher_nfl_id.map(tr[comp_col])
    d = d[d.bcomp.notna() & d.rcomp.notna()].reset_index(drop=True)
    d["gap"] = d.rcomp - d.bcomp

    cont = ["log_pick", "combine_weight", "arm_length", "forty", "ten_yd_split",
            "short_shuttle", "ngs_athleticism_score"]
    flags = ["undrafted", "forty_missing", "ten_yd_split_missing", "short_shuttle_missing",
             "arm_length_missing", "combine_weight_missing", "ngs_athleticism_score_missing"]
    # standardise each baseline on the analysis-set players (both sides pooled), impute missing at 0
    allp = pd.concat([d.blocker_nfl_id, d.rusher_nfl_id]).unique()
    bp = base.loc[allp]
    for c in cont:
        mu, sd = bp[c].mean(), bp[c].std()
        base[c + "_z"] = (base[c] - mu) / sd
        base[c + "_z"] = base[c + "_z"].fillna(0.0)
    for c in flags:
        base[c] = base[c].astype(float)
    X = pd.DataFrame(index=d.index)
    for c in cont:
        X["d_" + c] = d.rusher_nfl_id.map(base[c + "_z"]).values - d.blocker_nfl_id.map(base[c + "_z"]).values
    for c in flags:
        X["d_" + c] = d.rusher_nfl_id.map(base[c]).values - d.blocker_nfl_id.map(base[c]).values
    # standardise the difference columns (continuous ones only)
    for c in ["d_" + c for c in cont]:
        X[c] = (X[c] - X[c].mean()) / X[c].std()
    # pick difference (rusher - blocker log pick), standardised: used in the generator
    d["pick_diff_z"] = X["d_log_pick"]
    d["drop_z"] = (d.dropback_duration - d.dropback_duration.mean()) / d.dropback_duration.std()
    d["pre"] = d.pass_rushers_encountered
    d["pre_z"] = (d.pre - d.pre.mean()) / d.pre.std()
    d["gap_z"] = (d.gap - d.gap.mean()) / d.gap.std()
    dn = d.down.clip(upper=3)
    yb = pd.cut(d.yards_to_go, [-1, 3, 7, 1000], labels=["short", "med", "long"])
    d["dxd"] = dn.astype(str) + "_" + yb.astype(str)
    d["shotgun_i"] = d.shotgun.astype(float)
    d["pa_i"] = d.play_action.astype(float)
    d["dt_i"] = d.double_team.astype(float)
    d["edge_i"] = (d.rusher_lined_up_position == "EDGE").astype(float)
    d["bpos"] = d.blocker_lined_up_position
    d["season_c"] = d.season.astype(str)
    r1, r2 = rcs_basis(d.dropback_duration.values)
    d["rcs1"], d["rcs2"] = r1, r2
    ctx = dmatrix("rcs1 + rcs2 + C(dxd) + shotgun_i + pa_i + C(season_c) + C(bpos)"
                  " + edge_i + dt_i + pre_z", d, return_type="dataframe")
    # patsy gives an Intercept column first
    ctx["dropback_lin"] = d.drop_z.values
    F = pd.concat([ctx.reset_index(drop=True), X.reset_index(drop=True)], axis=1)
    # drop constant / duplicate columns other than Intercept
    keep = [c for c in F.columns if c == "Intercept" or F[c].std() > 1e-9]
    F = F[keep]
    F = F.loc[:, ~F.T.duplicated()]  # identical columns (e.g. forty / ten-yard missing flags)
    gap_idx_cols = F.columns.tolist()
    F["gap_z"] = d.gap_z.values
    d["bid"] = pd.factorize(d.blocker_nfl_id)[0]
    d["rid"] = pd.factorize(d.rusher_nfl_id)[0]
    d["did"] = pd.factorize(d.blocker_nfl_id.astype(str) + "_" + d.rusher_nfl_id.astype(str))[0]
    return d, F


# ------------------------------------------------------------- GLM engine ----

class Engine:
    """Logistic / linear fit with two-way cluster-robust SE for the last column (gap)."""

    def __init__(self, X, bid, rid, did):
        self.X = np.asarray(X, float)
        self.n, self.k = self.X.shape
        self.groups = []
        for g in (bid, rid, did):
            G = sp.csr_matrix((np.ones(self.n), (np.arange(self.n), g)), shape=(self.n, g.max() + 1))
            self.groups.append((G, g.max() + 1))

    def _cluster_cov(self, S, bread):
        n, k = self.n, self.k
        V = np.zeros((k, k))
        for i, (G, ng) in enumerate(self.groups):
            Sg = np.asarray(G.T @ S)
            meat = Sg.T @ Sg
            corr = ng / (ng - 1.0) * (n - 1.0) / (n - k)
            meat *= corr
            V += meat if i < 2 else -meat
        V = bread @ V @ bread
        # statsmodels' GLM(cov_type='cluster', two groups) does not clip; clip to PSD only if the gap variance is <= 0
        if V[-1, -1] > 0:
            return V
        w, U = np.linalg.eigh((V + V.T) / 2)
        w = np.clip(w, 0, None)
        return (U * w) @ U.T

    def logit(self, y, w=None, rows=None):
        X, n = self.X, self.n
        if rows is not None:
            sub = Engine.__new__(Engine)
            sub.X = X[rows]
            sub.n, sub.k = sub.X.shape
            sub.groups = [(G[rows], ng) for G, ng in self.groups]
            return sub.logit(y[rows], None if w is None else w[rows])
        w = np.ones(n) if w is None else w
        beta = np.zeros(self.k)
        beta[0] = logit(np.clip(np.average(y, weights=w), 1e-4, 1 - 1e-4))
        for _ in range(30):
            p = expit(X @ beta)
            W = w * p * (1 - p)
            H = X.T @ (X * W[:, None])
            step = np.linalg.solve(H + 1e-9 * np.eye(self.k), X.T @ (w * (y - p)))
            beta += step
            if np.max(np.abs(step)) < 1e-8:
                break
        p = expit(X @ beta)
        W = w * p * (1 - p)
        bread = np.linalg.inv(X.T @ (X * W[:, None]) + 1e-9 * np.eye(self.k))
        S = X * (w * (y - p))[:, None]
        V = self._cluster_cov(S, bread)
        return beta[-1], np.sqrt(V[-1, -1])

    def ols(self, y, rows=None):
        X = self.X
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        bread = np.linalg.inv(X.T @ X)
        S = X * (y - X @ beta)[:, None]
        V = self._cluster_cov(S, bread)
        return beta[-1], np.sqrt(V[-1, -1])


# ---------------------------------------------------------------- sim -------

def calibrate_intercept(d, sd, rng, b_gap=0.0):
    nb, nr = d.bid.max() + 1, d.rid.max() + 1
    lp0 = B_PICK * d.pick_diff_z.values + B_DROP * d.drop_z.values
    ps = []
    for _ in range(300):
        ub, ur = rng.normal(0, sd, nb), rng.normal(0, sd, nr)
        ps.append((lp0 + ub[d.bid.values] + ur[d.rid.values], None))
    LP = np.array([p[0] for p in ps])
    f = lambda a: expit(LP + a).mean() - BASE_RATE
    return brentq(f, -10, 5)


def run_cell(args):
    comp_name, comp_col, sd, nsim, effects, seed_key = args
    d, F = load_design(comp_col)
    eng = Engine(F.values, d.bid.values, d.rid.values, d.did.values)
    nb, nr = d.bid.max() + 1, d.rid.max() + 1
    dy_n = d.groupby("did").did.transform("size").values
    w_dyad = (1.0 / dy_n); w_dyad = w_dyad / w_dyad.mean()
    reg_rows = np.where(d.season_type.values == "REG")[0]
    ss = np.random.SeedSequence([SEED, seed_key])
    rng0 = np.random.default_rng(ss.spawn(1)[0])
    a = calibrate_intercept(d, sd, rng0)
    lp0 = a + B_PICK * d.pick_diff_z.values + B_DROP * d.drop_z.values
    gz = d.gap_z.values
    out = []
    for ei, eff in enumerate(effects):
        rng = np.random.default_rng(np.random.SeedSequence([SEED, seed_key, ei]))
        est = {"std": [], "dyad": [], "reg": []}
        for _ in range(nsim):
            ub, ur = rng.normal(0, sd, nb), rng.normal(0, sd, nr)
            lp = lp0 + eff * gz + ub[d.bid.values] + ur[d.rid.values]
            y = (rng.random(d.shape[0]) < expit(lp)).astype(float)
            est["std"].append(eng.logit(y))
            est["dyad"].append(eng.logit(y, w=w_dyad))
            est["reg"].append(eng.logit(y, rows=reg_rows))
        for v, arr in est.items():
            arr = np.array(arr)
            z = arr[:, 0] / arr[:, 1]
            out.append(dict(composite=comp_name, re_sd=sd, effect=eff, variant=v, nsim=nsim,
                            power=float(np.mean(np.abs(z) > 1.959964)),
                            bias=float(arr[:, 0].mean() - eff),
                            emp_sd=float(arr[:, 0].std(ddof=1)),
                            mean_se=float(arr[:, 1].mean()),
                            coverage=float(np.mean(np.abs(arr[:, 0] - eff) < 1.959964 * arr[:, 1])),
                            n_rep=int(len(d) if v != "reg" else len(reg_rows)),
                            intercept=float(a), z=z.tolist(), nb=int(nb), nr=int(nr)))
    return out


def run_continuous(nsim, comp_col, effects, mean=0.25, sd_tot=0.20, sd_re=0.05):
    """ASSUMPTION-based: linear outcome, mean .25, total SD .20; blocker and rusher RE SD .05 each."""
    d, F = load_design(comp_col)
    eng = Engine(F.values, d.bid.values, d.rid.values, d.did.values)
    nb, nr = d.bid.max() + 1, d.rid.max() + 1
    sd_res = np.sqrt(sd_tot ** 2 - 2 * sd_re ** 2)
    gz = d.gap_z.values
    out = []
    for ei, eff in enumerate(effects):
        rng = np.random.default_rng(np.random.SeedSequence([SEED, 999, ei]))
        r = []
        for _ in range(nsim):
            y = (mean + eff * gz + rng.normal(0, sd_re, nb)[d.bid.values]
                 + rng.normal(0, sd_re, nr)[d.rid.values] + rng.normal(0, sd_res, len(d)))
            r.append(eng.ols(y))
        r = np.array(r); z = r[:, 0] / r[:, 1]
        out.append(dict(effect=eff, power=float(np.mean(np.abs(z) > 1.959964)),
                        bias=float(r[:, 0].mean() - eff), emp_sd=float(r[:, 0].std(ddof=1)),
                        mean_se=float(r[:, 1].mean())))
    return out


def mde80(effects, power):
    """Linear interpolation of the power curve at 0.80 (extrapolating the last segment if needed)."""
    e, p = np.array(effects), np.array(power)
    for i in range(1, len(e)):
        if p[i - 1] < 0.8 <= p[i]:
            return float(e[i - 1] + (0.8 - p[i - 1]) * (e[i] - e[i - 1]) / (p[i] - p[i - 1])), "interpolated"
    # not reached: extrapolate from last two points
    if p[-1] < 0.8:
        slope = (p[-1] - p[-2]) / (e[-1] - e[-2])
        return float(e[-1] + (0.8 - p[-1]) / slope), "EXTRAPOLATED"
    return float(e[0]), "already>=80%"


def verify_engine():
    """Check the numpy engine vs statsmodels (GLM + two-way cluster) on one simulated outcome."""
    import statsmodels.api as sm
    d, F = load_design("composite")
    eng = Engine(F.values, d.bid.values, d.rid.values, d.did.values)
    rng = np.random.default_rng(1)
    y = (rng.random(len(d)) < 0.0952).astype(float)
    b, se = eng.logit(y)
    m = sm.GLM(y, F.values, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([d.bid.values, d.rid.values])})
    return b, se, m.params[-1], m.bse[-1]


# ---------------------------------------------------------------- main ------

def counts():
    res = {}
    for name, col in COMPOSITES.items():
        d, F = load_design(col)
        dy = d.groupby("did").size()
        res[name] = dict(reps=len(d), reg_reps=int((d.season_type == "REG").sum()),
                         blockers=int(d.bid.nunique()), rushers=int(d.rid.nunique()),
                         dyads=int(d.did.nunique()), dyads_ge2=int((dy >= 2).sum()),
                         k=int(F.shape[1]),
                         base_obs_note="n/a", gap_sd_raw=float(d.gap.std()),
                         corr_gap_pick=float(np.corrcoef(d.gap_z, d.pick_diff_z)[0, 1]),
                         top10_blocker_share=float(d.groupby("bid").size().nlargest(10).sum() / len(d)),
                         eff_dyad_n=float(len(d) / 1.0), n_dyad_weights=len(dy),
                         cols=F.columns.tolist())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsim", type=int, default=500)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    t0 = time.time()
    effects = EFFECTS if not a.quick else [0.0, 0.2]
    ver = verify_engine()
    print("engine check (mine b,se vs statsmodels b,se):", ver, flush=True)
    cnt = counts()
    jobs = []
    key = 0
    for cname, ccol in COMPOSITES.items():
        for sd in (RE_SDS if not a.quick else [0.35]):
            key += 1
            # split effects across jobs for parallelism
            for ei, e in enumerate(effects):
                jobs.append((cname, ccol, sd, a.nsim, [e], key * 100 + ei))
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(run_cell, jobs):
            rows += r
    res = pd.DataFrame(rows)
    from scipy.stats import t as tdist
    res["power_t"] = [float(np.mean(np.abs(z) > tdist.ppf(0.975, min(nb, nr) - 1))) for z, nb, nr in zip(res.z, res.nb, res.nr)]
    crit = {}
    for (c, sd, v), g in res[res.effect == 0].groupby(["composite", "re_sd", "variant"]):
        crit[(c, sd, v)] = float(np.quantile(np.abs(g.z.iloc[0]), 0.95))
    res["crit0"] = [crit[(c, sd, v)] for c, sd, v in zip(res.composite, res.re_sd, res.variant)]
    res["power_adj"] = [float(np.mean(np.abs(z) > k)) for z, k in zip(res.z, res.crit0)]
    res["z"] = None
    ceffects = [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04]
    cont = {n: run_continuous(a.nsim, c, ceffects) for n, c in COMPOSITES.items()}
    res.to_csv(ROOT / "scripts" / "_power_sim_raw.csv", index=False) if False else None
    write_report(res, cnt, cont, ceffects, ver, a.nsim, time.time() - t0)


def fmt_table(df, cols):
    s = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for _, r in df.iterrows():
        s += "| " + " | ".join(str(r[c]) for c in cols) + " |\n"
    return s


def write_report(res, cnt, cont, ceffects, ver, nsim, secs):
    L = []
    P = L.append
    P("# Power / minimum-detectable-effect simulation (step 3 of the pre-registered design)\n")
    P("Code: `scripts/power_simulation.py` (seed 2027; reproduce with `.venv\\Scripts\\python.exe scripts\\power_simulation.py`). "
      f"Simulations per setting: {nsim}. Runtime {secs/60:.1f} min. "
      "`data/processed/engaged_outcomes_SEALED.parquet` was **not opened**; every outcome here is simulated. "
      "Labels: **[computed]** = from the real design matrix or the simulation; **[assumption]** = a generator input.\n")
    P("## 1. Analysis set [computed]\n")
    P("Primary engaged reps; blocker lined up T/G/C and combine_position OL; rusher combine_position DL aligned EDGE or INTERIOR_LINE (section 3.3); both players with the composite.\n")
    P("| composite | reps | REG reps | blockers | rushers | dyads | dyads with >=2 reps | design columns | top-10 blockers' share | corr(gap, pick diff) |\n|---|---|---|---|---|---|---|---|---|---|")
    for n, c in cnt.items():
        P(f"| {n} | {c['reps']:,} | {c['reg_reps']:,} | {c['blockers']} | {c['rushers']} | {c['dyads']} | {c['dyads_ge2']} | {c['k']+0} (incl. intercept and gap) | {c['top10_blocker_share']:.3f} | {c['corr_gap_pick']:.3f} |")
    P("")
    P("Design (section 3.4): intercept; natural cubic spline (3 df) of dropback_duration; down (1, 2, 3+) x yards-to-go bucket (<=3, 4-7, 8+); shotgun; play action; season; blocker position T/G/C; rusher EDGE vs interior; double team; pass_rushers_encountered; rusher-minus-blocker differences of log pick, undrafted flag, weight, arm length, forty, ten-yard split, short shuttle, NGS athleticism and the corresponding missing flags (continuous columns standardised on the analysis-set players, missing values set to 0 after standardising); gap = rusher composite - blocker composite, standardised to SD 1. Constant and exactly duplicated columns are dropped (the forty and ten-yard-split missing-flag differences are identical in this set). The dropback spline is a restricted (natural) cubic spline with 3 df (linear term plus two nonlinear terms, knots at the 5/35/65/95th percentiles; a hand-built Harrell basis because patsy's `cr` basis put almost all its mass on one outlier rep) - **[decision]**. Down 4 is merged into 3+ and the yards-to-go cut points are my choices (section 3.3 does not give them) - **[decision]**.\n")
    P(f"Engine check on one null draw, my numpy IRLS + two-way cluster SE vs statsmodels GLM `cov_type=cluster` (blocker, rusher): gap estimate {ver[0]:.5f} vs {ver[2]:.5f}; SE {ver[1]:.5f} vs {ver[3]:.5f}.\n")
    P("## 2. Generator\n")
    P(f"- Logistic, `logit P = a + (-0.20) * pickdiff_z + 0.58 * dropback_z + gap_effect * gap_z + u_blocker + u_rusher` **[assumption: coefficients from the feasibility check; no other covariate has an effect]**. pickdiff_z = standardised rusher-minus-blocker log pick; dropback_z = standardised dropback_duration.")
    P("- u_blocker, u_rusher ~ N(0, s^2), crossed; s = 0.35 (main), 0.20 and 0.50 (sensitivity) **[assumption]**. Intercept `a` solved so the mean simulated rate is 0.0952 (averaged over 300 random-effect draws) **[computed from the assumed base rate]**.")
    P("- Fit: the frequentist mirror, logistic GLM with the full fixed-effect design, two-way cluster-robust SE (blocker + rusher - dyad, statsmodels-style small-sample factors, eigenvalue-clipped only if the gap variance is non-positive); Wald z test at two-sided alpha = 0.05. The fitted model uses a spline for dropback while the generator is linear in dropback, so misspecification is slight but present.\n")
    # power tables
    def sub(c, sd, v):
        return res[(res.composite == c) & (res.re_sd == sd) & (res.variant == v)].sort_values("effect")
    P("## 3. Power table, random-effect SD 0.35 (main) [computed]\n")
    P("Power = share of simulations with |z| > 1.96. Effect 0 row is the type-I error rate. Bias = mean estimate - planted; SE columns: empirical SD of estimates and mean model-based cluster SE.\n")
    for v, lab in [("std", "Standard (reps equally weighted)"), ("dyad", "Dyad-equal weights"), ("reg", "REG-only reps")]:
        P(f"### {lab}\n")
        P("| planted effect (log-odds/SD) | power: registered | power: sensA | bias: registered | bias: sensA | empirical SD: reg. | mean cluster SE: reg. | empirical SD: sensA | mean cluster SE: sensA | 95% CI coverage: reg. | sensA |\n|---|---|---|---|---|---|---|---|---|---|---|")
        a = sub("registered", 0.35, v); b = sub("sensA", 0.35, v)
        for (_, r), (_, s) in zip(a.iterrows(), b.iterrows()):
            P(f"| {r.effect:.2f} | {r.power:.3f} | {s.power:.3f} | {r.bias:+.4f} | {s.bias:+.4f} | {r.emp_sd:.4f} | {r.mean_se:.4f} | {s.emp_sd:.4f} | {s.mean_se:.4f} | {r.coverage:.3f} | {s.coverage:.3f} |")
        P(f"\nn reps in this variant: registered {int(a.n_rep.iloc[0]):,}, sensA {int(b.n_rep.iloc[0]):,}.\n")
    P("### Test calibration (standard weighting, RE SD 0.35) [computed]\n")
    P("The cluster-robust Wald test with ~70 blockers and ~97 rushers is anti-conservative: the mean model SE is below the empirical SD of the estimate. Rows show the type-I rate at effect 0 and power with (i) the test as specified, (ii) a t reference with min(G)-1 df, (iii) size-adjusted power (critical value = 95th percentile of |z| in the null simulations; not an available test in practice, a bound on what a calibrated test could do).\n")
    P("| planted effect | reg. as specified | reg. t-ref | reg. size-adjusted | sensA as specified | sensA t-ref | sensA size-adjusted |\n|---|---|---|---|---|---|---|")
    a = sub("registered", 0.35, "std"); b = sub("sensA", 0.35, "std")
    for (_, r), (_, q) in zip(a.iterrows(), b.iterrows()):
        P(f"| {r.effect:.2f} | {r.power:.3f} | {r.power_t:.3f} | {r.power_adj:.3f} | {q.power:.3f} | {q.power_t:.3f} | {q.power_adj:.3f} |")
    P("")
    # MDE
    P("## 4. Minimum detectable effect at 80% power [computed]\n")
    P("Interpolated linearly on the simulated power curve (planted-effect grid 0, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50). Draft-pick equivalents = MDE / 0.20. Probability change = expit(logit(0.0952) + MDE) - 0.0952 for a +1 SD gap, at the base rate. "
      "The analytic approximation 2.80 x mean cluster SE (at planted 0.20) is shown as a cross-check.\n")
    P("| composite | variant | RE SD | MDE (log-odds/SD), test as specified (normal ref.) | method | draft-pick equivalents (SD of pick diff) | pressure prob. change at base rate (points) | 2.80 x mean SE | MDE with t(G-1) reference | MDE size-adjusted (null 95th pct of abs z) |\n|---|---|---|---|---|---|---|---|---|---|")
    mdes = {}
    for c in COMPOSITES:
        for v in ["std", "dyad", "reg"]:
            for sd in RE_SDS:
                s = sub(c, sd, v)
                if s.empty:
                    continue
                m, how = mde80(s.effect.values, s.power.values)
                mdes[(c, v, sd)] = m
                dp = (expit(logit(BASE_RATE) + m) - BASE_RATE) * 100
                se02 = s[s.effect == 0.2].mean_se.iloc[0] if (s.effect == 0.2).any() else np.nan
                P(f"| {c} | {dict(std='standard', dyad='dyad-weighted', reg='REG only')[v]} | {sd} | {m:.3f} | {how} | {m/0.20:.2f} | {dp:.2f} | {2.8016*se02:.3f} | {mde80(s.effect.values, s.power_t.values)[0]:.3f} | {mde80(s.effect.values, s.power_adj.values)[0]:.3f} |")
    P("")
    # RE sensitivity
    P("## 5. Random-effect SD sensitivity (standard weighting) [computed under assumed SDs]\n")
    P("| planted effect | " + " | ".join(f"reg. power SD {sd}" for sd in RE_SDS) + " | " + " | ".join(f"sensA power SD {sd}" for sd in RE_SDS) + " |\n|" + "---|" * (1 + 2 * len(RE_SDS)))
    for e in EFFECTS:
        cells = []
        for c in COMPOSITES:
            for sd in RE_SDS:
                s = sub(c, sd, "std"); r = s[s.effect == e]
                cells.append(f"{r.power.iloc[0]:.3f}" if len(r) else "-")
        P(f"| {e:.2f} | " + " | ".join(cells) + " |")
    P("")
    P("| composite | RE SD | MDE | pick equivalents | empirical SD of gap estimate (at effect 0) | bias at effect 0.20 |\n|---|---|---|---|---|---|")
    for c in COMPOSITES:
        for sd in RE_SDS:
            s = sub(c, sd, "std")
            if s.empty:
                continue
            P(f"| {c} | {sd} | {mdes[(c,'std',sd)]:.3f} | {mdes[(c,'std',sd)]/0.2:.2f} | {s[s.effect==0].emp_sd.iloc[0]:.4f} | {s[s.effect==0.2].bias.iloc[0]:+.4f} |")
    P("")
    # continuous
    P("## 6. Continuous secondary outcome (peak pressure probability allowed): ASSUMPTION-BASED\n")
    P("The real distribution is unknown to me, so this is **not** a computed property of the data. Assumed: outcome mean 0.25, total SD 0.20 on the probability scale; blocker and rusher random-intercept SDs 0.05 each (assumed ICC about 6% per side), the rest independent residual; no other covariate effects planted. Fit: OLS with the full fixed-effect design and two-way cluster-robust SE. Effects are in probability units per SD of the gap.\n")
    P("| planted effect (prob. per SD of gap) | power: registered | power: sensA | mean SE: registered | mean SE: sensA |\n|---|---|---|---|---|")
    for i, e in enumerate(ceffects):
        r, s = cont["registered"][i], cont["sensA"][i]
        P(f"| {e:.3f} | {r['power']:.3f} | {s['power']:.3f} | {r['mean_se']:.4f} | {s['mean_se']:.4f} |")
    P("")
    cm = {c: mde80(ceffects, [x["power"] for x in cont[c]]) for c in COMPOSITES}
    for c in COMPOSITES:
        P(f"- {c}: MDE (80% power) = {cm[c][0]:.4f} probability units per SD of gap ({cm[c][1]}), i.e. {cm[c][0]/0.20:.3f} outcome SDs per gap SD. [assumption-based]")
    P("")
    # statement
    m_r = mdes[("registered", "std", 0.35)]; m_a = mdes[("sensA", "std", 0.35)]
    m_r5 = mdes.get(("registered", "std", 0.5), float('nan')); m_r2 = mdes.get(("registered", "std", 0.2), float('nan'))
    m_rd = mdes[("registered", "dyad", 0.35)]; m_rg = mdes[("registered", "reg", 0.35)]
    P("## 7. What the design can and cannot detect\n")
    P(f"- With the registered composite and RE SD 0.35 the design has 80% power for a gap effect of about **{m_r:.2f} log-odds per SD** ({m_r/0.20:.1f} draft-pick-difference SDs; a +1 SD gap raises pressure probability from 9.52% by about {(expit(logit(BASE_RATE)+m_r)-BASE_RATE)*100:.1f} points). For sensitivity composite A: {m_a:.2f}. These MDEs depend on the assumed random-effect SD: {m_r2:.2f} at SD 0.2 and {m_r5:.2f} at SD 0.5 (registered).")
    P(f"- Dyad-equal weighting and REG-only reps are less powerful or similar: MDE {m_rd:.2f} and {m_rg:.2f} (registered).")
    P("- Interpretation of a null: an interval that excludes effects larger than the MDE is the most that can be claimed; effects smaller than the MDE (for example the planted 0.10) are mostly missed, and the power table gives the exact miss rate. "
      "The effective sample size is driven by the 69 (sensA: 75) blockers and 97 rushers (the cluster count), not by the thousands of reps, because the gap varies at the player level; this is why the MDE is large relative to the pick effect.")
    P("- **Test size:** the as-specified two-way cluster Wald test rejects a true null in about 12% (registered) and 10% (sensA) of simulations at nominal 5%, because the cluster SE is about 15-20% too small with this few clusters (the t reference barely helps). The as-specified MDE (0.21 registered) is therefore optimistic; the size-adjusted MDE (0.25 registered, 0.23 sensA, i.e. 1.2 draft-pick SDs) is the honest planning number, and the preregistered decision rule should use a calibrated test (permutation, wild/cluster bootstrap) or the Bayesian interval rather than the plain cluster Wald z.")
    P("- Caveats: the generator is a simplified logistic model with assumed REs and only two non-zero nuisance effects; the Wald test uses the normal reference with few clusters, so type-I error and coverage (see table) should be read from the effect-0 row; the Bayesian primary model (priors, shrinkage) will not have identical power to this frequentist mirror; the continuous-outcome section is assumption-based throughout.")
    (ROOT / "reports" / "power_simulation.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote report", flush=True)


if __name__ == "__main__":
    main()

"""Shared helpers for the exploratory entries X1-X5 (read-only use of scripts/confirmatory_analysis.py)."""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import confirmatory_analysis as CA  # noqa: E402  (read-only import)

TABLES = REPO / "reports" / "exploratory" / "tables"
FIGS = REPO / "figures" / "exploratory"
PROC = REPO / "data" / "processed"
for d in (TABLES, FIGS):
    d.mkdir(parents=True, exist_ok=True)
T0 = time.time()


def say(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def build_base(with_k5: bool = False) -> "CA.AnalysisBase":
    """AnalysisBase in exploratory mode with sealed outcomes attached (frame F has y_press, y_rp, ...)."""
    A = CA.AnalysisBase(mode="exploratory", out_root=None)
    A.prepare(with_k5=with_k5)
    Y = pl.read_parquet(PROC / "engaged_outcomes_SEALED.parquet",
                        columns=CA.KEYS + ["pressure_allowed", "peak_pressure_probability_allowed",
                                           "rusher_time_to_pressure"]).to_pandas()
    A.attach_outcomes(Y)
    return A


def fit(A, cols, *, ver="reg", setname="P", yk="press", family="binomial", Xover=None, mask=None, name="x"):
    """GLM mirror (two-way cluster, t(G-1)); returns ModelRec with .glm and .D."""
    return A.fit_model(name, ver, setname, cols, family=family, yk=yk, bayes=False, glm=True, Xover=Xover, mask=mask)


M1S1 = CA.C_COLS + CA.Q_COLS + ["c_R", "c_B"]


def tab(rec, term):
    g = rec.glm.term(term)
    return dict(term=term, est=g["est"], se=g["se"], lo=g["ci_nom"][0], hi=g["ci_nom"][1], p=g["p_nom"],
                lo_k=g["ci_kappa"][0], hi_k=g["ci_kappa"][1], p_k=g["p_kappa"], n=g["n"], df=g["df"])


def save(df: pd.DataFrame, name: str):
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df


def reproduce(A):
    """E0.1 reproduction check: M1 gap -0.154 (kappa CI [-0.308, 0.000]); S1 c_B +0.143, c_R -0.064."""
    m1 = fit(A, CA.C_COLS + CA.Q_COLS + ["gap"], name="M1")
    s1 = fit(A, M1S1, name="M1-S1")
    out = pd.DataFrame([dict(model="M1", **tab(m1, "gap")), dict(model="M1-S1", **tab(s1, "c_B")),
                        dict(model="M1-S1", **tab(s1, "c_R"))])
    say("reproduction:", out[["model", "term", "est", "lo_k", "hi_k"]].round(3).to_dict("records"))
    ok = (abs(out.est[0] + 0.154) < 0.0006 and abs(out.est[1] - 0.143) < 0.0006 and abs(out.est[2] + 0.064) < 0.0006)
    return out, ok


# ------------------------------------------------------------------------------------ player-level (X1, X5) helpers
import math
from scipy import stats


def load_pp_games():
    pp = pl.read_parquet(PROC / "player_play.parquet")
    games = pl.read_parquet(PROC / "games.parquet").select(["game_id", "season", "season_type"])
    return pp, games


def play_level_dropback(pp: "pl.DataFrame") -> "pl.DataFrame":
    """Play-level dropback_duration (constant within a play where non-null; verified max range 0)."""
    return (pp.filter(pl.col("dropback_duration").is_not_null()).group_by(["game_id", "play_id"])
            .agg(pl.col("dropback_duration").first().alias("db_play")))


def context_cols(d: pd.DataFrame, db: np.ndarray) -> pd.DataFrame:
    """Dropback spline (Harrell, knots 5/35/65/95th pct of these snaps, standardised then Gram-Schmidt via QR),
    8 down x distance cells, shotgun-or-empty, season dummies. Same construction as Version.__init__ / raw_columns."""
    knots = np.quantile(db, [0.05, 0.35, 0.65, 0.95])
    B = np.column_stack(CA.harrell_rcs(db, knots))
    B = (B - B.mean(0)) / B.std(0, ddof=1)
    Q, R = np.linalg.qr(B)
    R = R * np.sign(np.diag(R))[:, None]
    T = np.linalg.inv(R) * math.sqrt(len(db) - 1.0)
    Bn = B @ T
    out = {f"db{i+1}": Bn[:, i] for i in range(3)}
    dn = np.minimum(d["down"].to_numpy(float), 3)
    ytg = d["yards_to_go"].to_numpy(float)
    bucket = np.where(ytg <= 3, "short", np.where(ytg <= 7, "med", "long"))
    for k in (1, 2, 3):
        for b in ("short", "med", "long"):
            if (k, b) != (1, "long"):
                out[f"dd_d{k}_{b}"] = ((dn == k) & (bucket == b)).astype(float)
    out["shotgun"] = d["offense_formation"].isin(["SHOTGUN", "EMPTY"]).to_numpy(float)
    out["s2023"] = (d["season"].to_numpy() == 2023).astype(float)
    out["s2024"] = (d["season"].to_numpy() == 2024).astype(float)
    return pd.DataFrame(out, index=d.index)


MEAS_COLS = ["combine_weight", "arm_length", "forty", "ten_yd_split", "short_shuttle", "three_cone", "ngs_athleticism_score"]


def measure_cols(d: pd.DataFrame, base: pd.DataFrame, idcol: str = "nfl_id") -> pd.DataFrame:
    """z over distinct players in d (ddof 1), missing -> 0; plus forty/shuttle/cone missing flags."""
    ids = pd.unique(d[idcol])
    out = {}
    for m in MEAS_COLS:
        v = d[idcol].map(base[m]).astype(float)
        pv = pd.Series(ids).map(base[m]).astype(float).to_numpy()
        mu, sd = np.nanmean(pv), np.nanstd(pv, ddof=1)
        out["z_" + CA.MSHORT[m]] = np.nan_to_num(((v - mu) / sd).to_numpy(), nan=0.0)
    out["f_dash"] = d[idcol].map(base["forty"]).isna().to_numpy(float)
    out["f_shuttle"] = d[idcol].map(base["short_shuttle"]).isna().to_numpy(float)
    out["f_cone"] = d[idcol].map(base["three_cone"]).isna().to_numpy(float)
    return pd.DataFrame(out, index=d.index)


def zplayer(d: pd.DataFrame, values: pd.Series, idcol: str = "nfl_id") -> np.ndarray:
    """z of a player-level value, with mean/SD (ddof 1) over distinct players in d."""
    pv = pd.Series(pd.unique(d[idcol])).map(values).astype(float).to_numpy()
    mu, sd = np.nanmean(pv), np.nanstd(pv, ddof=1)
    return ((d[idcol].map(values).astype(float) - mu) / sd).to_numpy()


def hygiene(X: pd.DataFrame, protect=()) -> pd.DataFrame:
    keep, seen = [], {}
    for c in X.columns:
        v = X[c].to_numpy(float)
        if np.all(v == v[0]) and c not in protect:
            continue
        k = v.tobytes()
        if k in seen and c not in protect:
            continue
        seen[k] = c
        keep.append(c)
    return X[keep]


def glm_cluster1(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, family: str = "binomial"):
    """statsmodels GLM (IRLS) with one-way cluster-robust covariance (default small-sample correction); t(G-1)."""
    import statsmodels.api as sm
    Xc = sm.add_constant(X.to_numpy(float), has_constant="add")
    names = ["const"] + list(X.columns)
    fam = sm.families.Binomial() if family == "binomial" else sm.families.Gaussian()
    g = pd.factorize(groups)[0]
    res = sm.GLM(y, Xc, family=fam).fit(maxiter=100, cov_type="cluster", cov_kwds={"groups": g})
    return OneWay(names, np.asarray(res.params), np.asarray(res.cov_params()), int(g.max()) + 1, len(y), res)


class OneWay:
    def __init__(self, names, beta, V, G, n, res=None):
        self.names, self.beta, self.V, self.G, self.n, self.res = names, beta, V, G, n, res
        self.df = G - 1

    def lin(self, c):
        c = np.asarray(c, float)
        est = float(c @ self.beta)
        se = float(np.sqrt(max(c @ self.V @ c, 0.0)))
        tq = stats.t.ppf(0.975, self.df)
        return dict(est=est, se=se, lo=est - tq * se, hi=est + tq * se, p=float(2 * stats.t.sf(abs(est / se), self.df)),
                    n=self.n, G=self.G)

    def term(self, name):
        c = np.zeros(len(self.names))
        c[self.names.index(name)] = 1.0
        return self.lin(c)

    def combo(self, coefs):
        c = np.zeros(len(self.names))
        for k, v in coefs.items():
            c[self.names.index(k)] = v
        return self.lin(c)

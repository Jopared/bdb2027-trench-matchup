#!/usr/bin/env python
"""X3: what the mirror-drill (O3) blocker trait measures. All GLMs on set P with the M1-S1 base
(C_COLS + Q_COLS + [c_R, c_B]), two-way cluster SE, t(G-1). Deterministic (no random numbers)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd, polars as pl
from scipy import stats
import _common as C
from _common import CA, say, PROC

BASE = CA.C_COLS + CA.Q_COLS


def row(label, rec, term, extra=None):
    d = C.tab(rec, term)
    d.update(fit=label, n_blockers=rec.D.nb, n_rushers=rec.D.nr)
    if extra:
        d.update(extra)
    return d


def main():
    A = C.build_base(with_k5=True)
    rep, ok = C.reproduce(A)
    C.save(rep, "x3_reproduction")
    say("reproduction ok:", ok)
    F, V = A.F, A.V["reg"]
    tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas().set_index("nfl_id")
    P = A.S["P"]
    ids_P = pd.unique(F.blocker_nfl_id[P])
    rows = []

    # ---- (a) quantised O3
    o3 = F.blocker_nfl_id.map(tr["O3_value"]).astype(float).to_numpy()
    cnt = pd.Series(tr.loc[ids_P, "O3_value"].round(2)).value_counts().sort_index()
    C.save(cnt.rename_axis("O3_value_s").reset_index(name="blockers_in_P"), "x3_O3_value_counts")
    say("O3 values among in-P blockers:", cnt.to_dict())
    X = V.X.copy()
    X["fast"] = (o3 <= 0.45 + 1e-9).astype(float)
    X["slow"] = (o3 >= 0.55 - 1e-9).astype(float)
    X.loc[np.isnan(o3), ["fast", "slow"]] = np.nan
    ra = C.fit(A, BASE + ["c_R", "fast", "slow"], Xover=X, name="X3a")
    nrep = {k: int(((X[k] == 1) & P).sum()) for k in ("fast", "slow")}
    nblk = {k: int(F.blocker_nfl_id[(X[k] == 1) & P].nunique()) for k in ("fast", "slow")}
    for t in ("fast", "slow"):
        rows.append(row(f"(a) quantised O3: {t} vs 0.50 s", ra, t, dict(reps_in_level=nrep[t], blockers_in_level=nblk[t])))
    rows.append(row("(a) quantised O3: c_R", ra, "c_R"))
    est_f, est_s = ra.glm.term("fast")["est"], ra.glm.term("slow")["est"]
    # for reference: c_B in the same sample
    rb0 = C.fit(A, BASE + ["c_R", "c_B"], name="X3a_ref")
    rows.append(row("(a-ref) c_B in M1-S1", rb0, "c_B"))
    monotone = (est_f > 0 > est_s) or (est_f < 0 < est_s)
    cB_est = rb0.glm.term("c_B")["est"]
    r_a = ("(a) fast contrast same sign as c_B (%s) and effect %s monotone across the three levels -> %s"
           % ("yes" if np.sign(est_f) == np.sign(cB_est) else "no", "is" if monotone else "is NOT",
              "'carried by a one-frame difference in a single 10 Hz rep'" if (np.sign(est_f) == np.sign(cB_est) and not monotone)
              else "reading not triggered"))

    # ---- (b) number of reversals
    ns = F.blocker_nfl_id.map(tr["O3_n_slots"]).astype(float)
    mu, sd = np.nanmean(tr.loc[ids_P, "O3_n_slots"]), np.nanstd(tr.loc[ids_P, "O3_n_slots"], ddof=1)
    X2 = V.X.copy()
    X2["z_nslots"] = ((ns - mu) / sd).to_numpy()
    rbb = C.fit(A, BASE + ["c_R", "c_B", "z_nslots"], Xover=X2, name="X3b")
    r_cn = float(np.corrcoef(X2.c_B[P], X2.z_nslots[P])[0, 1])
    rows.append(row("(b) c_B + z(O3_n_slots)", rbb, "c_B", dict(r_cB_nslots_rep_level=r_cn)))
    rows.append(row("(b) c_B + z(O3_n_slots)", rbb, "z_nslots"))
    rows.append(row("(b) c_B + z(O3_n_slots)", rbb, "c_R"))
    pl_n = tr.loc[ids_P, "O3_n_slots"]
    C.save(pl_n.describe().rename("O3_n_slots_in_P").reset_index(), "x3_nslots_summary")

    # ---- (c) k3 and k5 jointly
    k5 = A.V["k5"]
    X3 = V.X.copy()
    X3["c_B5"] = k5.X["c_B"].to_numpy()
    X3["c_R5"] = k5.X["c_R"].to_numpy()
    rc = C.fit(A, BASE + ["c_R", "c_B", "c_B5"], Xover=X3, name="X3c")
    rows.append(row("(c) k3 and k5 blocker composites jointly", rc, "c_B"))
    rows.append(row("(c) k3 and k5 blocker composites jointly", rc, "c_B5"))
    rk5 = C.fit(A, BASE + ["c_R", "c_B5"], Xover=X3, name="X3c5")
    rows.append(row("(c-ref) k5 composite alone (E0.4)", rk5, "c_B5"))
    # VIF
    Dm = rc.D
    Xf = np.column_stack([np.ones(Dm.n), Dm.X])
    vifs = {}
    for t in ("c_B", "c_B5"):
        j = Dm.names.index(t) + 1
        oth = np.delete(Xf, j, axis=1)
        coef = np.linalg.lstsq(oth, Xf[:, j], rcond=None)[0]
        r2 = 1 - np.sum((Xf[:, j] - oth @ coef) ** 2) / np.sum((Xf[:, j] - Xf[:, j].mean()) ** 2)
        vifs[t] = 1 / (1 - r2)
    rr = float(np.corrcoef(Dm.col("c_B"), Dm.col("c_B5"))[0, 1])
    vif = pd.DataFrame([dict(vif_cB_k3_full_design=vifs["c_B"], vif_cB_k5_full_design=vifs["c_B5"], rep_level_r_k3_k5=rr,
                             vif_pair_only=1 / (1 - rr ** 2))])
    C.save(vif, "x3_vif")
    say(vif.round(3).to_string())
    e3, e5 = rc.glm.term("c_B"), rc.glm.term("c_B5")
    r_c = ("(c) k3 part %+.3f [%.3f, %.3f], k5 part %+.3f [%.3f, %.3f] -> %s" %
           (e3["est"], e3["ci_nom"][0], e3["ci_nom"][1], e5["est"], e5["ci_nom"][0], e5["ci_nom"][1],
            "'smoothing-specific, consistent with measurement noise'" if (e3["est"] > 0 and e5["est"] <= 0)
            else "reading not triggered (not [k3 > 0 and k5 <= 0])"))

    # ---- (e) in-game set depth (Gaussian, outcome standardised inside fit_model)
    for col, nm in (("blocker_back_disp_05s", "y_d05"), ("blocker_back_disp_10s", "y_d10")):
        A.F[nm] = F[col].astype(float).to_numpy()
    A.y_of = lambda yk, A=A: A.F[yk].to_numpy(float)
    e_rows = []
    for nm, lab in (("y_d05", "0.5 s"), ("y_d10", "1.0 s")):
        re_ = A.fit_model("X3e_" + nm, "reg", "P", BASE + ["c_R", "c_B"], family="gaussian", yk=nm, bayes=False)
        d = C.tab(re_, "c_B")
        d.update(fit=f"(e) Gaussian, blocker_back_disp_{lab.replace(' s','').replace('.','')}s".replace("05s", "05s"),
                 outcome=nm, ybar=re_.meta["ybar"], ysd=re_.meta["ysd"], n_blockers=re_.D.nb, n_rushers=re_.D.nr,
                 est_yards=d["est"] * re_.meta["ysd"], lo_yards=d["lo"] * re_.meta["ysd"], hi_yards=d["hi"] * re_.meta["ysd"],
                 n_dropped_y_null=re_.meta["dropped_y_null"])
        e_rows.append(d)
        rows.append(d)
    e05 = e_rows[0]
    r_e = ("(e) 0.5 s: %+.4f outcome SD [%.4f, %.4f] (kappa CI [%.4f, %.4f]) -> %s" %
           (e05["est"], e05["lo"], e05["hi"], e05["lo_k"], e05["hi_k"],
            "'the trait shows no transfer to in-game set depth'" if (abs(e05["est"]) < 0.05 and e05["lo"] > -0.10 and e05["hi"] < 0.10)
            else "reading not triggered (not |est| < 0.05 with CI inside +-0.10)"))
    e10 = e_rows[1]
    r_e10 = ("(e) 1.0 s: %+.4f outcome SD [%.4f, %.4f] -> %s" %
             (e10["est"], e10["lo"], e10["hi"],
              "no transfer" if (abs(e10["est"]) < 0.05 and e10["lo"] > -0.10 and e10["hi"] < 0.10) else "rule not met"))

    res = pd.DataFrame(rows)
    C.save(res, "x3_glm_fits")
    show = res[["fit", "term", "est", "lo", "hi", "lo_k", "hi_k", "p", "n"]]
    say(show.round(4).to_string())

    # ---- (d) player level correlates of O3_value among OL with an O3 value
    cr = pl.read_parquet(PROC / "combine_results.parquet").to_pandas().set_index("nfl_id")
    ol = tr[(tr.combine_position == "OL") & tr.O3_value.notna()].copy()
    for c in ("three_cone", "short_shuttle", "ngs_athleticism_score", "combine_weight", "arm_length", "ngs_college_production_score"):
        ol[c] = cr.loc[ol.index, c].astype(float)
    ol["draft_year_"] = ol["draft_year"].astype(float)
    drows = []
    for c in ("three_cone", "short_shuttle", "ngs_athleticism_score", "combine_weight", "arm_length",
              "ngs_college_production_score", "draft_year_"):
        m = ol[c].notna()
        sr = stats.spearmanr(ol.O3_value[m], ol[c][m])
        z = np.arctanh(sr.statistic); se = 1.06 / np.sqrt(m.sum() - 3)
        drows.append(dict(variable=c, n=int(m.sum()), spearman_r=sr.statistic, p=sr.pvalue,
                          lo_approx=np.tanh(z - 1.96 * se), hi_approx=np.tanh(z + 1.96 * se)))
    dtab = pd.DataFrame(drows)
    groups = [g.O3_value.to_numpy() for _, g in ol.groupby("draft_year")]
    kw = stats.kruskal(*groups)
    kwt = pd.DataFrame([dict(n_OL_with_O3=len(ol), draft_years=",".join(str(int(k)) for k in sorted(ol.draft_year.unique())),
                             group_n=",".join(str(len(g)) for g in groups), H=kw.statistic, p=kw.pvalue,
                             medians=",".join(f"{np.median(g):.3f}" for g in groups))])
    C.save(dtab, "x3_player_level_spearman")
    C.save(kwt, "x3_kruskal_draft_year")
    say(dtab.round(4).to_string()); say(kwt.to_string())

    readings = [r_a, r_c, r_e, r_e10, "(b) and (d) carry no reading rule. None of these licenses a mechanism claim."]
    for r_ in readings:
        say("READING", r_)
    C.save(pd.DataFrame({"reading": readings}), "x3_readings")
    say("total seconds", round(__import__("time").time() - C.T0, 1))


if __name__ == "__main__":
    main()

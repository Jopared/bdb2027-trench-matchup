#!/usr/bin/env python
"""X4: selection (collider) and assignment discriminators. GLMs on set P with the M1-S1 base
(C_COLS + Q_COLS + [c_R, c_B]), two-way cluster SE, t(G-1). Deterministic (no random numbers)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd, polars as pl
import statsmodels.api as sm
import _common as C
from _common import CA, say, PROC

BASE = CA.C_COLS + CA.Q_COLS


def zblock(F, P, values_by_rep):
    """z over distinct blockers in P of a blocker-level quantity given per rep (taking each blocker's first value)."""
    s = pd.DataFrame({"b": F.blocker_nfl_id[P].to_numpy(), "v": np.asarray(values_by_rep)[P]}).drop_duplicates("b").set_index("b").v
    mu, sd = s.mean(), s.std(ddof=1)
    return (np.asarray(values_by_rep) - mu) / sd


def row(label, rec, term, **kw):
    d = C.tab(rec, term)
    d.update(fit=label, n_blockers=rec.D.nb, n_rushers=rec.D.nr, **kw)
    return d


def main():
    A = C.build_base(False)
    rep, ok = C.reproduce(A)
    C.save(rep, "x4_reproduction")
    say("reproduction ok:", ok)
    F, V = A.F, A.V["reg"]
    P = A.S["P"]
    tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas().set_index("nfl_id")
    rows = []

    # ---- (a) c_B x blocker pick
    zlp = zblock(F, P, F.log_pick_B.to_numpy(float))
    Xa = V.X.copy(); Xa["z_lpickB"] = zlp; Xa["cB_x_lpick"] = Xa["c_B"] * zlp
    ra = C.fit(A, BASE + ["c_R", "c_B", "z_lpickB", "cB_x_lpick"], Xover=Xa, name="X4a")
    for t in ("c_B", "z_lpickB", "cB_x_lpick"):
        rows.append(row("(a) + z(blocker log pick) + c_B x it", ra, t))
    cnt_all = F[P].groupby("blocker_nfl_id").size()
    # ---- (b) c_B x exposure (log reps in P)
    lr = np.log(F.blocker_nfl_id.map(cnt_all).to_numpy(float))
    zlr = zblock(F, P, lr)
    Xb = V.X.copy(); Xb["z_logreps"] = zlr; Xb["cB_x_logreps"] = Xb["c_B"] * zlr
    rb = C.fit(A, BASE + ["c_R", "c_B", "z_logreps", "cB_x_logreps"], Xover=Xb, name="X4b")
    for t in ("c_B", "z_logreps", "cB_x_logreps"):
        rows.append(row("(b) + z(log blocker reps in P) + c_B x it", rb, t))

    # ---- (c) player-level selection model
    ol = tr[(tr.combine_position == "OL") & tr.composite.notna()].copy()
    ol["log_pick"] = pl.read_parquet(PROC / "player_baselines.parquet").to_pandas().set_index("nfl_id").loc[ol.index, "log_pick"]
    ol["in_P"] = ol.index.isin(cnt_all.index).astype(float)
    ol["reps"] = cnt_all.reindex(ol.index).fillna(0).to_numpy()
    ol["log1p_reps"] = np.log1p(ol.reps)
    med = ol.log_pick.median()
    ol["late"] = (ol.log_pick > med).astype(float)
    ol["d2024"] = (ol.draft_year == 2024).astype(float)
    ol["d2025"] = (ol.draft_year == 2025).astype(float)
    crow = []
    for half, m in (("early (log pick <= median)", ol.late == 0), ("late (log pick > median)", ol.late == 1)):
        s = ol[m]
        Xh = sm.add_constant(s[["composite", "d2024", "d2025"]])
        Xh = Xh.loc[:, [c for c in Xh.columns if c == "const" or Xh[c].std() > 0]]
        lg = sm.Logit(s.in_P, Xh).fit(disp=0)
        ols = sm.OLS(s.log1p_reps, Xh).fit(cov_type="HC3")
        r_in, r_rep = np.corrcoef(s.composite, s.in_P)[0, 1], np.corrcoef(s.composite, s.log1p_reps)[0, 1]
        ci_l, ci_o = lg.conf_int().loc["composite"], ols.conf_int().loc["composite"]
        crow.append(dict(half=half, n_players=len(s), n_in_P=int(s.in_P.sum()), logit_slope=lg.params["composite"],
                         logit_lo=ci_l[0], logit_hi=ci_l[1], logit_p=lg.pvalues["composite"],
                         ols_slope=ols.params["composite"], ols_lo=ci_o[0], ols_hi=ci_o[1], ols_p=ols.pvalues["composite"],
                         r_composite_inP=r_in, r_composite_log1p_reps=r_rep))
    # interaction model (pooled)
    ol["comp_x_late"] = ol.composite * ol.late
    Xi = sm.add_constant(ol[["composite", "late", "comp_x_late", "d2024", "d2025"]])
    lgi = sm.Logit(ol.in_P, Xi).fit(disp=0)
    olsi = sm.OLS(ol.log1p_reps, Xi).fit(cov_type="HC3")
    cdf = pd.DataFrame(crow)
    cdf["pooled_interaction_logit_est"] = lgi.params["comp_x_late"]; cdf["pooled_interaction_logit_p"] = lgi.pvalues["comp_x_late"]
    cdf["pooled_interaction_ols_est"] = olsi.params["comp_x_late"]; cdf["pooled_interaction_ols_p"] = olsi.pvalues["comp_x_late"]
    cdf["median_log_pick"] = med
    C.save(cdf, "x4_selection_model")
    say(cdf.round(4).T.to_string())

    # ---- (d) assignment: team FE, rusher rating, game state
    rat = pd.read_csv(C.PROC / "confirmatory" / "player_ratings.csv")
    rrat = rat[rat.side == "rusher"].set_index("nfl_id").rating_mean
    base_X = V.X.copy()
    base_X["rusher_rating"] = F.rusher_nfl_id.map(rrat).to_numpy(float)
    mu, sd = np.nanmean(base_X.rusher_rating[P]), np.nanstd(base_X.rusher_rating[P], ddof=1)
    base_X["rusher_rating"] = (base_X.rusher_rating - mu) / sd
    base_X["score_diff_c"] = np.clip(F.score_diff_offense.to_numpy(float), -21, 21) / 10.0
    base_X["offense_win_prob"] = F.offense_win_prob.to_numpy(float)
    base_X["q4"] = (F.quarter.to_numpy() == 4).astype(float)
    base_X.loc[F.score_diff_offense.isna().to_numpy(), "score_diff_c"] = np.nan

    def team_dummies(col, prefix):
        teams = sorted(F[col][P].unique())
        out = {}
        for t in teams[1:]:
            out[f"{prefix}_{t}"] = (F[col].to_numpy() == t).astype(float)
        return pd.DataFrame(out)
    dfe, bfe = team_dummies("rusher_team", "defT"), team_dummies("blocker_team", "offT")
    Xd = pd.concat([base_X, dfe, bfe], axis=1)
    gs = ["score_diff_c", "offense_win_prob", "q4"]
    specs = [("(d1) + defense-team FE", list(dfe.columns)), ("(d2) + blocker-team FE", list(bfe.columns)),
             ("(d3) + rusher rating", ["rusher_rating"]), ("(d4) + score diff, win prob, Q4", gs),
             ("(d5) all together", list(dfe.columns) + list(bfe.columns) + ["rusher_rating"] + gs)]
    drows = []
    for lab, extra in specs:
        rd = C.fit(A, BASE + ["c_R", "c_B"] + extra, Xover=Xd, name="X4d")
        r_ = row(lab, rd, "c_B", n_extra_cols_kept=len(rd.D.names) - len(BASE) - 2, n=rd.D.n)
        rows.append(r_); drows.append(r_)
        rows.append(row(lab, rd, "c_R"))
    ref = C.tab(C.fit(A, C.M1S1), "c_B")["est"]
    d_in = all(abs(r_["est"] - 0.143) <= 0.05 for r_ in drows)

    # ---- (e) c_B x pos_T and c_B x edge
    Xe = V.X.copy(); Xe["cB_x_T"] = Xe.c_B * Xe.pos_T; Xe["cB_x_edge"] = Xe.c_B * Xe.edge
    re_ = C.fit(A, BASE + ["c_R", "c_B", "cB_x_T", "cB_x_edge"], Xover=Xe, name="X4e")
    D = re_.glm
    for t in ("c_B", "cB_x_T", "cB_x_edge"):
        rows.append(row("(e) + c_B x pos_T + c_B x edge", re_, t))
    for nm, co in (("c_B slope, tackle, interior", {"c_B": 1, "cB_x_T": 1}), ("c_B slope, guard/center, edge", {"c_B": 1, "cB_x_edge": 1}),
                   ("c_B slope, tackle, edge", {"c_B": 1, "cB_x_T": 1, "cB_x_edge": 1})):
        o = D.combo(co)
        rows.append(dict(fit="(e) derived", term=nm, est=o["est"], se=o["se"], lo=o["ci_nom"][0], hi=o["ci_nom"][1],
                         p=o["p_nom"], lo_k=o["ci_kappa"][0], hi_k=o["ci_kappa"][1], p_k=o["p_kappa"], n=o["n"]))
    # X1 all-snap c_B x pos_T (supplementary fit in X1's table)
    x1 = pd.read_csv(C.TABLES / "x1_fits.csv") if (C.TABLES / "x1_fits.csv").exists() else None

    res = pd.DataFrame(rows)
    C.save(res, "x4_glm_fits")
    say(res[["fit", "term", "est", "lo", "hi", "lo_k", "hi_k", "p", "n"]].round(4).to_string())

    # ---- (f) correlations
    X = V.X
    rater = F.rusher_nfl_id.map(rrat).to_numpy(float)
    feat = pd.DataFrame({"rusher_log_pick": F.log_pick_R.to_numpy(float), "rusher_rating": rater, "c_R": X.c_R.to_numpy(),
                         "edge": X.edge.to_numpy(), "double_team": X.double_team.to_numpy(),
                         "dropback_duration": F.dropback_duration.to_numpy(float)})
    fp = feat[P].copy(); fp["blocker"] = F.blocker_nfl_id[P].to_numpy(); fp["c_B"] = X.c_B[P].to_numpy()
    crows = []
    gb = fp.groupby("blocker").mean()
    for c in feat.columns:
        m = fp[c].notna()
        r_rep = np.corrcoef(fp.c_B[m], fp[c][m])[0, 1]
        mb = gb[c].notna()
        r_bl = np.corrcoef(gb.c_B[mb], gb[c][mb])[0, 1]
        crows.append(dict(feature=c, rep_level_r=r_rep, rep_n=int(m.sum()), blocker_level_r=r_bl, blocker_n=int(mb.sum())))
    cor = pd.DataFrame(crows)
    C.save(cor, "x4_correlations")
    say(cor.round(3).to_string())
    max_abs = float(np.nanmax(np.abs(cor[["rep_level_r", "blocker_level_r"]].to_numpy())))

    # ---- mechanical readings
    ia = res[(res.fit.str.startswith("(a)")) & (res.term == "cB_x_lpick")].iloc[0]
    cond1 = (ia.est > 0) and (ia.lo > 0)
    late = cdf[cdf.half.str.startswith("late")].iloc[0]
    cond2 = ((late.logit_lo > 0) or (late.logit_hi < 0) or (late.ols_lo > 0) or (late.ols_hi < 0)
             or max(abs(late.r_composite_inP), abs(late.r_composite_log1p_reps)) >= 0.3)
    r1 = ("Collider (1): (a) interaction %+.3f [%.3f, %.3f] -> %s; (c) late half: logit slope %+.3f [%.3f, %.3f], OLS slope %+.3f [%.3f, %.3f], "
          "r(inP) %+.3f, r(log1p reps) %+.3f -> %s. %s" %
          (ia.est, ia.lo, ia.hi, "satisfied" if cond1 else "not satisfied", late.logit_slope, late.logit_lo, late.logit_hi,
           late.ols_slope, late.ols_lo, late.ols_hi, late.r_composite_inP, late.r_composite_log1p_reps,
           "satisfied" if cond2 else "not satisfied",
           "Collider is called plausible." if (cond1 and cond2) else
           "The selection needed to produce Berkson bias is not present."))
    r2 = ("Assignment (2): (d) c_B estimates %s (range %.3f-%.3f; band 0.093-0.193); max |r| in (f) = %.3f (threshold 0.25) -> %s" %
          ([round(r_["est"], 3) for r_ in drows], min(r_["est"] for r_ in drows), max(r_["est"] for r_ in drows), max_abs,
           "excluded through observables" if (d_in and max_abs < 0.25) else "not excluded through observables"))
    ie = res[(res.fit.str.startswith("(e) +")) & (res.term == "cB_x_T")].iloc[0]
    r3 = ("(e) subgroup split reported, c_B x pos_T %+.3f [%.3f, %.3f]; X1 all-snap c_B x pos_T %s -> 'guards only' headline %s." %
          (ie.est, ie.lo, ie.hi,
           ("%+.3f [%.3f, %.3f]" % tuple(x1[(x1.term == "cB_x_T")][["est", "lo", "hi"]].iloc[0])) if x1 is not None else "n/a",
           "not permitted" if (x1 is None or not (((x1[x1.term == "cB_x_T"].hi.iloc[0] < 0) and ie.hi < 0) or ((x1[x1.term == "cB_x_T"].lo.iloc[0] > 0) and ie.lo > 0))) else "permitted"))
    for x in (r1, r2, r3):
        say("READING", x)
    C.save(pd.DataFrame({"reading": [r1, r2, r3]}), "x4_readings")
    say("total seconds", round(__import__("time").time() - C.T0, 1))


if __name__ == "__main__":
    main()

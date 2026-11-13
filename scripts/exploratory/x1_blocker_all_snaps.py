#!/usr/bin/env python
"""X1: blocker trait at player level on all pass-pro snaps. Logistic GLM, SE clustered by blocker, t(G-1).
Deterministic (no random numbers)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd, polars as pl
from scipy import stats
import _common as C
from _common import CA, say, PROC


def main():
    pp, games = C.load_pp_games()
    base = pl.read_parquet(PROC / "player_baselines.parquet").to_pandas().set_index("nfl_id")
    tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas().set_index("nfl_id")
    ol = tr[(tr.combine_position == "OL") & tr.composite.notna()]
    r = (pp.filter(pl.col("pressure_allowed").is_not_null())
           .filter(pl.col("lined_up_position").is_in(["T", "G", "C"]))
           .filter(pl.col("pass_result").is_not_null() & (pl.col("pass_result") != ""))
           .filter(pl.col("play_nullified_by_penalty") == "N")
           .join(games, on="game_id", how="inner").filter(pl.col("season_type").is_in(["REG", "POST"]))
           .filter(pl.col("dropback_duration").is_not_null() & pl.col("down").is_not_null()))
    n0 = r.height
    d = r.to_pandas()
    d = d[d.nfl_id.isin(ol.index)].reset_index(drop=True)
    eng = (pl.read_parquet(PROC / "engaged_pairs.parquet").filter(pl.col("engaged_primary"))
           .select(["game_id", "play_id", "blocker_nfl_id"]).unique().to_pandas()
           .rename(columns={"blocker_nfl_id": "nfl_id"}).assign(eng_play=1.0))
    d = d.merge(eng, on=["game_id", "play_id", "nfl_id"], how="left")
    d["eng_play"] = d["eng_play"].fillna(0.0)
    d["y"] = d["pressure_allowed"].astype(float)
    d["pos_T"] = (d.lined_up_position == "T").astype(float)
    d["pos_C"] = (d.lined_up_position == "C").astype(float)
    d["draft_year"] = d.nfl_id.map(base["draft_year"])
    d["exp1"] = ((d.season - d.draft_year) >= 1).astype(float)
    flow = pd.DataFrame([dict(step="pass-pro snaps after row filters (all OL)", value=n0),
                         dict(step="analysis snaps (OL with registered composite)", value=len(d)),
                         dict(step="distinct blockers", value=d.nfl_id.nunique()),
                         dict(step="pressure rate", value=d.y.mean()),
                         dict(step="snaps with engaged cohort pair (eng_play)", value=int(d.eng_play.sum()))])
    C.save(flow, "x1_flow")
    say(flow.to_string())
    ctx = C.context_cols(d, d.dropback_duration.to_numpy(float))

    def design(s, comp_values, comp_name="c_B"):
        Xc = ctx.loc[s.index].copy()
        Xc["pos_T"], Xc["pos_C"] = s["pos_T"], s["pos_C"]
        M = C.measure_cols(s, base)
        X = pd.concat([Xc, M], axis=1)
        X[comp_name] = C.zplayer(s, comp_values)
        return X

    X = design(d, tr["composite"])
    y = d.y.to_numpy(float)
    grp = d.nfl_id.to_numpy()
    rows = []

    def add(label, out, terms, ev):
        for t in terms:
            if isinstance(t, tuple):
                o = out.combo(t[1]); name = t[0]
            else:
                o = out.term(t); name = t
            rows.append(dict(fit=label, term=name, **o, events=int(ev)))

    def fit_sub(Xs, ys, gs, protect):
        Xs = C.hygiene(Xs, protect=protect)
        return C.glm_cluster1(Xs, ys, gs)

    fa = fit_sub(X, y, grp, ("c_B",)); add("(a) ctx + measures + c_B", fa, ["c_B"], y.sum())
    Xb = X.copy()
    Xb["log_pick"] = C.zplayer(d, base["log_pick"])
    Xb["undrafted"] = d.nfl_id.map(base["undrafted"]).astype(float).to_numpy()
    fb = fit_sub(Xb, y, grp, ("c_B",)); add("(b) (a) + log pick + undrafted", fb, ["c_B", "log_pick", "undrafted"], y.sum())
    m0 = d.eng_play.to_numpy() == 0
    fc = fit_sub(X[m0], y[m0], grp[m0], ("c_B",)); add("(c) (a) on eng_play == 0", fc, ["c_B"], y[m0].sum())
    Xd = X.copy(); Xd["eng_play"] = d.eng_play; Xd["cB_x_eng"] = Xd["c_B"] * Xd["eng_play"]
    fd = fit_sub(Xd, y, grp, ("c_B", "cB_x_eng"))
    add("(d) (a) + eng_play + c_B x eng_play", fd,
        ["c_B", "eng_play", "cB_x_eng", ("c_B + c_B x eng_play (engaged plays)", {"c_B": 1, "cB_x_eng": 1})], y.sum())
    Xe = X.copy(); Xe["exp1"] = d.exp1; Xe["cB_x_exp1"] = Xe["c_B"] * Xe["exp1"]
    fe = fit_sub(Xe, y, grp, ("c_B", "cB_x_exp1"))
    add("(e) (a) + exp1 + c_B x exp1", fe,
        ["c_B", "exp1", "cB_x_exp1", ("c_B + c_B x exp1 (season 2+)", {"c_B": 1, "cB_x_exp1": 1})], y.sum())
    # (g) supplementary, NOT in the X1 spec: c_B x pos_T on all snaps (needed for the X4(e) "guards only" rule)
    Xg = X.copy(); Xg["cB_x_T"] = Xg["c_B"] * Xg["pos_T"]
    fg = fit_sub(Xg, y, grp, ("c_B", "cB_x_T"))
    add("(g, not in spec) (a) + c_B x pos_T", fg,
        ["c_B", "cB_x_T", ("c_B + c_B x pos_T (tackles)", {"c_B": 1, "cB_x_T": 1})], y.sum())
    # (f) 5-frame composite
    k5 = CA.build_k5_composites()
    mk = d.nfl_id.map(k5).notna().to_numpy()
    s = d[mk]
    Xf = design(s, k5)
    ff = fit_sub(Xf, s.y.to_numpy(float), s.nfl_id.to_numpy(), ("c_B",))
    add("(f) (a) with 5-frame composite", ff, ["c_B"], s.y.sum())
    Xs = design(s, tr["composite"])
    fs = fit_sub(Xs, s.y.to_numpy(float), s.nfl_id.to_numpy(), ("c_B",))
    add("(f-ref, not in spec) (a) on (f)'s sample", fs, ["c_B"], s.y.sum())
    res = pd.DataFrame(rows)
    C.save(res, "x1_fits")
    say(res[["fit", "term", "est", "lo", "hi", "p", "n", "G"]].round(4).to_string())

    # blocker-season O/E, expected from fit (a) without c_B
    Xn = X.drop(columns=["c_B"])
    Xn = C.hygiene(Xn)
    fn = C.glm_cluster1(Xn, y, grp)
    Xm = np.column_stack([np.ones(len(Xn)), Xn.to_numpy(float)])
    d["p_hat_noCB"] = 1 / (1 + np.exp(-(Xm @ fn.beta)))
    d["c_B"] = X["c_B"].to_numpy()
    bs = (d.groupby(["nfl_id", "season"]).agg(snaps=("y", "size"), O=("y", "sum"), E=("p_hat_noCB", "sum"),
                                                c_B=("c_B", "first"), engaged_snaps=("eng_play", "sum")).reset_index())
    bs["z_OE"] = (bs.O - bs.E) / np.sqrt(bs.E)
    bsf = bs[bs.snaps >= 100].copy()
    C.save(bs, "x1_blocker_season_all")
    pr = stats.pearsonr(bsf.c_B, bsf.z_OE)
    sr = stats.spearmanr(bsf.c_B, bsf.z_OE)
    z = np.arctanh(pr.statistic); se = 1 / np.sqrt(len(bsf) - 3)
    oe = pd.DataFrame([dict(n_blocker_seasons=len(bsf), n_blockers=bsf.nfl_id.nunique(), pearson_r=pr.statistic,
                            pearson_p=pr.pvalue, pearson_lo_nominal=np.tanh(z - 1.96 * se),
                            pearson_hi_nominal=np.tanh(z + 1.96 * se), spearman_r=sr.statistic, spearman_p=sr.pvalue)])
    C.save(oe, "x1_oe_correlation")
    say(oe.round(4).to_string())

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.scatter(bsf.c_B, bsf.z_OE, s=bsf.snaps / 6, alpha=0.6, color="#3b6ea5", edgecolor="white", linewidth=0.5)
    b1, b0 = np.polyfit(bsf.c_B, bsf.z_OE, 1)
    xs = np.linspace(bsf.c_B.min(), bsf.c_B.max(), 50)
    ax.plot(xs, b0 + b1 * xs, color="#c0504d", lw=1.5)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("blocker mirror-drill composite c_B (z over blockers in set)")
    ax.set_ylabel("(observed - expected pressures) / sqrt(expected)")
    ax.set_title(f"X1 (exploratory): blocker-seasons with >=100 snaps, n={len(bsf)}, r={pr.statistic:.2f}", fontsize=10)
    fig.tight_layout()
    fig.savefig(C.FIGS / "x1_blocker_season_OE.png", dpi=150)
    C.save(bsf, "x1_blocker_season_scatter_data")

    # mechanical readings
    ga = res[res.fit.str.startswith("(a)")].iloc[0]
    gb = res[(res.fit.str.startswith("(b)")) & (res.term == "c_B")].iloc[0]
    gd = res[(res.fit.str.startswith("(d)")) & (res.term == "cB_x_eng")].iloc[0]
    ge = res[(res.fit.str.startswith("(e)")) & (res.term == "cB_x_exp1")].iloc[0]
    r1 = ("R1: (a) CI includes 0 and upper < 0.15 -> bounded" if (ga.lo <= 0 <= ga.hi and ga.hi < 0.15)
          else "R1: (a) excludes 0 positive" if ga.lo > 0
          else "R1: neither branch applies (CI includes 0 but upper >= 0.15, or excludes 0 negative)")
    r2 = "R2: interaction CI includes 0 -> not distinguishable" if gd.lo <= 0 <= gd.hi else "R2: interaction CI excludes 0"
    r3 = f"R3: |(b)-(a)| = {abs(gb.est - ga.est):.4f} ({'>' if abs(gb.est - ga.est) > .03 else '<='} 0.03)"
    r4 = "R4: rookie timing supported" if (ge.est < 0 and ge.hi < 0) else "R4: rookie timing not supported"
    for x in (r1, r2, r3, r4):
        say("READING", x)
    C.save(pd.DataFrame({"reading": [r1, r2, r3, r4]}), "x1_readings")
    say("total seconds", round(__import__("time").time() - C.T0, 1))


if __name__ == "__main__":
    main()

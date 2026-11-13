#!/usr/bin/env python
"""X5: rusher trait at player level on all pass-rush snaps (blitzing true, EDGE / INTERIOR_LINE, DL in combine_traits).
Logistic GLM, SE clustered by rusher, t(G-1). Deterministic (no random numbers)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd, polars as pl
import _common as C
from _common import say, PROC


def main():
    pp, games = C.load_pp_games()
    dbp = C.play_level_dropback(pp)
    base = pl.read_parquet(PROC / "player_baselines.parquet").to_pandas().set_index("nfl_id")
    tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas().set_index("nfl_id")
    dl = tr[tr.combine_position == "DL"]
    r = (pp.filter(pl.col("blitzing") == True)  # noqa: E712
           .filter(pl.col("lined_up_position").is_in(["EDGE", "INTERIOR_LINE"]))
           .filter(pl.col("pass_result").is_not_null() & (pl.col("pass_result") != ""))
           .filter(pl.col("play_nullified_by_penalty") == "N")
           .join(games, on="game_id", how="inner").filter(pl.col("season_type").is_in(["REG", "POST"]))
           .join(dbp, on=["game_id", "play_id"], how="left"))
    n_all = r.height
    d = r.to_pandas()
    d = d[d.nfl_id.isin(dl.index)]
    n_dl = len(d)
    d["dropback_duration"] = d["db_play"]
    n_nodb = int(d.dropback_duration.isna().sum())
    d = d[d.dropback_duration.notna() & d.down.notna() & d.yards_to_go.notna()].reset_index(drop=True)
    d["press"] = d["time_to_pressure"].notna().astype(float)
    d["quick"] = d["quick_pressure"].fillna(False).astype(bool).astype(float)
    d["edge"] = (d.lined_up_position == "EDGE").astype(float)
    flow = pd.DataFrame([dict(step="blitzing, EDGE/INTERIOR_LINE, dropback, not nullified, REG/POST", rows=n_all),
                         dict(step="+ nfl_id is DL in combine_traits", rows=n_dl),
                         dict(step="- no play-level dropback_duration (dropped)", rows=-n_nodb),
                         dict(step="analysis frame (before composite requirement)", rows=len(d)),
                         dict(step="pressure rate (time_to_pressure non-null)", rows=float(d.press.mean())),
                         dict(step="quick_pressure rate", rows=float(d.quick.mean()))])
    C.save(flow, "x5_flow")
    say(flow.to_string())
    ctx = C.context_cols(d, d.dropback_duration.to_numpy(float))

    def run(label, sub_mask, comp_values: pd.Series, extra_pick=False, comp_name="c_R", outcome="press"):
        s = d[sub_mask].copy()
        Xc = ctx.loc[s.index].copy()
        Xc["edge"] = s["edge"]
        M = C.measure_cols(s, base)
        X = pd.concat([Xc, M], axis=1)
        X[comp_name] = C.zplayer(s, comp_values)
        if extra_pick:
            X["log_pick"] = C.zplayer(s, base["log_pick"])   # z-scored over distinct rushers
            X["undrafted"] = s["nfl_id"].map(base["undrafted"]).astype(float).to_numpy()
        X = C.hygiene(X, protect=(comp_name,))
        out = C.glm_cluster1(X, s[outcome].to_numpy(float), s["nfl_id"].to_numpy())
        res = dict(fit=label, outcome=outcome, **out.term(comp_name), rushers=out.G, snaps=out.n,
                   events=int(s[outcome].sum()))
        if extra_pick:
            res["log_pick_est"] = out.term("log_pick")["est"]
            res["undrafted_est"] = out.term("undrafted")["est"]
        return res

    comps = {"a": tr["composite"], "c": tr["composite_sensA"], "d": tr["D5_z"]}
    rows = []
    for outcome in ("press", "quick"):
        ma = d.nfl_id.map(comps["a"]).notna()
        rows.append(run("(a) + c_R (registered D1)", ma, comps["a"], outcome=outcome))
        rows.append(run("(b) (a) + log pick + undrafted", ma, comps["a"], extra_pick=True, outcome=outcome))
        mc = d.nfl_id.map(comps["c"]).notna()
        rows.append(run("(c) c_R from composite_sensA (D1 + D5)", mc, comps["c"], outcome=outcome))
        md = d.nfl_id.map(comps["d"]).notna()
        rows.append(run("(d) D5_z alone", md, comps["d"], comp_name="D5_z", outcome=outcome))
    res = pd.DataFrame(rows)
    C.save(res, "x5_fits")
    say(res[["fit", "outcome", "est", "lo", "hi", "p", "rushers", "snaps", "events"]].round(4).to_string())
    pa, pb = res[(res.outcome == "press") & res.fit.str.startswith(("(a)", "(b)"))].itertuples()
    ok_null = all((r_.lo <= 0 <= r_.hi) and r_.hi < 0.10 for r_ in (pa, pb))
    say("READING (a),(b) both CI include 0 with upper < 0.10:", ok_null)
    for r_ in res[(res.outcome == "press") & res.fit.str.startswith(("(c)", "(d)"))].itertuples():
        say("READING", r_.fit, "CI excludes 0 negative:", r_.hi < 0)
    say("READING (a) positive excluding 0:", bool(pa.lo > 0))
    say("total seconds", round(__import__("time").time() - C.T0, 1))


if __name__ == "__main__":
    main()

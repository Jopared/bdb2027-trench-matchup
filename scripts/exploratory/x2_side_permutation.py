#!/usr/bin/env python
"""X2: Freedman-Lane permutation test (V5 machinery) for the side terms c_B and c_R of M1-S1 (GLM, set P).
Seed: numpy default_rng(2027), a fresh stream for each tested side; 2,000 draws."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd
import _common as C
from _common import CA, say

NPERM = 2000


def main():
    A = C.build_base(False)
    rep, ok = C.reproduce(A)
    C.save(rep, "x2_reproduction")
    say("reproduction ok:", ok)
    rec = C.fit(A, C.M1S1, name="M1-S1")
    D, F, V = rec.D, A.F, A.V["reg"]
    obs = {t: rec.glm.term(t) for t in ("c_B", "c_R")}
    idx = D.idx
    side_info = {}
    for s, ids, idc, cm in (("B", D.bl_ids, "blocker_nfl_id", "composite_B"), ("R", D.ru_ids, "rusher_nfl_id", "composite_R")):
        sub = F.iloc[idx].drop_duplicates(idc).set_index(idc).loc[ids]
        MEAS = CA.MEAS
        cols = [np.nan_to_num((sub[f"{m}_{s}"].to_numpy(float) - V.side[(m, s)][0]) / V.side[(m, s)][1]) for m in MEAS]
        cols += [sub["forty_" + s].isna().to_numpy(float), sub["short_shuttle_" + s].isna().to_numpy(float),
                 sub["three_cone_" + s].isna().to_numpy(float)]
        Z = np.column_stack([np.ones(len(sub))] + cols)
        keep = [0] + [j for j in range(1, Z.shape[1]) if np.ptp(Z[:, j]) > 0]
        Z = Z[:, keep]
        comp = sub[cm].to_numpy(float)
        coef = np.linalg.lstsq(Z, comp, rcond=None)[0]
        fit = Z @ coef
        side_info[s] = dict(fit=fit, res=comp - fit, cls=sub["draft_year_" + s].to_numpy(), n=len(sub))
    clu = CA.ClusterIdx(D.bid, D.rid, D.did)
    X = np.column_stack([np.ones(D.n), D.X])
    y = rec.y
    beta0 = rec.glm.beta.copy()
    b_chk, V_chk = CA.fast_logit_cluster(X, y, clu)
    gi = {"c_B": D.names.index("c_B") + 1, "c_R": D.names.index("c_R") + 1}
    eng_chk = dict(max_abs_beta_diff=float(np.abs(b_chk - rec.glm.beta).max()),
                   se_cB_diff=float(abs(np.sqrt(V_chk[gi["c_B"], gi["c_B"]]) - obs["c_B"]["se"])),
                   se_cR_diff=float(abs(np.sqrt(V_chk[gi["c_R"], gi["c_R"]]) - obs["c_R"]["se"])))
    say("engine check:", eng_chk)
    rows, draws = [], {}
    bid_or_rid = {"B": D.bid, "R": D.rid}
    for term, s in (("c_B", "B"), ("c_R", "R")):
        t0 = __import__("time").time()
        inf = side_info[s]
        mu, sd = V.std[term]
        X0 = X.copy()
        orig_col = X0[:, gi[term]].copy()
        rng = np.random.default_rng(2027)
        bs, ts = np.empty(NPERM), np.empty(NPERM)
        for k in range(NPERM):
            e = inf["res"].copy()
            for c in np.unique(inf["cls"]):
                mm = np.flatnonzero(inf["cls"] == c)
                e[mm] = inf["res"][mm][rng.permutation(len(mm))]
            comp = inf["fit"] + e
            X0[:, gi[term]] = (comp[bid_or_rid[s]] - mu) / sd
            b, Vm = CA.fast_logit_cluster(X0, y, clu, beta0=beta0)
            bs[k], ts[k] = b[gi[term]], b[gi[term]] / np.sqrt(Vm[gi[term], gi[term]])
        o = obs[term]
        t_obs = o["est"] / o["se"]
        p2 = (1 + np.sum(np.abs(ts) >= abs(t_obs))) / (NPERM + 1)
        p1 = (1 + np.sum(ts * np.sign(t_obs) >= abs(t_obs))) / (NPERM + 1)
        pc = (1 + np.sum(np.abs(bs) >= abs(o["est"]))) / (NPERM + 1)
        rows.append(dict(term=term, permuted_side=s, n_players_permuted=inf["n"], beta_obs=o["est"], se_obs=o["se"],
                         t_obs=t_obs, p_two_studentized=p2, p_one_same_direction=p1, p_two_coef=pc,
                         tnull_mean=ts.mean(), tnull_sd=ts.std(ddof=1), tnull_q025=np.quantile(ts, .025),
                         tnull_q975=np.quantile(ts, .975), bnull_sd=bs.std(ddof=1), seconds=__import__("time").time() - t0))
        draws[term] = (bs, ts)
        say(term, "t_obs", round(t_obs, 3), "p2", round(p2, 4), "p_coef", round(pc, 4))
    res = C.save(pd.DataFrame(rows), "x2_permutation_summary")
    C.save(pd.DataFrame({"k": np.arange(1, NPERM + 1), "beta_star_cB": draws["c_B"][0], "t_star_cB": draws["c_B"][1],
                         "beta_star_cR": draws["c_R"][0], "t_star_cR": draws["c_R"][1]}), "x2_permutation_draws")
    C.save(pd.DataFrame([eng_chk]), "x2_engine_check")
    p = res.set_index("term").p_two_studentized
    for t in ("c_B", "c_R"):
        say(f"READING {t}: p={p[t]:.4f} ->", "not distinguishable from permutation noise" if p[t] >= .05
            else "passes calibrated permutation test (secondary/exploratory)")
    say("total seconds", round(__import__("time").time() - C.T0, 1))


if __name__ == "__main__":
    main()

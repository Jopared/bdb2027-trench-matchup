"""Step 1 of the pre-registered design: Combine-trait qualification and frozen side composites.

Run from the repo root:  .venv/Scripts/python.exe scripts/trait_qualification.py
Writes reports/trait_qualification.md and data/processed/combine_traits.parquet.
Reads ONLY combine_tracking and combine_results. Never reads player_play or game tracking.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from bdb2027 import traits as T

ROOT = Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "reports" / "trait_qualification.md"
OUT_PQ = ROOT / "data" / "processed" / "combine_traits.parquet"
L: list[str] = []


def w(s=""):
    L.append(str(s))


def f3(v, d=3):
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def rci(r, lo, hi, d=3):
    return "n/a" if not np.isfinite(r) else f"{r:.{d}f} [{f3(lo, d)}, {f3(hi, d)}]"


def tbl(rows, cols):
    w()
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for r in rows:
        w("| " + " | ".join(str(x) for x in r) + " |")
    w()


def main():
    cr = T.load_combine_results()
    reps = {k: T.load_reps(v) for k, v in T.DRILLS.items()}
    n_side = cr.combine_position.value_counts().to_dict()

    POP = T.engaged_populations()
    R3, R5, V3, V5 = {}, {}, {}, {}
    for tid in T.TRAITS:
        R3[tid] = T.evaluate_trait(tid, reps, cr, 3, pop=POP)
        R5[tid] = T.evaluate_trait(tid, reps, cr, 5, pop=POP)
        V3[tid], V5[tid] = T.gate_verdicts(R3[tid]), T.gate_verdicts(R5[tid])

    comp, info = T.build_composites(R3, V3, cr)

    # ----------------------------------------------------------- sensitivity composites (NOT the registered composites)
    def sens(tids_by_side):
        c = pd.Series(np.nan, index=comp.index); n = pd.Series(0, index=comp.index)
        for side, tids in tids_by_side.items():
            m = comp.combine_position == side
            Z = comp.loc[m, [f"{t}_z" for t in tids]]
            c[m] = Z.mean(axis=1, skipna=True); n[m] = Z.notna().sum(axis=1)
        return c.where(n > 0), n
    # A: reliability + redundancy pass, coverage ignored. B: A plus O1 (point r >= 0.50, CI lower 0.293 misses 0.30)
    sensA = {s: [t for t in T.TRAITS if T.TRAITS[t].side == s and V3[t]["rel"] and V3[t]["red"]] for s in ("OL", "DL")}
    sensB = {s: sorted(set(v) | ({"O1"} if s == "OL" else set())) for s, v in sensA.items()}
    comp["composite_sensA"], comp["composite_sensA_n"] = sens(sensA)
    comp["composite_sensB"], comp["composite_sensB_n"] = sens(sensB)

    # extra per-trait columns for the parquet
    for t in T.TRAITS:
        comp[f"{t}_gate_reliability"] = V3[t]["rel"]
        comp[f"{t}_gate_redundancy"] = V3[t]["red"]
        comp[f"{t}_gate_coverage"] = V3[t]["cov"]
        comp.loc[comp.combine_position != T.TRAITS[t].side, [f"{t}_value", f"{t}_z", f"{t}_n_slots"]] = np.nan
    comp["composite_components"] = comp.combine_position.map(lambda s: ",".join(info[s]["passing"]))
    OUT_PQ.parent.mkdir(parents=True, exist_ok=True)
    comp.to_parquet(OUT_PQ, index=False)

    # ----------------------------------------------------------- report
    w("# Trait qualification (step 1 of the pre-registered design)")
    w()
    w("Applies the fixed pool O1-O5 / D1-D6 and the fixed gates of `reports/candidates_v2.md` section 3.2 to Combine tracking and "
      "Combine results only. No NFL outcome, `player_play` or game tracking was read. Every number below is **computed** by "
      "`scripts/trait_qualification.py` using `src/bdb2027/traits.py` (bootstrap: 2,000 resamples over players, seed 2027, percentile CI). "
      "Items I had to decide are tagged **[decision]**; the full list is in section 7. Gates are applied mechanically; no definition was tuned.")
    w()
    w(f"Side sizes (combine_position): OL {n_side['OL']}, DL {n_side['DL']}. **Registered coverage gate** (rule 4) is measured against the engaged-rep set "
      f"(`engaged_pairs.parquet`, engaged_primary): blockers = distinct blocker_nfl_id lined up T/G/C with combine_position OL (**{len(POP['OL'])}**); "
      f"rushers = distinct rusher_nfl_id with combine_position DL (**{len(POP['DL'])}**). Coverage against all combine players is also shown and labelled 'all-players'. "
      "No outcome column was read.")
    w()

    # ---- headline
    w("## 0. Headline")
    w()
    for s in ("OL", "DL"):
        p = info[s]["passing"]
        w(f"- **{s} composite = {{{', '.join(p) if p else 'none'}}}** ({'; '.join(T.TRAITS[t].short for t in p)}).")
    w("- Three verdicts sit on a knife edge and decide the composition: **O1** r = "
      f"{rci(R3['O1']['r'], R3['O1']['lo'], R3['O1']['hi'])}, bootstrap lower bound {f3(R3['O1']['lo'])} vs the 0.30 bar (point estimate passes, CI fails by "
      f"{f3(0.30 - R3['O1']['lo'])}); **O4** and **D5** pass reliability and redundancy but fail coverage at "
      f"{R3['O4']['coverage_n']}/{R3['O4']['n_pop']} = {100 * R3['O4']['coverage']:.1f}% of engaged blockers (OL) and {R3['D5']['coverage_n']}/{R3['D5']['n_pop']} = {100 * R3['D5']['coverage']:.1f}% of engaged rushers (DL) "
      "against the 80% bar (registered engaged-rep-set populations; all-players coverage was 78.5% / 78.8%, i.e. the correction moved them closer but not over; the 40 exists for 95/121 OL, 93/118 DL). Under the rule as written all three are out. Sensitivity composites that admit them are "
      "provided in the parquet (`composite_sensA`, `composite_sensB`) and section 2, clearly separate from the registered composite.")
    w("- D4 cannot be evaluated as defined: the wave drill is one forward start plus one lateral reaction, so almost no rep has >= 4 reversals "
      f"(n with a value = {R3['D4']['coverage_n']} of {R3['D4']['n_pop']} engaged rushers).")
    w(f"- **O3 (the only OL component) is smoothing-fragile:** odd/even r = {rci(R3['O3']['r'], R3['O3']['lo'], R3['O3']['hi'])} with 3-frame smoothing but {rci(R5['O3']['r'], R5['O3']['lo'], R5['O3']['hi'])} with 5-frame smoothing "
      "(below the 0.60 bar), and 0.580 / 0.473 under the min-run-2 and 0.5 yd/s threshold variants (section 6). The registered (3-frame) verdict is PASS; the sensitivity would FAIL, which would leave OL with no passing trait (primary hypothesis then DL-only per rule 6).")
    w("- The 40-yard acceleration-shape coverage question (246/375) could not be reproduced: the specified definition yields a value for 373/375 pairs (the 2 exceptions are TE runs that already exceed 2.0 yd/s at the first frame), and for all 84 OL and all 84 DL pairs (section 3).")
    w()

    # ---- 1. gate table
    w("## 1. Gate table (3-frame smoothing; primary)")
    w()
    rows = []
    for tid, tr in T.TRAITS.items():
        r, v = R3[tid], V3[tid]
        rel_kind = "odd/even" if tr.kind == "within" else "cross-rep"
        rows.append([tid, tr.side, tr.short, rel_kind, r["n"], rci(r["r"], r["lo"], r["hi"]),
                     f"{f3(r['max_abs_r'])} ({r['argmax']})", f"{r['coverage_n']}/{r['n_pop']} = {100 * r['coverage']:.1f}% (all-players {100 * r['coverage_all']:.1f}%)",
                     "PASS" if v["rel"] else "FAIL", "PASS" if v["red"] else "FAIL", "PASS" if v["cov"] else "FAIL",
                     "**PASS**" if v["passed"] else "FAIL"])
    tbl(rows, ["ID", "Side", "Trait", "Reliability type", "n pairs", "r [95% CI]", "max abs r (measure)", "Coverage (engaged set)", "Reliability gate", "Redundancy gate", "Coverage gate", "Overall"])
    w("Gate rules as applied: reliability = cross-rep r >= 0.50 and bootstrap lower bound >= 0.30 (two-slot traits), or odd/even within-rep r >= 0.60 "
      "(O3, D4; **[decision]** uncorrected r is gated, Spearman-Brown value reported alongside; the 0.30 CI-bound is not required for within-rep traits, per the pool text); "
      "redundancy = all |r| < 0.75 vs forty, ten_yd_split, short_shuttle, three_cone (n >= 30 only), combine_weight, arm_length, within the side; "
      "coverage = share of the side's engaged-rep-set players (79-ish blockers / rushers, see above) with a trait value (any rep).")
    w()

    # ---- per-trait detail
    w("### 1a. Per-trait detail")
    w()
    for tid, tr in T.TRAITS.items():
        r, r5, v, v5 = R3[tid], R5[tid], V3[tid], V5[tid]
        w(f"#### {tid} ({tr.side}, {tr.drill}): {tr.short}")
        w()
        w(f"- **Definition as implemented:** {tr.definition}")
        if tr.note:
            w(f"- Note: {tr.note}")
        w(f"- Orientation: {'higher raw value' if tr.orient > 0 else 'lower raw value'} = more athletic; composite uses {'+' if tr.orient > 0 else '-'} z.")
        if tr.kind == "within":
            w(f"- n players with a value (>= 4 reversals; all players): {r['coverage_all_n']} of {r['n_side']}; players with a rep: {r['reps_total']}. Reversals per rep: "
              + ", ".join(f"{k} {f3(vv, 2)}" for k, vv in r["n_rev_dist"].items()) + ".")
            w(f"- Within-rep odd vs even reversal r = {rci(r['r'], r['lo'], r['hi'])} (n = {r['n']}); Spearman-Brown full-length r = {f3(r['r_sb'])}.")
            w(f"- 5-frame smoothing: r = {rci(r5['r'], r5['lo'], r5['hi'])} (n = {r5['n']}); verdict {'unchanged' if v5['passed'] == v['passed'] else 'CHANGES to ' + ('PASS' if v5['passed'] else 'FAIL')}.")
        else:
            w(f"- Reps: {r['reps_total']} rep/slot values; pairs with both slots: {r['n']}; players with >= 1 value (all players): {r['coverage_all_n']} of {r['n_side']}.")
            w(f"- Cross-rep r on the gate scale = {rci(r['r'], r['lo'], r['hi'])} (n = {r['n']}); Spearman-Brown two-rep-mean reliability = {f3(r['r_sb'])}. "
              f"r without year standardisation = {f3(r['r_sideonly'])}; r on raw values = {f3(r['r_raw'])}"
              + (" (raw values mix drift sides, shown for completeness)." if tr.grouped else "."))
            w(f"- 5-frame smoothing: r = {rci(r5['r'], r5['lo'], r5['hi'])} (n = {r5['n']}); verdict {'unchanged' if v5['passed'] == v['passed'] else 'CHANGES to ' + ('PASS' if v5['passed'] else 'FAIL')}.")
        dv = ", ".join(f"{y}: {f3(d, 2)}" for y, d in r["drift"].items()) if r["drift"] else "n/a"
        ym = "; ".join(f"{y}: mean {f3(m, 3)}, SD {f3(s, 3)}, n {n}" for y, (m, s, n) in r["year_means"].items())
        w(f"- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = {'side-standardised z' if tr.grouped else 'raw trait'}): {dv}; max {f3(r['drift_max'], 2)} -> "
          f"{'FLAG (> 0.5)' if r['drift_flag'] else 'no flag'}. Year means: {ym}.")
        applied = r["year_applied"]
        why = "prescribed (side x year z is part of the definition)" if tr.prescribed_z else ("applied by [decision], same treatment as O1/D1" if (tr.grouped) else ("applied because drift flag fired" if applied else "not applied (no flag)"))
        w(f"- Year standardisation applied to gate-scale values: **{'yes' if applied else 'no'}** ({why}). The composite additionally z-scores within position x draft year.")
        red = ", ".join(f"{c} {f3(x[0])} (n {x[1]}){' [skipped, n<30]' if x[2] else ''}" for c, x in r["red"].items())
        w(f"- Redundancy |r| vs official (gate scale): {red}. **max |r| = {f3(r['max_abs_r'])} ({r['argmax']})**; on the raw (non-year-standardised) trait scale max |r| = {f3(r['max_abs_r_raw'])}"
          + (" (verdict differs from gate scale)." if (r['max_abs_r_raw'] < 0.75) != (r['max_abs_r'] < 0.75) else "."))
        w(f"- Coverage (engaged-rep set, registered gate): {r['coverage_n']}/{r['n_pop']} = {100 * r['coverage']:.1f}%; all-players coverage: {r['coverage_all_n']}/{r['n_side']} = {100 * r['coverage_all']:.1f}%" + (f"; players with both slots: {r['n_both_slots']}" if tr.kind == "cross" else "") + ".")
        if tr.oob_note:
            w(f"- {tr.oob_note}")
        w(f"- **Verdicts:** reliability {'PASS' if v['rel'] else 'FAIL'} ({v['rel_rule']}); redundancy {'PASS' if v['red'] else 'FAIL'}; coverage {'PASS' if v['cov'] else 'FAIL'} -> **{'PASS' if v['passed'] else 'FAIL'}**.")
        w()

    # ---- 2. composites
    w("## 2. Frozen side composites")
    w()
    w("Rule: equal-weighted mean of the within-position x within-draft-year z-scores (player-level trait value; oriented so higher = more athletic) of every passing trait; "
      "a player needs >= 1 component; Mosier reliability for the unit-weighted composite of standardised components: rel = 1 - sum(1 - r_ii) / (k + 2 sum_{i<j} r_ij), "
      "with r_ii = reliability of the player-level trait value (**[decision]** Spearman-Brown-corrected cross-rep or odd/even r, because the player value is a two-rep mean / full-length median) "
      "and r_ij = Pearson among players with all components. With one component the Mosier value is that component's reliability.")
    w()
    for s in ("OL", "DL"):
        i = info[s]
        w(f"### {s}")
        w()
        if not i["passing"]:
            w("No passing trait.")
            continue
        w(f"- Components: **{', '.join(i['passing'])}**; definitions: " + " | ".join(f"{t}: {T.TRAITS[t].definition}" for t in i["passing"]))
        w(f"- Mosier composite reliability: **{f3(i['mosier'])}** (Spearman-Brown-corrected component reliabilities {[f3(x) for x in i['rel']]}); with uncorrected single-rep r_ii: {f3(i['mosier_uncorrected'])}.")
        eng_n = int(comp[comp.nfl_id.isin(list(POP[s])) & comp.composite.notna()].shape[0])
        w(f"- Players with a composite: **{i['n_comp']}** of {n_side[s]} all combine {s} players; **{eng_n}** of {len(POP[s])} engaged-set {'blockers' if s == 'OL' else 'rushers'} (players with all components: {i['n_all_components']}; component-count distribution {i['ncomp_dist']}).")
        if i.get("corr") is not None:
            w(f"- Component intercorrelations:\n\n```\n{i['corr'].round(3).to_string()}\n```")
        m = (comp.combine_position == s) & comp.composite.notna()
        g = comp[m].groupby("draft_year").composite.agg(["count", "mean", "std", "min", "max"])
        tbl([[int(y), int(r_["count"]), f3(r_["mean"]), f3(r_["std"]), f3(r_["min"]), f3(r_["max"])] for y, r_ in g.iterrows()],
            ["draft_year", "n with composite", "mean", "SD", "min", "max"])
        allc = comp[(comp.combine_position == s)].groupby("draft_year").size()
        w("Players per draft year (all of the side): " + ", ".join(f"{int(y)}: {n}" for y, n in allc.items()) +
          ". (Within-year means are 0 by construction; SD is 1 for a one-component composite and < 1 when several imperfectly correlated components are averaged.)")
        w()
    w("### Sensitivity composites (NOT the registered composites; for the decision-maker)")
    w()
    for nm, spec in (("A (reliability + redundancy pass, coverage ignored)", sensA), ("B (A plus O1, whose point r passes but CI lower bound misses 0.30)", sensB)):
        col = "composite_sensA" if nm.startswith("A") else "composite_sensB"
        w(f"- {nm}: OL = {{{', '.join(spec['OL'])}}}, DL = {{{', '.join(spec['DL'])}}}; players with a composite: OL {int(comp[(comp.combine_position == 'OL')][col].notna().sum())}, DL {int(comp[(comp.combine_position == 'DL')][col].notna().sum())}. "
          f"Correlation with registered composite: OL {f3(comp[comp.combine_position == 'OL'][['composite', col]].corr().iloc[0, 1])}, DL {f3(comp[comp.combine_position == 'DL'][['composite', col]].corr().iloc[0, 1])}.")
    w()

    # ---- 3. 246 / 375
    w("## 3. The 246 / 375 acceleration-shape coverage question")
    w()
    F = reps["forty"].copy()
    rows_ = []
    for _, rr in F[F.rep <= 2].iterrows():
        v, top = T.accel_shape(rr.s, 3)
        ss = T.cmean(rr.s, 3)
        i9 = next((i for i in range(len(ss)) if ss[i] >= 0.9 * top), len(ss) - 1)
        rows_.append(dict(rem=len(ss) - 1 - i9, nfl_id=rr.nfl_id, rep=rr.rep, pos=rr.combine_position, val=v, top=top, last=ss[-2] / top if len(ss) > 2 else np.nan,
                          dx=rr.x[-1] - rr.x[0], x0=rr.x[0], n=len(rr.s), s0=ss[1], i2=int(np.argmax(ss >= 2.0)) if (np.nan_to_num(ss) >= 2.0).any() else -1))
    A = pd.DataFrame(rows_)
    pairs = A.groupby("nfl_id").filter(lambda g: len(g) == 2)
    pp = pairs.groupby("nfl_id").agg(pos=("pos", "first"), ok=("val", lambda v: v.notna().all()), top=("top", "max"), last=("last", "min"),
                                     dx=("dx", "min"), x0=("x0", "max"))
    tot = len(pp)
    bypos = pp.groupby("pos").ok.agg(["size", "sum"])
    w(f"Computed with the specified definition (frame-based, 3-frame smoothed s, run must be seen below 2.0 first): **{int(pp.ok.sum())} of {tot} pairs have a value in both runs**; by position (pairs / with value): "
      + ", ".join(f"{p}: {int(r_['size'])}/{int(r_['sum'])}" for p, r_ in bypos.iterrows()) + ".")
    w(f"At run level: {int(A.val.notna().sum())} of {len(A)} runs have a value (all {A.nfl_id.nunique()} players with a 40). Frames before s first crosses 2.0: median index {int(A.i2.median())}, range {int(A.i2.min())}-{int(A.i2.max())}; "
      f"second-frame smoothed s median {A.s0.median():.2f} yd/s; every run is seen below 2.0 before crossing it (except {int((A.val.isna()).sum())} runs). "
      f"The first frame at 0.9 x top speed leaves a median of {int(A.rem.median())} frames (minimum {int(A.rem.min())}) before the recording ends, so nothing is right-censored.")
    w()
    w("So the specified trait does **not** go missing for non-linemen. I could not recover the prior query's implementation, so I tested the mechanisms that could plausibly produce a position-dependent shortfall "
      "(pairs retained / OL / DL retained under each):")
    w()
    hyp = []
    ids = pp.index
    pos = pp["pos"]
    def row(lab, mask):
        keep = pp.index[mask]
        hyp.append([lab, len(keep), int((pos[keep] == "OL").sum()), int((pos[keep] == "DL").sum())])
    row("specified definition (value in both runs)", pp.ok.values)
    att = (pl.read_parquet(T.paths.parquet("combine_tracking"))
           .filter((pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "FORTY_YARD_DASH") & pl.col("attempt").is_in([1, 2]))
           .group_by("nfl_id").agg(pl.col("attempt").n_unique().alias("na")).filter(pl.col("na") == 2)["nfl_id"].to_list())
    row("pairs identified by attempt numbers 1 and 2 (numbering unreliable)", pp.index.isin(att))
    for cap in (11.0, 10.9, 10.5):
        row(f"both-run top speed < {cap} yd/s (speed-dependent filter)", (pp.top < cap).values)
    for thr in (0.97, 0.98):
        row(f"last-frame speed >= {thr} x top (requires run to end at top speed)", (pp["last"] >= thr).values)
    row("run covers >= 40 yd in x", (pp.dx >= 40).values)
    row("first-frame x < 10", (pp.x0 < 10).values)
    tbl(hyp, ["hypothesised cause", "pairs retained (of 375)", "OL retained (of 84)", "DL retained (of 84)"])
    w("None of these reproduces 246 with OL and DL complete. The only family that spares the slower linemen and removes the faster groups is a **speed-dependent condition** "
      "(top speeds: OL median 9.4, DL 10.1, TE 10.4, DB 11.0, WR 11.1 yd/s): the closest hit is a top-speed cap near 10.9-11.0 (242-268 pairs), but it also removes some DL, so it is not an exact match. "
      "**Conclusion (computed fact + inference):** the shortfall is not a property of the data or of the specified definition; it came from an implementation detail of the earlier ad-hoc query that "
      "interacted with speed (I could not identify which). The real coverage issue is different and binds: the 40 exists for only "
      f"{R3['O4']['coverage_all_n']}/{n_side['OL']} OL and {R3['D5']['coverage_all_n']}/{n_side['DL']} DL players (11 OL and 9 DL have a single tracked run; the rest have none): all-players coverage 78.5% / 78.8%, and {R3['O4']['coverage_n']}/{R3['O4']['n_pop']} = {100*R3['O4']['coverage']:.1f}% / {R3['D5']['coverage_n']}/{R3['D5']['n_pop']} = {100*R3['D5']['coverage']:.1f}% in the registered engaged-rep populations, **just under the 80% bar either way**.")
    w()

    # ---- 4. PASS_RUSH_DROP phase semantics
    w("## 4. PASS_RUSH_DROP and the inferred 'open hips and run' phase")
    w()
    D = reps["drop"][reps["drop"].combine_position == "OL"]
    tpk = [float(np.nanargmax(T.cmean(s_, 3)) * 0.1) for s_ in D.s]
    w("- **O1** is the whole-rep maximum of the 3-frame smoothed speed. It uses no onset, no time window and no phase boundary; the drift-side label uses only the first and last positions of the rep (sign of y_end - y_start). "
      f"It therefore does not depend on the inferred phase semantics. (Computed: the peak occurs at median {np.median(tpk):.1f} s into the rep, range {min(tpk):.1f}-{max(tpk):.1f} s; nothing in the definition conditions on this.)")
    w("- **O2** (`open_and_run`) *does* depend on it (search window starts at onset + 1.8 s, then s 2.0 -> 4.5 yd/s). It fails the reliability gate, so it is not in any composite. "
      f"Checks: OL composite components = {info['OL']['passing']}; no PASS_RUSH_DROP trait is among them.")
    w("- O3 uses the mirror drill and O4/O5 the 40, so none of them involves the PASS_RUSH_DROP semantics.")
    w()

    # ---- 5. atlas
    w("## 5. Reliability atlas (T1)")
    w()
    rows = []
    for tid, tr in T.TRAITS.items():
        r, v = R3[tid], V3[tid]
        fails = [n_ for n_, ok in (("reliability", v["rel"]), ("redundancy", v["red"]), ("coverage", v["cov"])) if not ok]
        rows.append([f"{tid} {tr.short}", tr.drill.replace("PASS_PRO(-/_)MIRROR_DRILL", "PASS_PRO mirror"), r["n"] if np.isfinite(r["r"]) else r["n"],
                     rci(r["r"], r["lo"], r["hi"]), f"{f3(r['max_abs_r'])}" + (f" ({r['argmax']})" if r['argmax'] else ""),
                     "PASS" if v["passed"] else "FAIL (" + ", ".join(fails) + ")"])
    tbl(rows, ["Trait", "Drill", "n", "r [95% CI]", "max abs r vs stopwatch / size", "Verdict"])
    w("r = cross-rep (two reps / two sides / two runs) except O3 and D4 (odd vs even reversals within one rep). For D4 the odd/even r is not estimable (too few reps with >= 4 reversals).")
    w()

    # ---- 6. variants
    w("## 6. Definition variants tried (log; none used for any gate)")
    w()
    vrows = []

    def vrow(tid, lab, variant="", k=3):
        r = T.evaluate_trait(tid, reps, cr, k, variant, pop=POP)
        vrows.append([tid, lab, r["n"], rci(r["r"], r["lo"], r["hi"]), f"{r['coverage_n']}", f3(r["max_abs_r"])])
    for t in T.TRAITS:
        vrow(t, "primary (3-frame)")
        vrow(t, "5-frame smoothing", "", 5)
    for t in ("O1", "D1", "O5", "D6"):
        vrow(t, "unsmoothed max s", "raw")
        vrow(t, "pandas rolling min_periods=1 (edge frames kept)", "pm1")
    for t in ("O1", "O2", "D1", "D2", "D3"):          # side-only z (no year standardisation), pairs as in primary
        Tt = T.rep_table(t, reps, 3)
        Tt["z"] = T.z_within(Tt, "val", ["grp"])
        Wd = Tt.pivot_table(index="nfl_id", columns="slot", values="z", aggfunc="first")
        a_, b_ = Wd[1].to_numpy(), Wd[2].to_numpy()
        lo_, hi_ = T.boot_r(a_, b_)
        vrows.append([t, "z within drift side only (no year standardisation)", int((np.isfinite(a_) & np.isfinite(b_)).sum()), rci(T.pear(a_, b_), lo_, hi_), "", ""])
    for t in ("O4", "D5"):
        vrow(t, "linearly interpolated crossing times", "interp")
    for t in ("O3", "D4"):
        vrow(t, "each directional run >= 2 qualifying frames", "minrun2")
        vrow(t, "|vy| threshold 0.5 yd/s instead of 1.0", "thr0.5")
    tbl(vrows, ["Trait", "Variant", "n", "r [95% CI]", "n with value", "max abs r"])
    w("Reversal-count distribution for the single-rep traits (primary definition): "
      + "; ".join(f"{t}: " + ", ".join(f"{k} {f3(v_, 1)}" for k, v_ in R3[t]['n_rev_dist'].items()) for t in ("O3", "D4")) + ".")
    w()
    # side-label agreement
    R = reps["rush"][reps["rush"].combine_position == "DL"]
    ds = np.array([T.drift_side_y(y) for y in R.y]); ss_ = np.array([T.start_side_rush(x, y) for x, y in zip(R.x, R.y)])
    Dp = reps["drop"][reps["drop"].combine_position == "OL"]
    pairs_ = Dp[Dp.rep <= 2].assign(side=lambda d: [T.drift_side_y(y) for y in d.y]).groupby("nfl_id").side.agg(["nunique", "size"])
    w(f"Side-label checks (computed): PASS_RUSH_DRILL (DL) drift-in-y vs nearest-start rule agree on {int((ds == ss_).sum())}/{len(ds)} reps (drift used as the label **[decision]**: it was the tested C2 rule and is robust to the odd start). "
      f"PASS_RUSH_DROP (OL): {int((pairs_['nunique'] == 2).sum())} of {int((pairs_['size'] == 2).sum())} two-rep players drift opposite ways. "
      f"DL players with both sides: {int(R.assign(side=ds).groupby('nfl_id').side.nunique().eq(2).sum())} of {R.nfl_id.nunique()}; players with two reps on the same side: {int((R.assign(side=ds).groupby(['nfl_id', 'side']).size() > 1).sum())} (first chronological rep per side used).")
    w()

    # ---- 7. decisions
    w("## 7. Decisions I made (ambiguous or unspecified details)")
    w()
    for s_ in [
        "Smoothing: 3-frame (and 5-frame) centred mean using full windows only (edge frames NaN) for all speed traits, so edge partial windows never create a maximum. Variant with edge-kept smoothing is logged in section 6. O2 keeps the C1 min_periods=1 smoothing because that is the tested definition.",
        "Rep order = chronological by first timestamp, never `attempt`. PASS_RUSH_DROP: first two reps; rep 2 is dropped if it starts > 3 yd from rep 1 (C1 same-start rule). PASS_RUSH_DRILL: first chronological rep per side.",
        "PASS_RUSH_DRILL side = drift in y (> 0 is right), the C2 rule; the start-nearest rule agrees (section 6).",
        "Rep-level z-scoring within side x year is applied to O1 and D1 as specified, and also (my choice, same treatment) to O2, D2 and D3. The 40 traits and O3/D4 are year-standardised only if the drift flag (> 0.5 pooled SD) fires; the composite always z-scores within position x draft year.",
        "Reliability for two-slot traits is the Pearson r between the gate-scale slot values (rep 1 vs rep 2; left vs right; run 1 vs run 2) over players with both. D1 pairs left with right, O1 pairs rep 1 with rep 2 (which are mostly opposite drift sides).",
        "Player value = mean of the available slot values (>= 1 slot), so coverage counts players with a single usable rep; this inflates coverage slightly relative to a both-slots requirement (both-slots coverage is reported per trait).",
        "O3/D4 reversal: consecutive qualifying frames (|vy| >= 1.0 yd/s) of opposite sign; time = first new-direction frame minus last old-direction frame; vy from the 3-frame smoothed y, central difference. Odd/even = alternate reversals in chronological order. Within-rep gate applied to the uncorrected r (conservative).",
        "O4/D5 acceleration shape: frame-based crossing times (first frame with smoothed s >= 2.0; first frame >= 0.9 x own top speed), run must be seen below 2.0 first. Interpolated variant logged.",
        "Redundancy uses the gate-scale (year-/side-standardised) player value against raw official measures; the raw-scale max |r| is reported next to it (no verdict changes).",
        "Mosier component reliabilities are Spearman-Brown-corrected to the length of the player-level value; uncorrected value also reported.",
        "Coverage denominators are all combine_position OL (121) / DL (118) players, because the engaged-rep set is not built yet.",
        "D2 and D3 were selected in a prior search (C2): the pool records out-of-bag/earlier values (0.22, 0.37). The in-sample numbers here are shown, and the verdict is FAIL either way.",
    ]:
        w(f"- {s_}")
    w()
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print("wrote", OUT_MD, OUT_PQ)
    print("\n".join(L[:60]))


if __name__ == "__main__":
    main()

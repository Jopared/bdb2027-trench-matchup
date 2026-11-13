# C3 feasibility: the rep matchup (gates G1 and G2)

Code: `scripts/feasibility/c3_rep_matchup.py` (all numbers below are printed by that script). Aggregates only. "Verified" means computed by the script; "inference" is marked.

## Method as run
- Pairs: REG+POST dropbacks (`pass_result <> ''`), `lined_up_position <> 'NA'`; blocker = `pressure_allowed` non-null; rusher = `blitzing == True`, opposing `team_abbr`. The unfiltered pair table reproduces candidates.md section 4 exactly (REG 27,747 pairs / 15,646 plays / 127 blockers / 159 rushers / 2,376 OL pressure pairs; PRE 6,533; POST 1,524). POST adds 1,524 pairs (35 OL, 47 rushers).
- Tracking is 10 Hz (every frame gap is 100 ms). Window = snap + 0.2 s to the earliest of snap + 3.0 s, `pass_forward`, `qb_sack` (first tagged frame among the loaded players; `qb_strip_sack` is not used). Windows run 4 to 29 frames (median 27). Two plays lacked `ball_snap` and were dropped (29,269 of 29,271 pairs kept; 73 of those have no overlapping frames and count as non-engaged).
- Distance is x/y Euclidean between the two players at equal timestamps. Engaged = at least k frames with d <= threshold.
- Penalty-nullified plays were kept (coherence changes by under 0.001 when they are removed).

## G1: engagement and coherence (REG+POST, verified)

| variant | engaged reps | of which REG | distinct OL | distinct rushers | OL with >=10 | rushers with >=10 | OL pressure given engaged | coherence, engaged | coherence, non-engaged | ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| **1.5 yd / 4 fr (primary)** | **8,271** | 7,840 | 107 | 129 | **70** | **82** | 9.5% | **79.7%** (n=787) | **19.3%** (n=1,725) | **4.1x** |
| 1.25 / 4 | 7,290 | 6,926 | 105 | 122 | 70 | 79 | 9.7% | 84.6% | 20.1% | 4.2x |
| 2.0 / 4 | 10,246 | 9,709 | 109 | 134 | 73 | 89 | 9.0% | 72.2% | 18.3% | 3.9x |
| 1.5 / 3 | 8,539 | 8,088 | 108 | 130 | 71 | 83 | 9.4% | 79.0% | 19.0% | 4.2x |
| 1.5 / 6 | 7,599 | 7,209 | 106 | 122 | 70 | 79 | 9.7% | 82.7% | 19.7% | 4.2x |

Coherence = P(rusher `time_to_pressure` non-null | OL `pressure_allowed`) within the pair class. Primary 95% CI (1,000 play-cluster bootstrap resamples, seed 2027): engaged 76.9-82.4%, non-engaged 17.3-21.2%. REG only: 79.6% (n=744) vs 18.8% (n=1,632). Reverse direction: P(rusher pressure | engaged, OL not pressured) = 2.3% vs 9.7% non-engaged; P(OL pressure | engaged, rusher pressured) = 78.2% vs 15.1%.

Double teams (primary): 536 of 7,154 engaged plays (7.5%) have more than one cohort OL engaged with the same rusher; 547 of 7,710 engaged (play, rusher) units (7.1%). The share ranges 5.6% (1.25 yd) to 10.8% (2.0 yd). A cohort-only count understates true double teams (non-cohort blockers are untracked). Only 249 of 8,018 (play, OL) units have more than one engaged cohort rusher.

Engagement rate among all pairs is 28.3% (8,271 / 29,269), inside the document's 25-40% guess. It does not vary by season (29%, 28%, 28% for 2023/24/25).

**G1 verdict: PASS on every threshold, for all five variants.** The thresholds were >= 4,000 reps (8,271), >= 60 OL and >= 60 rushers with >= 10 reps (70 and 82), coherence >= 40% and >= 2x (79.7%, 4.1x).

Caveats (inference unless stated):
- The coherence statistic is partly mechanical. The tracking-based definition and the NGS pressure attribution probably both reflect "this rusher was on this blocker", so 80% shows the definition picks up real matchups; it does not show that the engaged rusher caused the pressure.
- The "non-engaged" rate of 19.3% is far above the 10% base rate, so misses are common (pressure attributed to a rusher who was not within 1.5 yd for 4 frames, for example a stunt or a wider rusher).
- Engaged reps raise the OL pressure rate only a little (9.5% vs 8.2%) (verified). Pressure is a rare event (about 790 pressured engaged reps), which matters for any rep-level model that adds interactions.
- Threshold-sensitive quantities are the double-team share and the count, not the gate verdict.

## G2: power check (verified)

Logistic regression of OL `pressure_allowed` on z(rusher pick - OL pick), z(rusher weight - OL weight) and `dropback_duration`, cluster-robust SE by OL. Undrafted = 262 (127 of 510 cohort players); no missing weights or dropback durations, so no rows were dropped. SD of the pick difference is 96.3 picks and of the weight difference 32.7 lb.

Primary (engaged reps, 1.5 yd / 4 fr), n = 8,271, 107 OL clusters, 129 rushers, 787 pressured reps:

| term | coef | SE (by OL) | p | odds ratio |
|---|---|---|---|---|
| const | -4.274 | 0.122 | < 0.001 | |
| z pick differential | **-0.204** | 0.049 | **< 0.001** (z = -4.20) | 0.816 per SD |
| z weight differential | -0.214 | 0.045 | < 0.001 | 0.808 per SD |
| dropback_duration | 0.577 | 0.032 | < 0.001 | 1.78 per second |

**Sign convention (the document is ambiguous here).** The differential is rusher pick minus OL pick and a lower pick number is a better prospect, so "better-drafted rusher means more pressure allowed" implies a **negative** coefficient. That is what is observed. The decomposition agrees: rusher pick -0.185 (SE 0.051, p < 0.001, better-drafted rusher means more pressure) and OL pick +0.109 (SE 0.045, p = 0.015, better-drafted OL means less).

Robustness (all verified, pick coefficient with p < 0.001 unless noted): SE clustered by rusher 0.047; two-way (OL and rusher) clustered SE 0.051 (p = 0.0001); T/G/C blockers only -0.210 (n = 8,202, 79 OL); REG only -0.203 (n = 7,840); the four engagement variants -0.201 to -0.219; without the dropback control -0.187; with rusher-position (EDGE / interior / other) and blocker-position dummies -0.202 (SE 0.047). By blocker position: T -0.245 (p < 0.001), G -0.206 (p = 0.006), C -0.194 (SE 0.138, p = 0.16, n = 832).

Other findings:
- The weight differential has an unexpected-looking sign (heavier rusher relative to blocker, less pressure allowed). It is confounded by position: with rusher-position and blocker-position dummies it falls to -0.066 (p = 0.32). Read it as a position artefact, not a size effect. The pick effect survives the position controls. (The decomposition and position-split conclusions are verified; the "artefact" reading is inference.)
- Engagement filtering matters: on all co-occurring pairs the pick coefficient is -0.110 (SE 0.032) and the weight coefficient -0.047; on non-engaged pairs -0.075 (p = 0.03) and +0.011. The effect is about 2x larger on engaged reps, which supports the engagement definition. The non-engaged pick effect is not zero (inference: misclassified reps, or rushers who are better-drafted also produce pressure on other blockers).
- Secondary outcome, rusher pressure on the same model: pick -0.220 (SE 0.050), weight -0.269 (SE 0.044), clustered by rusher.

**G2 verdict: PASS.** The pick differential has the expected sign at p < 0.001. This is a known, mostly player-level effect, so it tests power of the rep-level design, not the Combine tracking hypothesis.

## Notes for using C3 as an opponent-adjustment module (verified unless marked)

- **Seasons.** Engaged reps: 2023 = 440, 2024 = 2,093, 2025 = 5,738 (69% from 2025). OL with >= 10 engaged reps within a single season: 15 (2023), 37 (2024), 62 (2025). Any analysis stratified by season would be thin before 2025.
- **Players.** Counts per player are heavily skewed. Per OL: min 1, quartiles 3 / 57 / 123, max 317. Per rusher: min 1, quartiles 5 / 29 / 84, max 344. The top 10 OL hold 31% of engaged reps and the top 10 rushers 34%. 1,491 distinct OL-by-rusher dyads occur, 1,089 of them with two or more reps (so crossed random effects are estimable).
- **Blocker type.** Of 8,271 engaged reps, 8,202 (99.2%) are T/G/C; TE 59, slot WR 7, WR 2, FB 1. Only 79 distinct T/G/C OL appear (107 counting TE/WR/FB). T/G/C-only gives 70 OL and 80 rushers with >= 10 reps. Engagement rate by blocker: G 28.9%, T 28.5%, C 26.5%, TE 15.9%. Restricting to TE/WR/FB loses 69 reps.
- **Rusher type.** `blitzing == True` is not only DL. Engaged reps by rusher position: interior line 4,614, edge 3,561, OLB 33, MLB 21, slot CB 39, CB 2, safety 1 (96 non-DL, 1.2%). Engagement rate: interior 35.3% vs edge 23.2%. The blocker/rusher position mix therefore differs between engaged and non-engaged pairs, so an opponent-adjustment model must include position.
- **Coverage.** The cohort OL who ever appear engaged is 79 T/G/C of about 120 OL in the cohort (inference on the 120; cohort OL count is from candidates.md). The adjustment module covers a rusher or OL only if they have enough engaged reps. About 70 and 80 clear 10 reps, so roughly 55-65% of cohort OL and a minority of the 510 overall.
- **Pressure rarity.** About 790 pressured engaged reps in total. A mixed model with trait interactions will have limited power; the continuous `peak_pressure_probability_allowed` outcome would help (not tested here).

## What the candidate document got wrong or left ambiguous

1. Section 4 counts verified exactly; nothing wrong there. Its "perhaps 25-40% engaged" guess is right (28.3%).
2. "Blockers include some TE/WR": true but tiny (0.8% of engaged reps).
3. The G2 wording "expected sign (better-drafted rusher means more pressure)" does not say that the expected coefficient on (rusher pick - OL pick) is negative, because lower pick = better. A reader testing for a positive coefficient would call it a failure.
4. The "rusher" definition (`blitzing == True`) includes about 3.2% non-DL positions among all pairs (872 of 29,269; 96 of the engaged reps, 1.2%), and `blitzing` is null on 3 blocker rows.
5. Section 4's "OL pressures allowed" count is a count of pair rows, not of distinct pressured blocker snaps (a blocker can appear in several pairs per play). Not an error, but a reader may mistake it for distinct events.
6. The tracking window ends at `pass_forward` or `qb_sack`. Plays without `pass_forward` (scrambles and sacks, about 12% of plays) rely on the 3.0 s cap or the sack tag. Engagement is therefore observed over a shorter window on quick-pressure plays (inference: a mild bias toward fewer qualifying frames on exactly the plays with pressure; the coherence result was strong regardless).

## Overall

| Gate | Value | n | Verdict |
|---|---|---|---|
| G1 reps >= 4,000 | 8,271 (REG 7,840) | 29,269 pairs | pass |
| G1 OL with >= 10 reps >= 60 | 70 (T/G/C only 70) | 107 OL | pass |
| G1 rushers with >= 10 reps >= 60 | 82 (DL-type only 79) | 129 | pass |
| G1 coherence >= 40% and >= 2x | 79.7% vs 19.3%, 4.1x | 787 / 1,725 OL-pressure pairs | pass |
| G2 pick differential sign and p < 0.05 | coef -0.204 (SE 0.049), p < 0.001 | 8,271 reps, 107 OL clusters | pass |

C3 clears both feasibility gates and the verdicts do not depend on the engagement threshold. The weakest points are the 2025 concentration, the skewed per-player counts, and the rarity of pressure.

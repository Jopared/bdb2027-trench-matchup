# Trait qualification (step 1 of the pre-registered design)

Applies the fixed pool O1-O5 / D1-D6 and the fixed gates of `reports/candidates_v2.md` section 3.2 to Combine tracking and Combine results only. No NFL outcome, `player_play` or game tracking was read. Every number below is **computed** by `scripts/trait_qualification.py` using `src/bdb2027/traits.py` (bootstrap: 2,000 resamples over players, seed 2027, percentile CI). Items I had to decide are tagged **[decision]**; the full list is in section 7. Gates are applied mechanically; no definition was tuned.

Side sizes (combine_position): OL 121, DL 118. **Registered coverage gate** (rule 4) is measured against the engaged-rep set (`engaged_pairs.parquet`, engaged_primary): blockers = distinct blocker_nfl_id lined up T/G/C with combine_position OL (**79**); rushers = distinct rusher_nfl_id with combine_position DL (**97**). Coverage against all combine players is also shown and labelled 'all-players'. No outcome column was read.

## 0. Headline

- **OL composite = {O3}** (mirror reversal time).
- **DL composite = {D1}** (rush-drill peak speed).
- Three verdicts sit on a knife edge and decide the composition: **O1** r = 0.505 [0.293, 0.685], bootstrap lower bound 0.293 vs the 0.30 bar (point estimate passes, CI fails by 0.007); **O4** and **D5** pass reliability and redundancy but fail coverage at 63/79 = 79.7% of engaged blockers (OL) and 77/97 = 79.4% of engaged rushers (DL) against the 80% bar (registered engaged-rep-set populations; all-players coverage was 78.5% / 78.8%, i.e. the correction moved them closer but not over; the 40 exists for 95/121 OL, 93/118 DL). Under the rule as written all three are out. Sensitivity composites that admit them are provided in the parquet (`composite_sensA`, `composite_sensB`) and section 2, clearly separate from the registered composite.
- D4 cannot be evaluated as defined: the wave drill is one forward start plus one lateral reaction, so almost no rep has >= 4 reversals (n with a value = 2 of 97 engaged rushers).
- **O3 (the only OL component) is smoothing-fragile:** odd/even r = 0.704 [0.473, 0.842] with 3-frame smoothing but 0.570 [0.426, 0.697] with 5-frame smoothing (below the 0.60 bar), and 0.580 / 0.473 under the min-run-2 and 0.5 yd/s threshold variants (section 6). The registered (3-frame) verdict is PASS; the sensitivity would FAIL, which would leave OL with no passing trait (primary hypothesis then DL-only per rule 6).
- The 40-yard acceleration-shape coverage question (246/375) could not be reproduced: the specified definition yields a value for 373/375 pairs (the 2 exceptions are TE runs that already exceed 2.0 yd/s at the first frame), and for all 84 OL and all 84 DL pairs (section 3).

## 1. Gate table (3-frame smoothing; primary)


| ID | Side | Trait | Reliability type | n pairs | r [95% CI] | max abs r (measure) | Coverage (engaged set) | Reliability gate | Redundancy gate | Coverage gate | Overall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 | OL | drop peak speed | cross-rep | 118 | 0.505 [0.293, 0.685] | 0.432 (forty) | 78/79 = 98.7% (all-players 99.2%) | FAIL | PASS | PASS | FAIL |
| O2 | OL | drop open_and_run | cross-rep | 116 | 0.358 [0.190, 0.511] | 0.341 (forty) | 78/79 = 98.7% (all-players 99.2%) | FAIL | PASS | PASS | FAIL |
| O3 | OL | mirror reversal time | odd/even | 105 | 0.704 [0.473, 0.842] | 0.320 (three_cone) | 69/79 = 87.3% (all-players 86.8%) | PASS | PASS | PASS | **PASS** |
| O4 | OL | 40 acceleration shape | cross-rep | 84 | 0.708 [0.508, 0.833] | 0.276 (ten_yd_split) | 63/79 = 79.7% (all-players 78.5%) | PASS | PASS | FAIL | FAIL |
| O5 | OL | 40 top speed | cross-rep | 84 | 0.924 [0.889, 0.952] | 0.907 (forty) | 63/79 = 79.7% (all-players 78.5%) | PASS | FAIL | FAIL | FAIL |
| D1 | DL | rush-drill peak speed | cross-rep | 106 | 0.639 [0.408, 0.812] | 0.715 (forty) | 97/97 = 100.0% (all-players 100.0%) | PASS | PASS | PASS | **PASS** |
| D2 | DL | rush turn_min_speed | cross-rep | 92 | 0.415 [0.178, 0.602] | 0.278 (ten_yd_split) | 97/97 = 100.0% (all-players 100.0%) | FAIL | PASS | PASS | FAIL |
| D3 | DL | rush get_off | cross-rep | 84 | 0.369 [0.153, 0.577] | 0.387 (forty) | 93/97 = 95.9% (all-players 96.6%) | FAIL | PASS | PASS | FAIL |
| D4 | DL | wave reversal time | odd/even | 2 | n/a | n/a () | 2/97 = 2.1% (all-players 1.7%) | FAIL | FAIL | FAIL | FAIL |
| D5 | DL | 40 acceleration shape | cross-rep | 84 | 0.529 [0.349, 0.681] | 0.291 (forty) | 77/97 = 79.4% (all-players 78.8%) | PASS | PASS | FAIL | FAIL |
| D6 | DL | 40 top speed | cross-rep | 84 | 0.976 [0.963, 0.985] | 0.978 (forty) | 77/97 = 79.4% (all-players 78.8%) | PASS | FAIL | FAIL | FAIL |

Gate rules as applied: reliability = cross-rep r >= 0.50 and bootstrap lower bound >= 0.30 (two-slot traits), or odd/even within-rep r >= 0.60 (O3, D4; **[decision]** uncorrected r is gated, Spearman-Brown value reported alongside; the 0.30 CI-bound is not required for within-rep traits, per the pool text); redundancy = all |r| < 0.75 vs forty, ten_yd_split, short_shuttle, three_cone (n >= 30 only), combine_weight, arm_length, within the side; coverage = share of the side's engaged-rep-set players (79-ish blockers / rushers, see above) with a trait value (any rep).

### 1a. Per-trait detail

#### O1 (OL, PASS_RUSH_DROP): drop peak speed

- **Definition as implemented:** Whole-rep max of the 3-frame centred-mean speed (edge frames excluded); each rep z-scored within drift side (sign of y_end - y_start) x draft year; player value = mean of the (up to) two rep z-scores.
- Orientation: higher raw value = more athletic; composite uses + z.
- Reps: 238 rep/slot values; pairs with both slots: 118; players with >= 1 value (all players): 120 of 121.
- Cross-rep r on the gate scale = 0.505 [0.293, 0.685] (n = 118); Spearman-Brown two-rep-mean reliability = 0.671. r without year standardisation = 0.567; r on raw values = 0.539 (raw values mix drift sides, shown for completeness).
- 5-frame smoothing: r = 0.461 [0.227, 0.659] (n = 118); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = side-standardised z): 2023: -0.80, 2024: 0.32, 2025: 0.42; max 0.80 -> FLAG (> 0.5). Year means: 2023: mean -0.464, SD 0.974, n 36; 2024: mean 0.165, SD 0.875, n 46; 2025: mean 0.240, SD 0.599, n 38.
- Year standardisation applied to gate-scale values: **yes** (prescribed (side x year z is part of the definition)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.432 (n 94), ten_yd_split -0.374 (n 95), short_shuttle -0.134 (n 64), three_cone -0.212 (n 61), combine_weight -0.078 (n 120), arm_length 0.017 (n 120). **max |r| = 0.432 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.426.
- Coverage (engaged-rep set, registered gate): 78/79 = 98.7%; all-players coverage: 120/121 = 99.2%; players with both slots: 118.
- **Verdicts:** reliability FAIL (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage PASS -> **FAIL**.

#### O2 (OL, PASS_RUSH_DROP): drop open_and_run

- **Definition as implemented:** C1 open_and_run: onset = first of 3 consecutive frames with smoothed s >= 0.5; time from s >= 2.0 (searched from onset + 1.8 s) to s >= 4.5 yd/s (linear-interpolated crossings, C1 min_periods=1 smoothing). Seconds; lower = more athletic. Z within drift side x year (decision, same treatment as O1).
- Note: Depends on the inferred 'open hips and run' phase timing (onset + 1.8 s).
- Orientation: lower raw value = more athletic; composite uses - z.
- Reps: 238 rep/slot values; pairs with both slots: 116; players with >= 1 value (all players): 120 of 121.
- Cross-rep r on the gate scale = 0.358 [0.190, 0.511] (n = 116); Spearman-Brown two-rep-mean reliability = 0.527. r without year standardisation = 0.343; r on raw values = 0.344 (raw values mix drift sides, shown for completeness).
- 5-frame smoothing: r = 0.348 [0.184, 0.500] (n = 116); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = side-standardised z): 2023: 1.05, 2024: -0.42, 2025: -0.56; max 1.05 -> FLAG (> 0.5). Year means: 2023: mean 0.589, SD 1.050, n 36; 2024: mean -0.181, SD 0.694, n 46; 2025: mean -0.273, SD 0.454, n 38.
- Year standardisation applied to gate-scale values: **yes** (applied by [decision], same treatment as O1/D1). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty 0.341 (n 94), ten_yd_split 0.244 (n 95), short_shuttle 0.058 (n 64), three_cone 0.155 (n 61), combine_weight 0.128 (n 120), arm_length 0.108 (n 120). **max |r| = 0.341 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.335.
- Coverage (engaged-rep set, registered gate): 78/79 = 98.7%; all-players coverage: 120/121 = 99.2%; players with both slots: 116.
- **Verdicts:** reliability FAIL (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage PASS -> **FAIL**.

#### O3 (OL, PASS_PRO(-/_)MIRROR_DRILL): mirror reversal time

- **Definition as implemented:** Median lateral reversal time of the single rep: vy = centred difference of 3-frame smoothed y; reversal = consecutive frames with |vy| >= 1.0 yd/s of opposite sign, time = first frame in the new direction minus last frame in the old direction. Needs >= 4 reversals. Lower = more athletic. Reliability = odd- vs even-numbered reversals (median of each half).
- Orientation: lower raw value = more athletic; composite uses - z.
- n players with a value (>= 4 reversals; all players): 105 of 121; players with a rep: 121. Reversals per rep: count 121.00, mean 4.19, std 0.87, min 2.00, 25% 4.00, 50% 4.00, 75% 5.00, max 7.00.
- Within-rep odd vs even reversal r = 0.704 [0.473, 0.842] (n = 105); Spearman-Brown full-length r = 0.826.
- 5-frame smoothing: r = 0.570 [0.426, 0.697] (n = 104); verdict CHANGES to FAIL.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2023: -0.21, 2024: 0.14, 2025: 0.08; max 0.21 -> no flag. Year means: 2023: mean 0.482, SD 0.061, n 37; 2024: mean 0.499, SD 0.096, n 39; 2025: mean 0.497, SD 0.060, n 29.
- Year standardisation applied to gate-scale values: **no** (not applied (no flag)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty 0.281 (n 83), ten_yd_split 0.315 (n 84), short_shuttle 0.259 (n 56), three_cone 0.320 (n 52), combine_weight 0.142 (n 105), arm_length -0.073 (n 105). **max |r| = 0.320 (three_cone)**; on the raw (non-year-standardised) trait scale max |r| = 0.320.
- Coverage (engaged-rep set, registered gate): 69/79 = 87.3%; all-players coverage: 105/121 = 86.8%.
- **Verdicts:** reliability PASS (within-rep odd/even r >= 0.60); redundancy PASS; coverage PASS -> **PASS**.

#### O4 (OL, FORTY_YARD_DASH): 40 acceleration shape

- **Definition as implemented:** Time (s) from the first frame with 3-frame smoothed s >= 2.0 yd/s (run must be seen below 2.0 first) to the first frame at >= 0.9 x that run's own top speed (max of smoothed s); mean over the two runs. Lower = more athletic.
- Orientation: lower raw value = more athletic; composite uses - z.
- Reps: 179 rep/slot values; pairs with both slots: 84; players with >= 1 value (all players): 95 of 121.
- Cross-rep r on the gate scale = 0.708 [0.508, 0.833] (n = 84); Spearman-Brown two-rep-mean reliability = 0.829. r without year standardisation = 0.708; r on raw values = 0.708.
- 5-frame smoothing: r = 0.615 [0.450, 0.753] (n = 77); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2023: 0.18, 2024: -0.04, 2025: -0.14; max 0.18 -> no flag. Year means: 2023: mean 2.333, SD 0.183, n 30; 2024: mean 2.300, SD 0.288, n 37; 2025: mean 2.282, SD 0.200, n 28.
- Year standardisation applied to gate-scale values: **no** (not applied (no flag)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.038 (n 95), ten_yd_split 0.276 (n 95), short_shuttle 0.142 (n 59), three_cone 0.144 (n 59), combine_weight 0.130 (n 95), arm_length 0.159 (n 95). **max |r| = 0.276 (ten_yd_split)**; on the raw (non-year-standardised) trait scale max |r| = 0.276.
- Coverage (engaged-rep set, registered gate): 63/79 = 79.7%; all-players coverage: 95/121 = 78.5%; players with both slots: 84.
- **Verdicts:** reliability PASS (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage FAIL -> **FAIL**.

#### O5 (OL, FORTY_YARD_DASH): 40 top speed

- **Definition as implemented:** Max of the 3-frame smoothed s within the run (yd/s); mean over the two runs. Higher = more athletic.
- Orientation: higher raw value = more athletic; composite uses + z.
- Reps: 179 rep/slot values; pairs with both slots: 84; players with >= 1 value (all players): 95 of 121.
- Cross-rep r on the gate scale = 0.924 [0.889, 0.952] (n = 84); Spearman-Brown two-rep-mean reliability = 0.960. r without year standardisation = 0.924; r on raw values = 0.924.
- 5-frame smoothing: r = 0.925 [0.894, 0.951] (n = 84); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2023: 0.02, 2024: 0.01, 2025: -0.04; max 0.04 -> no flag. Year means: 2023: mean 9.401, SD 0.422, n 30; 2024: mean 9.399, SD 0.305, n 37; 2025: mean 9.386, SD 0.329, n 28.
- Year standardisation applied to gate-scale values: **no** (not applied (no flag)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.907 (n 95), ten_yd_split -0.549 (n 95), short_shuttle -0.386 (n 59), three_cone -0.389 (n 59), combine_weight -0.024 (n 95), arm_length 0.054 (n 95). **max |r| = 0.907 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.907.
- Coverage (engaged-rep set, registered gate): 63/79 = 79.7%; all-players coverage: 95/121 = 78.5%; players with both slots: 84.
- **Verdicts:** reliability PASS (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy FAIL; coverage FAIL -> **FAIL**.

#### D1 (DL, PASS_RUSH_DRILL): rush-drill peak speed

- **Definition as implemented:** Whole-rep max of the 3-frame centred-mean speed (edge frames excluded); each rep z-scored within side (left/right by drift in y) x draft year; player value = mean of the first chronological left and right rep z-scores (>=1 rep).
- Orientation: higher raw value = more athletic; composite uses + z.
- Reps: 224 rep/slot values; pairs with both slots: 106; players with >= 1 value (all players): 118 of 118.
- Cross-rep r on the gate scale = 0.639 [0.408, 0.812] (n = 106); Spearman-Brown two-rep-mean reliability = 0.780. r without year standardisation = 0.642; r on raw values = 0.642 (raw values mix drift sides, shown for completeness).
- 5-frame smoothing: r = 0.638 [0.404, 0.813] (n = 106); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = side-standardised z): 2023: 0.62, 2024: -0.60, 2025: -0.01; max 0.62 -> FLAG (> 0.5). Year means: 2023: mean 0.367, SD 0.946, n 37; 2024: mean -0.356, SD 0.759, n 37; 2025: mean -0.004, SD 0.871, n 44.
- Year standardisation applied to gate-scale values: **yes** (prescribed (side x year z is part of the definition)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.715 (n 94), ten_yd_split -0.634 (n 94), short_shuttle -0.509 (n 46), three_cone -0.616 (n 43), combine_weight -0.628 (n 118), arm_length -0.000 (n 118). **max |r| = 0.715 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.706.
- Coverage (engaged-rep set, registered gate): 97/97 = 100.0%; all-players coverage: 118/118 = 100.0%; players with both slots: 106.
- **Verdicts:** reliability PASS (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage PASS -> **PASS**.

#### D2 (DL, PASS_RUSH_DRILL): rush turn_min_speed

- **Definition as implemented:** C2 turn_min_speed (run reference heading, 15-60 deg window): min smoothed s while the heading has turned 15 -> 60 deg from the initial run heading. Z within side x year (decision).
- Orientation: higher raw value = more athletic; composite uses + z.
- Reps: 224 rep/slot values; pairs with both slots: 92; players with >= 1 value (all players): 118 of 118.
- Cross-rep r on the gate scale = 0.415 [0.178, 0.602] (n = 92); Spearman-Brown two-rep-mean reliability = 0.586. r without year standardisation = 0.451; r on raw values = 0.451 (raw values mix drift sides, shown for completeness).
- 5-frame smoothing: r = 0.393 [0.177, 0.581] (n = 90); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = side-standardised z): 2023: 0.94, 2024: -0.49, 2025: -0.41; max 0.94 -> FLAG (> 0.5). Year means: 2023: mean 0.551, SD 0.745, n 37; 2024: mean -0.319, SD 1.133, n 37; 2025: mean -0.248, SD 0.704, n 44.
- Year standardisation applied to gate-scale values: **yes** (applied by [decision], same treatment as O1/D1). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.235 (n 94), ten_yd_split -0.278 (n 94), short_shuttle -0.233 (n 46), three_cone -0.238 (n 43), combine_weight -0.099 (n 118), arm_length 0.015 (n 118). **max |r| = 0.278 (ten_yd_split)**; on the raw (non-year-standardised) trait scale max |r| = 0.228.
- Coverage (engaged-rep set, registered gate): 97/97 = 100.0%; all-players coverage: 118/118 = 100.0%; players with both slots: 92.
- Pool records out-of-bag r = 0.22 (selected from a search in C2); the in-sample number computed here is optimistic.
- **Verdicts:** reliability FAIL (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage PASS -> **FAIL**.

#### D3 (DL, PASS_RUSH_DRILL): rush get_off

- **Definition as implemented:** C2 get_off: threshold-crossing time (s) from s first crossing 1.0 to s first crossing 4.0 yd/s (3-frame smoothed; NaN if s is never seen below 1.0). Lower = more athletic. Z within side x year (decision).
- Orientation: lower raw value = more athletic; composite uses - z.
- Reps: 224 rep/slot values; pairs with both slots: 84; players with >= 1 value (all players): 114 of 118.
- Cross-rep r on the gate scale = 0.369 [0.153, 0.577] (n = 84); Spearman-Brown two-rep-mean reliability = 0.539. r without year standardisation = 0.445; r on raw values = 0.445 (raw values mix drift sides, shown for completeness).
- 5-frame smoothing: r = 0.342 [0.061, 0.620] (n = 49); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = side-standardised z): 2023: -0.91, 2024: 0.11, 2025: 0.70; max 0.91 -> FLAG (> 0.5). Year means: 2023: mean -0.541, SD 0.690, n 34; 2024: mean 0.047, SD 0.944, n 36; 2025: mean 0.340, SD 0.816, n 44.
- Year standardisation applied to gate-scale values: **yes** (applied by [decision], same treatment as O1/D1). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty 0.387 (n 90), ten_yd_split 0.347 (n 90), short_shuttle 0.308 (n 43), three_cone 0.248 (n 39), combine_weight 0.346 (n 114), arm_length 0.002 (n 114). **max |r| = 0.387 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.376.
- Coverage (engaged-rep set, registered gate): 93/97 = 95.9%; all-players coverage: 114/118 = 96.6%; players with both slots: 84.
- Pool records r = 0.37 (C2).
- **Verdicts:** reliability FAIL (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage PASS -> **FAIL**.

#### D4 (DL, FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION): wave reversal time

- **Definition as implemented:** Median lateral reversal time of the single rep, same definition as O3. Needs >= 4 reversals. Lower = more athletic. Reliability = odd vs even reversals.
- Orientation: lower raw value = more athletic; composite uses - z.
- n players with a value (>= 4 reversals; all players): 2 of 118; players with a rep: 112. Reversals per rep: count 112.00, mean 2.46, std 0.57, min 1.00, 25% 2.00, 50% 2.00, 75% 3.00, max 4.00.
- Within-rep odd vs even reversal r = n/a (n = 2); Spearman-Brown full-length r = n/a.
- 5-frame smoothing: r = n/a (n = 1); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2024: n/a, 2025: n/a; max n/a -> no flag. Year means: 2024: mean 0.750, SD n/a, n 1; 2025: mean 0.450, SD n/a, n 1.
- Year standardisation applied to gate-scale values: **no** (not applied (no flag)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty n/a (n 1), ten_yd_split n/a (n 1), short_shuttle n/a (n 2), three_cone n/a (n 2) [skipped, n<30], combine_weight n/a (n 2), arm_length n/a (n 2). **max |r| = n/a ()**; on the raw (non-year-standardised) trait scale max |r| = n/a.
- Coverage (engaged-rep set, registered gate): 2/97 = 2.1%; all-players coverage: 2/118 = 1.7%.
- **Verdicts:** reliability FAIL (within-rep odd/even r >= 0.60); redundancy FAIL; coverage FAIL -> **FAIL**.

#### D5 (DL, FORTY_YARD_DASH): 40 acceleration shape

- **Definition as implemented:** Same definition as O4 (time from smoothed s >= 2.0 yd/s to 0.9 x own top speed, mean of runs). Lower = more athletic.
- Orientation: lower raw value = more athletic; composite uses - z.
- Reps: 177 rep/slot values; pairs with both slots: 84; players with >= 1 value (all players): 93 of 118.
- Cross-rep r on the gate scale = 0.529 [0.349, 0.681] (n = 84); Spearman-Brown two-rep-mean reliability = 0.692. r without year standardisation = 0.618; r on raw values = 0.618.
- 5-frame smoothing: r = 0.536 [0.376, 0.676] (n = 81); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2023: 0.11, 2024: -0.76, 2025: 0.67; max 0.76 -> FLAG (> 0.5). Year means: 2023: mean 2.279, SD 0.181, n 33; 2024: mean 2.190, SD 0.160, n 31; 2025: mean 2.340, SD 0.115, n 29.
- Year standardisation applied to gate-scale values: **yes** (applied because drift flag fired). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.291 (n 93), ten_yd_split -0.241 (n 93), short_shuttle -0.100 (n 40), three_cone -0.133 (n 38), combine_weight -0.207 (n 93), arm_length 0.066 (n 93). **max |r| = 0.291 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.272.
- Coverage (engaged-rep set, registered gate): 77/97 = 79.4%; all-players coverage: 93/118 = 78.8%; players with both slots: 84.
- **Verdicts:** reliability PASS (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy PASS; coverage FAIL -> **FAIL**.

#### D6 (DL, FORTY_YARD_DASH): 40 top speed

- **Definition as implemented:** Same definition as O5 (max smoothed s in the 40, mean of runs). Higher = more athletic.
- Orientation: higher raw value = more athletic; composite uses + z.
- Reps: 177 rep/slot values; pairs with both slots: 84; players with >= 1 value (all players): 93 of 118.
- Cross-rep r on the gate scale = 0.976 [0.963, 0.985] (n = 84); Spearman-Brown two-rep-mean reliability = 0.988. r without year standardisation = 0.976; r on raw values = 0.976.
- 5-frame smoothing: r = 0.977 [0.964, 0.986] (n = 84); verdict unchanged.
- Year drift (year mean minus mean of other years, in pooled within-year SD; scale = raw trait): 2023: 0.22, 2024: -0.14, 2025: -0.09; max 0.22 -> no flag. Year means: 2023: mean 10.108, SD 0.706, n 33; 2024: mean 9.967, SD 0.543, n 31; 2025: mean 9.988, SD 0.543, n 29.
- Year standardisation applied to gate-scale values: **no** (not applied (no flag)). The composite additionally z-scores within position x draft year.
- Redundancy |r| vs official (gate scale): forty -0.978 (n 93), ten_yd_split -0.890 (n 93), short_shuttle -0.671 (n 40), three_cone -0.673 (n 38), combine_weight -0.830 (n 93), arm_length 0.008 (n 93). **max |r| = 0.978 (forty)**; on the raw (non-year-standardised) trait scale max |r| = 0.978.
- Coverage (engaged-rep set, registered gate): 77/97 = 79.4%; all-players coverage: 93/118 = 78.8%; players with both slots: 84.
- **Verdicts:** reliability PASS (cross-rep r >= 0.50 and CI lower >= 0.30); redundancy FAIL; coverage FAIL -> **FAIL**.

## 2. Frozen side composites

Rule: equal-weighted mean of the within-position x within-draft-year z-scores (player-level trait value; oriented so higher = more athletic) of every passing trait; a player needs >= 1 component; Mosier reliability for the unit-weighted composite of standardised components: rel = 1 - sum(1 - r_ii) / (k + 2 sum_{i<j} r_ij), with r_ii = reliability of the player-level trait value (**[decision]** Spearman-Brown-corrected cross-rep or odd/even r, because the player value is a two-rep mean / full-length median) and r_ij = Pearson among players with all components. With one component the Mosier value is that component's reliability.

### OL

- Components: **O3**; definitions: O3: Median lateral reversal time of the single rep: vy = centred difference of 3-frame smoothed y; reversal = consecutive frames with |vy| >= 1.0 yd/s of opposite sign, time = first frame in the new direction minus last frame in the old direction. Needs >= 4 reversals. Lower = more athletic. Reliability = odd- vs even-numbered reversals (median of each half).
- Mosier composite reliability: **0.826** (Spearman-Brown-corrected component reliabilities ['0.826']); with uncorrected single-rep r_ii: 0.704.
- Players with a composite: **105** of 121 all combine OL players; **69** of 79 engaged-set blockers (players with all components: 105; component-count distribution {0: 16, 1: 105}).

| draft_year | n with composite | mean | SD | min | max |
|---|---|---|---|---|---|
| 2023 | 37 | -0.000 | 1.000 | -1.912 | 1.341 |
| 2024 | 39 | -0.000 | 1.000 | -4.686 | 1.025 |
| 2025 | 29 | -0.000 | 1.000 | -2.572 | 1.618 |

Players per draft year (all of the side): 2023: 37, 2024: 46, 2025: 38. (Within-year means are 0 by construction; SD is 1 for a one-component composite and < 1 when several imperfectly correlated components are averaged.)

### DL

- Components: **D1**; definitions: D1: Whole-rep max of the 3-frame centred-mean speed (edge frames excluded); each rep z-scored within side (left/right by drift in y) x draft year; player value = mean of the first chronological left and right rep z-scores (>=1 rep).
- Mosier composite reliability: **0.780** (Spearman-Brown-corrected component reliabilities ['0.780']); with uncorrected single-rep r_ii: 0.639.
- Players with a composite: **118** of 118 all combine DL players; **97** of 97 engaged-set rushers (players with all components: 118; component-count distribution {1: 118}).

| draft_year | n with composite | mean | SD | min | max |
|---|---|---|---|---|---|
| 2023 | 37 | -0.000 | 1.000 | -2.423 | 1.814 |
| 2024 | 37 | 0.000 | 1.000 | -2.630 | 1.687 |
| 2025 | 44 | -0.000 | 1.000 | -1.625 | 2.433 |

Players per draft year (all of the side): 2023: 37, 2024: 37, 2025: 44. (Within-year means are 0 by construction; SD is 1 for a one-component composite and < 1 when several imperfectly correlated components are averaged.)

### Sensitivity composites (NOT the registered composites; for the decision-maker)

- A (reliability + redundancy pass, coverage ignored): OL = {O3, O4}, DL = {D1, D5}; players with a composite: OL 117, DL 118. Correlation with registered composite: OL 0.813, DL 0.744.
- B (A plus O1, whose point r passes but CI lower bound misses 0.30): OL = {O1, O3, O4}, DL = {D1, D5}; players with a composite: OL 121, DL 118. Correlation with registered composite: OL 0.654, DL 0.744.

## 3. The 246 / 375 acceleration-shape coverage question

Computed with the specified definition (frame-based, 3-frame smoothed s, run must be seen below 2.0 first): **373 of 375 pairs have a value in both runs**; by position (pairs / with value): DB: 93/93, DL: 84/84, OL: 84/84, TE: 32/30, WR: 82/82.
At run level: 791 of 793 runs have a value (all 418 players with a 40). Frames before s first crosses 2.0: median index 4, range 1-43; second-frame smoothed s median 0.96 yd/s; every run is seen below 2.0 before crossing it (except 2 runs). The first frame at 0.9 x top speed leaves a median of 24 frames (minimum 17) before the recording ends, so nothing is right-censored.

So the specified trait does **not** go missing for non-linemen. I could not recover the prior query's implementation, so I tested the mechanisms that could plausibly produce a position-dependent shortfall (pairs retained / OL / DL retained under each):


| hypothesised cause | pairs retained (of 375) | OL retained (of 84) | DL retained (of 84) |
|---|---|---|---|
| specified definition (value in both runs) | 373 | 84 | 84 |
| pairs identified by attempt numbers 1 and 2 (numbering unreliable) | 302 | 78 | 63 |
| both-run top speed < 11.0 yd/s (speed-dependent filter) | 269 | 84 | 81 |
| both-run top speed < 10.9 yd/s (speed-dependent filter) | 242 | 84 | 81 |
| both-run top speed < 10.5 yd/s (speed-dependent filter) | 174 | 84 | 64 |
| last-frame speed >= 0.97 x top (requires run to end at top speed) | 352 | 72 | 74 |
| last-frame speed >= 0.98 x top (requires run to end at top speed) | 308 | 55 | 59 |
| run covers >= 40 yd in x | 252 | 55 | 49 |
| first-frame x < 10 | 8 | 7 | 0 |

None of these reproduces 246 with OL and DL complete. The only family that spares the slower linemen and removes the faster groups is a **speed-dependent condition** (top speeds: OL median 9.4, DL 10.1, TE 10.4, DB 11.0, WR 11.1 yd/s): the closest hit is a top-speed cap near 10.9-11.0 (242-268 pairs), but it also removes some DL, so it is not an exact match. **Conclusion (computed fact + inference):** the shortfall is not a property of the data or of the specified definition; it came from an implementation detail of the earlier ad-hoc query that interacted with speed (I could not identify which). The real coverage issue is different and binds: the 40 exists for only 95/121 OL and 93/118 DL players (11 OL and 9 DL have a single tracked run; the rest have none): all-players coverage 78.5% / 78.8%, and 63/79 = 79.7% / 77/97 = 79.4% in the registered engaged-rep populations, **just under the 80% bar either way**.

## 4. PASS_RUSH_DROP and the inferred 'open hips and run' phase

- **O1** is the whole-rep maximum of the 3-frame smoothed speed. It uses no onset, no time window and no phase boundary; the drift-side label uses only the first and last positions of the rep (sign of y_end - y_start). It therefore does not depend on the inferred phase semantics. (Computed: the peak occurs at median 4.2 s into the rep, range 2.3-7.8 s; nothing in the definition conditions on this.)
- **O2** (`open_and_run`) *does* depend on it (search window starts at onset + 1.8 s, then s 2.0 -> 4.5 yd/s). It fails the reliability gate, so it is not in any composite. Checks: OL composite components = ['O3']; no PASS_RUSH_DROP trait is among them.
- O3 uses the mirror drill and O4/O5 the 40, so none of them involves the PASS_RUSH_DROP semantics.

## 5. Reliability atlas (T1)


| Trait | Drill | n | r [95% CI] | max abs r vs stopwatch / size | Verdict |
|---|---|---|---|---|---|
| O1 drop peak speed | PASS_RUSH_DROP | 118 | 0.505 [0.293, 0.685] | 0.432 (forty) | FAIL (reliability) |
| O2 drop open_and_run | PASS_RUSH_DROP | 116 | 0.358 [0.190, 0.511] | 0.341 (forty) | FAIL (reliability) |
| O3 mirror reversal time | PASS_PRO mirror | 105 | 0.704 [0.473, 0.842] | 0.320 (three_cone) | PASS |
| O4 40 acceleration shape | FORTY_YARD_DASH | 84 | 0.708 [0.508, 0.833] | 0.276 (ten_yd_split) | FAIL (coverage) |
| O5 40 top speed | FORTY_YARD_DASH | 84 | 0.924 [0.889, 0.952] | 0.907 (forty) | FAIL (redundancy, coverage) |
| D1 rush-drill peak speed | PASS_RUSH_DRILL | 106 | 0.639 [0.408, 0.812] | 0.715 (forty) | PASS |
| D2 rush turn_min_speed | PASS_RUSH_DRILL | 92 | 0.415 [0.178, 0.602] | 0.278 (ten_yd_split) | FAIL (reliability) |
| D3 rush get_off | PASS_RUSH_DRILL | 84 | 0.369 [0.153, 0.577] | 0.387 (forty) | FAIL (reliability) |
| D4 wave reversal time | FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION | 2 | n/a | n/a | FAIL (reliability, redundancy, coverage) |
| D5 40 acceleration shape | FORTY_YARD_DASH | 84 | 0.529 [0.349, 0.681] | 0.291 (forty) | FAIL (coverage) |
| D6 40 top speed | FORTY_YARD_DASH | 84 | 0.976 [0.963, 0.985] | 0.978 (forty) | FAIL (redundancy, coverage) |

r = cross-rep (two reps / two sides / two runs) except O3 and D4 (odd vs even reversals within one rep). For D4 the odd/even r is not estimable (too few reps with >= 4 reversals).

## 6. Definition variants tried (log; none used for any gate)


| Trait | Variant | n | r [95% CI] | n with value | max abs r |
|---|---|---|---|---|---|
| O1 | primary (3-frame) | 118 | 0.505 [0.293, 0.685] | 78 | 0.432 |
| O1 | 5-frame smoothing | 118 | 0.461 [0.227, 0.659] | 78 | 0.430 |
| O2 | primary (3-frame) | 116 | 0.358 [0.190, 0.511] | 78 | 0.341 |
| O2 | 5-frame smoothing | 116 | 0.348 [0.184, 0.500] | 78 | 0.331 |
| O3 | primary (3-frame) | 105 | 0.704 [0.473, 0.842] | 69 | 0.320 |
| O3 | 5-frame smoothing | 104 | 0.570 [0.426, 0.697] | 69 | 0.320 |
| O4 | primary (3-frame) | 84 | 0.708 [0.508, 0.833] | 63 | 0.276 |
| O4 | 5-frame smoothing | 77 | 0.615 [0.450, 0.753] | 63 | 0.278 |
| O5 | primary (3-frame) | 84 | 0.924 [0.889, 0.952] | 63 | 0.907 |
| O5 | 5-frame smoothing | 84 | 0.925 [0.894, 0.951] | 63 | 0.908 |
| D1 | primary (3-frame) | 106 | 0.639 [0.408, 0.812] | 97 | 0.715 |
| D1 | 5-frame smoothing | 106 | 0.638 [0.404, 0.813] | 97 | 0.714 |
| D2 | primary (3-frame) | 92 | 0.415 [0.178, 0.602] | 97 | 0.278 |
| D2 | 5-frame smoothing | 90 | 0.393 [0.177, 0.581] | 97 | 0.269 |
| D3 | primary (3-frame) | 84 | 0.369 [0.153, 0.577] | 93 | 0.387 |
| D3 | 5-frame smoothing | 49 | 0.342 [0.061, 0.620] | 57 | 0.482 |
| D4 | primary (3-frame) | 2 | n/a | 2 | n/a |
| D4 | 5-frame smoothing | 1 | n/a | 1 | n/a |
| D5 | primary (3-frame) | 84 | 0.529 [0.349, 0.681] | 77 | 0.291 |
| D5 | 5-frame smoothing | 81 | 0.536 [0.376, 0.676] | 77 | 0.267 |
| D6 | primary (3-frame) | 84 | 0.976 [0.963, 0.985] | 77 | 0.978 |
| D6 | 5-frame smoothing | 84 | 0.977 [0.964, 0.986] | 77 | 0.978 |
| O1 | unsmoothed max s | 118 | 0.538 [0.351, 0.703] | 78 | 0.421 |
| O1 | pandas rolling min_periods=1 (edge frames kept) | 118 | 0.524 [0.327, 0.695] | 78 | 0.427 |
| D1 | unsmoothed max s | 106 | 0.640 [0.410, 0.812] | 97 | 0.717 |
| D1 | pandas rolling min_periods=1 (edge frames kept) | 106 | 0.639 [0.407, 0.812] | 97 | 0.716 |
| O5 | unsmoothed max s | 84 | 0.917 [0.871, 0.951] | 63 | 0.906 |
| O5 | pandas rolling min_periods=1 (edge frames kept) | 84 | 0.924 [0.889, 0.952] | 63 | 0.907 |
| D6 | unsmoothed max s | 84 | 0.976 [0.963, 0.985] | 77 | 0.978 |
| D6 | pandas rolling min_periods=1 (edge frames kept) | 84 | 0.976 [0.963, 0.985] | 77 | 0.978 |
| O1 | z within drift side only (no year standardisation) | 118 | 0.567 [0.389, 0.706] |  |  |
| O2 | z within drift side only (no year standardisation) | 116 | 0.343 [0.134, 0.541] |  |  |
| D1 | z within drift side only (no year standardisation) | 106 | 0.642 [0.412, 0.823] |  |  |
| D2 | z within drift side only (no year standardisation) | 92 | 0.451 [0.261, 0.619] |  |  |
| D3 | z within drift side only (no year standardisation) | 84 | 0.445 [0.243, 0.639] |  |  |
| O4 | linearly interpolated crossing times | 84 | 0.711 [0.526, 0.829] | 63 | 0.280 |
| D5 | linearly interpolated crossing times | 84 | 0.598 [0.457, 0.720] | 77 | 0.268 |
| O3 | each directional run >= 2 qualifying frames | 104 | 0.580 [0.416, 0.705] | 69 | 0.289 |
| O3 | |vy| threshold 0.5 yd/s instead of 1.0 | 111 | 0.473 [0.241, 0.642] | 73 | 0.246 |
| D4 | each directional run >= 2 qualifying frames | 2 | n/a | 2 | n/a |
| D4 | |vy| threshold 0.5 yd/s instead of 1.0 | 15 | -0.460 [-0.735, -0.117] | 13 | 0.746 |

Reversal-count distribution for the single-rep traits (primary definition): O3: count 121.0, mean 4.2, std 0.9, min 2.0, 25% 4.0, 50% 4.0, 75% 5.0, max 7.0; D4: count 112.0, mean 2.5, std 0.6, min 1.0, 25% 2.0, 50% 2.0, 75% 3.0, max 4.0.

Side-label checks (computed): PASS_RUSH_DRILL (DL) drift-in-y vs nearest-start rule agree on 225/225 reps (drift used as the label **[decision]**: it was the tested C2 rule and is robust to the odd start). PASS_RUSH_DROP (OL): 110 of 118 two-rep players drift opposite ways. DL players with both sides: 106 of 118; players with two reps on the same side: 1 (first chronological rep per side used).

## 7. Decisions I made (ambiguous or unspecified details)

- Smoothing: 3-frame (and 5-frame) centred mean using full windows only (edge frames NaN) for all speed traits, so edge partial windows never create a maximum. Variant with edge-kept smoothing is logged in section 6. O2 keeps the C1 min_periods=1 smoothing because that is the tested definition.
- Rep order = chronological by first timestamp, never `attempt`. PASS_RUSH_DROP: first two reps; rep 2 is dropped if it starts > 3 yd from rep 1 (C1 same-start rule). PASS_RUSH_DRILL: first chronological rep per side.
- PASS_RUSH_DRILL side = drift in y (> 0 is right), the C2 rule; the start-nearest rule agrees (section 6).
- Rep-level z-scoring within side x year is applied to O1 and D1 as specified, and also (my choice, same treatment) to O2, D2 and D3. The 40 traits and O3/D4 are year-standardised only if the drift flag (> 0.5 pooled SD) fires; the composite always z-scores within position x draft year.
- Reliability for two-slot traits is the Pearson r between the gate-scale slot values (rep 1 vs rep 2; left vs right; run 1 vs run 2) over players with both. D1 pairs left with right, O1 pairs rep 1 with rep 2 (which are mostly opposite drift sides).
- Player value = mean of the available slot values (>= 1 slot), so coverage counts players with a single usable rep; this inflates coverage slightly relative to a both-slots requirement (both-slots coverage is reported per trait).
- O3/D4 reversal: consecutive qualifying frames (|vy| >= 1.0 yd/s) of opposite sign; time = first new-direction frame minus last old-direction frame; vy from the 3-frame smoothed y, central difference. Odd/even = alternate reversals in chronological order. Within-rep gate applied to the uncorrected r (conservative).
- O4/D5 acceleration shape: frame-based crossing times (first frame with smoothed s >= 2.0; first frame >= 0.9 x own top speed), run must be seen below 2.0 first. Interpolated variant logged.
- Redundancy uses the gate-scale (year-/side-standardised) player value against raw official measures; the raw-scale max |r| is reported next to it (no verdict changes).
- Mosier component reliabilities are Spearman-Brown-corrected to the length of the player-level value; uncorrected value also reported.
- Coverage denominators are all combine_position OL (121) / DL (118) players, because the engaged-rep set is not built yet.
- D2 and D3 were selected in a prior search (C2): the pool records out-of-bag/earlier values (0.22, 0.37). The in-sample numbers here are shown, and the verdict is FAIL either way.

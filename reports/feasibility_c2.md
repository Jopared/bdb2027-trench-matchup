# Feasibility check C2 (edge bend): gates G1-G6

Script: `scripts/feasibility/c2_edge_bend.py` (run `.venv/Scripts/python.exe scripts/feasibility/c2_edge_bend.py`). Bootstrap CIs: 2,000 resamples of players, seed 2027. Every number below is computed by that script unless it is labelled as inference. No Combine drill metric is correlated with the NFL pressure outcome anywhere in this report (G5b uses in-game bend only; the drill metric appears only against in-game kinematics, G4, G6).

## 0. Headline

| gate | metric | value | 95% CI | n | verdict |
|---|---|---|---|---|---|
| G1 get_off | cross-side Pearson r, get_off (s 1.0 to 4.0 yd/s), year-standardised (raw 0.44 [0.24, 0.64]) | 0.37 | [0.13, 0.59] | 84 | **fail** (go needs 0.60) |
| G1 bend, pre-specified family | best of turn_accel / turn_min_speed / speed_carry / turn_time, 15-75 deg from initial run heading: turn_min_speed | 0.33 | [0.11, 0.54] | 83 | amber (go needs 0.40, no-go below 0.25) |
| G1 bend, primary by rule | `turn_min_speed\|run\|15-60` (year-standardised, raw 0.45) | 0.40 | [0.19, 0.57] | 92 | **amber** (selection-corrected r 0.22) |
| G2 | max abs r of primary two-side mean vs 10-yd, 40, weight, 3-cone | 0.41 (3-cone n=33) | see section 3 | 71 / 71 / 92 / 33 | **pass** |
| G3 get_off | split-half (odd/even), Spearman-Brown, >=30 rush snaps, PRE+REG+POST | 0.96 | [0.95, 0.97] | 109 | **pass** (go 0.70) |
| G3 in-game bend (bendB, EDGE-aligned) | same | 0.92 | [0.85, 0.95] | 57 | **pass** (go 0.60) |
| G4 get_off | drill get_off (two-side mean) vs in-game player_get_off, partial on EDGE/IDL | 0.04 | [-0.17, 0.24] | 75 | **fail** (go 0.25) |
| G4 bend, pooled | drill primary vs in-game bendB, partial on EDGE/IDL | 0.19 | [-0.09, 0.41] | 82 | amber |
| G4 bend, EDGE only | same, EDGE-aligned snaps | 0.29 | [-0.02, 0.53] | 46 | pass nominal, CI includes 0 |
| G5a | pressure split-half SB, >=100 REG rush snaps, residualised on EDGE/IDL (pooled unadjusted 0.83) | 0.74 | [0.60, 0.84] | 65 | **pass** (go 0.50) |
| G5b | partial r, in-game bendB vs beta-binomial-shrunk REG pressure rate, controlling in-game get_off and EDGE/IDL | 0.41 | [0.23, 0.56] | 85 | **pass** (go 0.25); EDGE-aligned only 0.22 [-0.01, 0.44] n=51 |
| G6 (exploratory) | drill (L - R) vs in-game (clockwise - counter-clockwise turn, bendA), >=8 EDGE snaps per sense | -0.21 | [-0.49, 0.07] | 35 | report only |

**Overall rule:** go if G1-bend, G2, G3 pass and (G4-bend or G5) passes. G1-bend = amber, G2 = pass, G3 = pass, G4-bend = amber, G5 = pass. **Decision: NO-GO as the rule is written (amber at best).** The only blocking item is G1-bend: the drill bend metrics are not consistent enough across the two reps (best defensible r about 0.33 to 0.40, and about 0.2 once the metric selection is corrected for). G2, G3 and G5 are comfortable; G4-bend is borderline; the get_off branch fails G1 and G4, so the fallback "get_off only" also does not rescue the idea.

Verdict thresholds that candidates.md leaves open are my operational choice: pass at the go threshold, amber within 0.10 below it (G1-bend: amber between 0.25 and 0.40, which is the file's no-go/go band), fail below that; G2 amber for max |r| in [0.60, 0.70). Where a year-drift flag fired, the year-standardised r is used for the verdict; G4/G5 take the lower of pooled and EDGE-only (G4) or pooled and unadjusted (G5a) where both are shown.

## 1. What the drill trajectories look like (verified by code)

- 225 reps from 118 players (`PASS_RUSH_DRILL`, entity PLAYER): 217 reps in SKILL_DRILLS_DL, 8 reps from 4 players in SKILL_DRILLS_LB. Side is assigned by the direction of travel in y (finish y > start y = "R", rep ending near y=39; otherwise "L", ending near y=15). Reps by year and side:

| draft year | L | R |
|---|---|---|
| 2023 | 37 | 32 |
| 2024 | 32 | 35 |
| 2025 | 45 | 44 |

- Players by sides recorded: {'LR': 105, 'L': 7, 'R': 5, 'LLR': 1}. So 106 players have both an L and an R rep (candidates.md says 102); one player has two L reps and one R (the first chronological rep per side is used everywhere).
- Start: median x = 44.47 (IQR 44.21 to 44.65); median y = 23.20 for R reps and 30.47 for L reps (documented 23.75 / 30.25). Matches the audit's x of about 44.5.
- Share reaching the finish line (R: y >= 39; L: y <= 15): 98.7% overall (L 99.1%, R 98.2%). The drill is essentially always tracked to the finish.
- Duration median 4.4 s (IQR 4.2 to 4.6; 10 Hz, median 45 frames); one rep is 10.2 s long (103 frames). Peak speed median 7.67 yd/s (IQR 7.31 to 7.92).
- Shape (heading `dir` is consistent with the heading from x/y differences: mean difference 0.01 deg, SD 0.8 deg at s > 3; speed from x/y matches `s` to 0.02 yd/s). Heading measured against the +x axis (dir = 90), with s >= 4 yd/s as the clock origin:

| quantity | count | 25% | 50% | 75% |
|---|---|---|---|---|
| dev_vs_x_at_s4 | 225.00 | 3.87 | 9.48 | 21.15 |
| t15_after_s4 | 225.00 | -0.27 | 0.13 | 0.27 |
| s_at_15deg | 225.00 | 3.94 | 4.09 | 4.31 |
| t45_after_s4 | 225.00 | 0.37 | 0.63 | 0.75 |
| s_at_45deg | 225.00 | 4.10 | 4.39 | 4.67 |
| t75_after_s4 | 224.00 | 0.93 | 1.16 | 1.28 |
| s_at_75deg | 224.00 | 5.15 | 5.49 | 5.83 |
| max_dev_vs_x_axis | 225.00 | 89.69 | 92.29 | 95.48 |

- Reading: players are already about 9 deg (median; IQR about 4 to 21 deg) off the +x axis toward the finish side when speed first reaches 4 yd/s, so the turn is an arc that starts while still accelerating, not a straight run followed by a corner. The heading deviation passes 15 deg at about 0.1 s after s = 4, 45 deg at +0.6 s and 75 deg at +1.2 s (speed 4.1, 4.4 and 5.5 yd/s). The final heading is about 90 to 92 deg off +x (it points at the finish line), reached in 99.6% of reps (>= 75 deg). The turn window 15 to 75 deg lasts about 1.0 s (median) and speed climbs only from about 4.0 to 5.4 yd/s within it; the 7.5 to 7.7 yd/s peak is reached after the heading has already settled, on the run to the line.
- Crop by year: median first-frame speed 2023: 0.52, 2024: 0.59, 2025: 0.17 yd/s; mean time (from first frame) at which s first reaches 1.0 yd/s 2023: 0.20 s, 2024: 0.25 s, 2025: 0.48 s; reaches 4.0 yd/s 2023: 1.03 s, 2024: 1.31 s, 2025: 1.69 s. The 2025 crop does start earlier (confirmed). In 2023 and 2024 the first smoothed frame is often already at or above 1.0 yd/s, so the threshold crossing is never observed: get_off is missing for 2023: 18, 2024: 8, 2025: 0 reps (these are the quickest starters, so the loss is not random).

## 2. Metric definitions used (all logged)

Common: `x, y, s, dir` at 10 Hz; `dis` and `a` not used. Smoothing = centred moving mean of `s` and of the unwrapped `dir`, 3 frames (primary) or 5 frames (sensitivity), edge frames dropped. dtheta/dt = centred difference of the smoothed unwrapped heading over 0.2 s, in rad/s; centripetal acceleration = s_smoothed x |dtheta/dt| (yd/s^2). Heading is unwrapped starting at the first frame with smoothed s >= 2 yd/s (earlier headings are noise at near-zero speed).

**Get-off (G1, G2, G4):** time from first smoothed s >= 1.0 to first s >= 4.0 yd/s, linear interpolation of the crossing; the specified definition is `get_off`. Sensitivity variants: `go_2_4` (2.0 to 4.0), `go_2_5` (2.0 to 5.0; this one runs into the turn), `go_1_4_rawS` (1.0 to 4.0 on unsmoothed s).

**Bend family (window of heading deviation 15 to 75 deg, as specified):** `turn_accel` = mean centripetal acceleration over frames in the window; `turn_min_speed` = min smoothed s in the window; `speed_carry` = s at the 75 deg crossing / s at the 15 deg crossing; `turn_time` = duration of the window. I added `peak_cent` = max centripetal acceleration in the window (the drill analogue of the in-game metric). Heading deviation is signed toward the finish side. The reference heading was tried two ways: `run` = mean heading between first s >= 1.0 and first s >= 3.0 (the early straight run) and `x` = fixed +x axis (dir = 90). Windows tried: 15-75 (specified), 15-60, 30-75. That is 5 metrics x 3 windows x 2 references = 30 bend candidates, each at 3 and 5 frames. The window search starts at the first frame with s >= 2 and takes the first frame at or above each threshold.

Exploratory definitions dropped before the final grid (interactive, not in the script): (a) initial run heading taken at s 3 to 4.5 yd/s: players are already 10 to 30 deg off line by then, the 15 deg crossing was found in only 59 of 225 reps and the 75 deg crossing in only 88; dropped.

Windows found per definition (reps with a valid window, of 225): `turn_accel|run|15-75`: 198, `turn_accel|run|15-60`: 211, `turn_accel|run|30-75`: 198, `turn_accel|x|15-75`: 224, `turn_accel|x|15-60`: 224, `turn_accel|x|30-75`: 224.

**Selection rule for the primary drill bend metric (applied to the 30 candidates at 3 frames with >= 75 L/R pairs):** (1) highest cross-side Pearson r (the year-standardised r when the year-drift flag fires for that metric, otherwise raw); (2) among candidates within 0.05 of that best, the one with the lowest max |r| against ten_yd_split, forty, combine_weight (and three_cone when n >= 15), computed on the two-side mean; (3) remaining ties go to the 15-75 window, then to the 15-60 window. Best r = 0.42; candidates within 0.05: `turn_min_speed|run|15-60`, `peak_cent|x|15-75`, `peak_cent|x|15-60`, `peak_cent|x|30-75`. **Primary = `turn_min_speed|run|15-60`** (turn_min_speed with the run-heading reference and the 15-60 window: the speed at which the player enters the turn).
Note on what this means: `turn_min_speed` is essentially the speed carried into the arc, a speed measure rather than a pure turning-sharpness measure; the centripetal-acceleration metrics were less consistent across sides (see table). The rule picks the best of 30 correlated metrics, which inflates r: re-running the whole selection inside bootstrap resamples and scoring the winner on the out-of-bag players gives a mean in-sample best r of 0.50 but an out-of-bag r of only 0.22 (1,000 resamples). Read the primary's r as an upper-ish estimate.

**In-game (G3-G6):** rush snap = `player_play` row with blitzing == True and pass_result != '' and lined_up_position != 'NA' (35,565 snaps, 115 of the 118 drill players). t = 0 at the ball_snap frame; window = snap + 0.3 s to the earlier of snap + 3.0 s and the first pass_forward / qb_sack / qb_strip_sack event. `bendA` = max over window frames with smoothed s >= 3.5 yd/s of s x |dtheta/dt| (needs >= 2 gated frames). `bendB` = mean smoothed s over window frames whose smoothed heading is 30 to 80 deg from the upfield direction (dir = 90 if play_direction is left, 270 if right; needs >= 2 frames). Both at 3 and 5 frames. Turn sense for G6 = sign of the net heading change across the gated frames (clockwise = dir increasing; needs >= 20 deg). bend metrics use EDGE-aligned snaps (G3, G4 EDGE-only, G6) or all alignments with an EDGE/IDL indicator (G4 pooled, G5b). Player alignment indicator = EDGE if >= 50% of his rush snaps are lined up at EDGE (56 of 115 players). Season types: PRE+REG+POST for kinematics, REG for pressure. Chronological order = season, season type, week, game_id, play_id. Pressure = time_to_pressure non-null; shrinkage = beta-binomial with a method-of-moments prior per alignment group.

Convention check (verified): in the 2024 tracking, the mean snap x of the offence minus the defence is +6.3 when play_direction == left and -6.0 when right, so the offence's end zone is at decreasing x when left and the rusher's upfield is +x when left, as candidates.md says. In-game bend availability: bendA exists on 79% of EDGE rush snaps but only 27% of IDL snaps (the 3.5 yd/s gate); bendB on 77% and 75%.

## 3. Gate results in detail

### G1 cross-side consistency (left rep vs right rep; the two reps differ in side and move, so this is a lower bound on reliability)

| metric | n (3f) | r raw 3f | CI raw | Spearman 3f | r year-z 3f | max year dev (SD) | drift flag | r used 3f | n (5f) | r raw 5f | r year-z 5f |
|---|---|---|---|---|---|---|---|---|---|---|---|
| get_off | 84 | 0.44 | [0.24, 0.64] | 0.49 | 0.37 | 0.87 | yes | 0.37 | 49 | 0.41 | 0.33 |
| go_2_4 | 106 | 0.45 | [0.28, 0.61] | 0.51 | 0.39 | 0.69 | yes | 0.39 | 105 | 0.47 | 0.42 |
| go_2_5 | 106 | -0.15 | [-0.48, 0.49] | 0.34 | -0.16 | 0.32 | no | -0.15 | 105 | -0.15 | -0.15 |
| go_1_4_rawS | 104 | 0.46 | [0.30, 0.61] | 0.51 | 0.38 | 0.95 | yes | 0.38 | 104 | 0.46 | 0.38 |
| turn_accel\|run\|15-75 | 83 | 0.37 | [0.18, 0.55] | 0.41 | 0.27 | 0.93 | yes | 0.27 | 81 | 0.36 | 0.26 |
| turn_min_speed\|run\|15-75 | 83 | 0.38 | [0.18, 0.56] | 0.42 | 0.33 | 0.91 | yes | 0.33 | 81 | 0.35 | 0.34 |
| speed_carry\|run\|15-75 | 83 | -0.07 | [-0.23, 0.12] | -0.01 | -0.11 | 0.45 | no | -0.07 | 81 | -0.03 | -0.04 |
| turn_time\|run\|15-75 | 83 | 0.15 | [-0.06, 0.47] | 0.22 | 0.17 | 0.26 | no | 0.15 | 81 | 0.15 | 0.20 |
| peak_cent\|run\|15-75 | 83 | 0.32 | [0.14, 0.50] | 0.37 | 0.29 | 0.56 | yes | 0.29 | 81 | 0.37 | 0.35 |
| turn_accel\|run\|15-60 | 92 | 0.39 | [0.20, 0.55] | 0.33 | 0.34 | 0.95 | yes | 0.34 | 90 | 0.39 | 0.34 |
| turn_min_speed\|run\|15-60 | 92 | 0.45 | [0.26, 0.62] | 0.46 | 0.40 | 0.98 | yes | 0.40 | 90 | 0.44 | 0.42 |
| speed_carry\|run\|15-60 | 92 | 0.16 | [0.02, 0.31] | 0.17 | 0.10 | 0.62 | yes | 0.10 | 90 | 0.22 | 0.17 |
| turn_time\|run\|15-60 | 92 | 0.19 | [-0.06, 0.44] | 0.14 | 0.18 | 0.26 | no | 0.19 | 90 | 0.25 | 0.26 |
| peak_cent\|run\|15-60 | 92 | 0.30 | [0.09, 0.52] | 0.37 | 0.28 | 0.70 | yes | 0.28 | 90 | 0.29 | 0.26 |
| turn_accel\|run\|30-75 | 83 | 0.21 | [-0.03, 0.46] | 0.27 | 0.13 | 0.72 | yes | 0.13 | 81 | 0.25 | 0.17 |
| turn_min_speed\|run\|30-75 | 83 | 0.28 | [0.05, 0.53] | 0.42 | 0.25 | 0.94 | yes | 0.25 | 81 | 0.32 | 0.33 |
| speed_carry\|run\|30-75 | 83 | -0.18 | [-0.37, 0.04] | -0.08 | -0.20 | 0.34 | no | -0.18 | 81 | -0.15 | -0.16 |
| turn_time\|run\|30-75 | 83 | 0.05 | [-0.18, 0.49] | 0.15 | 0.07 | 0.19 | no | 0.05 | 81 | 0.08 | 0.09 |
| peak_cent\|run\|30-75 | 83 | 0.31 | [0.13, 0.49] | 0.36 | 0.29 | 0.57 | yes | 0.29 | 81 | 0.37 | 0.34 |
| turn_accel\|x\|15-75 | 105 | 0.33 | [0.08, 0.57] | 0.46 | 0.36 | 0.37 | no | 0.33 | 105 | 0.24 | 0.27 |
| turn_min_speed\|x\|15-75 | 105 | 0.19 | [-0.03, 0.54] | 0.41 | 0.24 | 0.66 | yes | 0.24 | 105 | 0.05 | 0.09 |
| speed_carry\|x\|15-75 | 105 | 0.17 | [-0.02, 0.38] | 0.21 | 0.21 | 0.69 | yes | 0.21 | 105 | -0.05 | -0.05 |
| turn_time\|x\|15-75 | 105 | 0.07 | [-0.08, 0.61] | 0.29 | 0.08 | 0.44 | no | 0.07 | 105 | -0.00 | 0.01 |
| peak_cent\|x\|15-75 | 105 | 0.42 | [0.28, 0.55] | 0.43 | 0.39 | 0.47 | no | 0.42 | 105 | 0.44 | 0.41 |
| turn_accel\|x\|15-60 | 105 | 0.35 | [0.11, 0.60] | 0.45 | 0.38 | 0.40 | no | 0.35 | 105 | 0.25 | 0.30 |
| turn_min_speed\|x\|15-60 | 105 | 0.20 | [-0.03, 0.54] | 0.42 | 0.24 | 0.66 | yes | 0.24 | 105 | 0.06 | 0.09 |
| speed_carry\|x\|15-60 | 105 | 0.19 | [-0.05, 0.44] | 0.15 | 0.24 | 0.74 | yes | 0.24 | 105 | -0.05 | -0.01 |
| turn_time\|x\|15-60 | 105 | 0.09 | [-0.05, 0.64] | 0.29 | 0.10 | 0.41 | no | 0.09 | 105 | 0.01 | 0.03 |
| peak_cent\|x\|15-60 | 105 | 0.42 | [0.28, 0.55] | 0.43 | 0.39 | 0.47 | no | 0.42 | 105 | 0.44 | 0.41 |
| turn_accel\|x\|30-75 | 105 | 0.24 | [0.02, 0.49] | 0.42 | 0.23 | 0.40 | no | 0.24 | 105 | 0.24 | 0.24 |
| turn_min_speed\|x\|30-75 | 105 | 0.31 | [0.13, 0.62] | 0.53 | 0.29 | 0.75 | yes | 0.29 | 105 | 0.30 | 0.29 |
| speed_carry\|x\|30-75 | 105 | 0.07 | [-0.02, 0.28] | 0.27 | -0.01 | 0.73 | yes | -0.01 | 105 | 0.12 | 0.03 |
| turn_time\|x\|30-75 | 105 | -0.04 | [-0.12, 0.39] | 0.24 | -0.05 | 0.31 | no | -0.04 | 105 | -0.04 | -0.05 |
| peak_cent\|x\|30-75 | 105 | 0.42 | [0.28, 0.55] | 0.43 | 0.38 | 0.47 | no | 0.42 | 105 | 0.44 | 0.41 |

`r used` = year-standardised r where the drift flag fires (a year mean differing from the mean of the other years by more than 0.5 pooled within-year SD, checked per side), raw otherwise. The first four rows are get-off variants; the next four are the pre-specified family (run heading, 15-75); the rest are the other candidates. The 5-frame sensitivity gives the same picture (best run-reference bend r about 0.44 raw for turn_min_speed 15-60, peak_cent|x 0.44; get_off 0.41 with n = 49 because the 5-frame smoothing loses more starts). The x-reference turn_min_speed and speed_carry collapse at 5 frames (0.19 to 0.05 and 0.17 to -0.05), i.e. several candidates are not stable to the smoothing choice.

**G1 by draft year** (cross-side r within each class; n small, CIs wide; values are on year-standardised metrics so the within-year r is not affected by year offsets):

| metric | year | n | r | CI |
|---|---|---|---|---|
| get_off | 2023 | 17 | 0.32 | [0.02, 0.79] |
| get_off | 2024 | 23 | 0.63 | [0.07, 0.87] |
| get_off | 2025 | 44 | 0.28 | [-0.05, 0.58] |
| turn_min_speed\|run\|15-60 | 2023 | 29 | 0.59 | [0.02, 0.84] |
| turn_min_speed\|run\|15-60 | 2024 | 27 | 0.45 | [0.18, 0.68] |
| turn_min_speed\|run\|15-60 | 2025 | 36 | 0.28 | [-0.08, 0.59] |
| turn_accel\|run\|15-75 | 2023 | 27 | 0.53 | [0.15, 0.82] |
| turn_accel\|run\|15-75 | 2024 | 24 | 0.44 | [0.04, 0.75] |
| turn_accel\|run\|15-75 | 2025 | 32 | 0.00 | [-0.22, 0.28] |

Pooled and by year agree that get_off is about 0.3 to 0.6 and the bend metrics about 0 to 0.6 with no stable year ordering; 2025 is the weakest year for both bend metrics (r = 0.28 and 0.00), the year with the earliest crop and the most reps.

**Year-mean drift (threshold-crossing metrics, mean and SD by year and side):**

| metric | side | year | n | mean | sd |
|---|---|---|---|---|---|
| get_off | L | 2023 | 25 | 0.91 | 0.27 |
| get_off | L | 2024 | 28 | 1.11 | 0.41 |
| get_off | L | 2025 | 45 | 1.31 | 0.40 |
| get_off | R | 2023 | 26 | 0.86 | 0.27 |
| get_off | R | 2024 | 31 | 1.03 | 0.28 |
| get_off | R | 2025 | 44 | 1.10 | 0.33 |
| go_2_4 | L | 2023 | 37 | 0.65 | 0.26 |
| go_2_4 | L | 2024 | 32 | 0.81 | 0.39 |
| go_2_4 | L | 2025 | 45 | 0.95 | 0.37 |
| go_2_4 | R | 2023 | 32 | 0.60 | 0.23 |
| go_2_4 | R | 2024 | 35 | 0.75 | 0.29 |
| go_2_4 | R | 2025 | 44 | 0.81 | 0.31 |
| turn_min_speed\|run\|15-60 | L | 2023 | 37 | 4.22 | 0.47 |
| turn_min_speed\|run\|15-60 | L | 2024 | 29 | 3.93 | 0.52 |
| turn_min_speed\|run\|15-60 | L | 2025 | 37 | 3.75 | 0.50 |
| turn_min_speed\|run\|15-60 | R | 2023 | 29 | 4.32 | 0.35 |
| turn_min_speed\|run\|15-60 | R | 2024 | 35 | 3.53 | 0.89 |
| turn_min_speed\|run\|15-60 | R | 2025 | 44 | 3.80 | 0.58 |
| turn_accel\|run\|15-75 | L | 2023 | 36 | 4.68 | 0.66 |
| turn_accel\|run\|15-75 | L | 2024 | 24 | 4.33 | 0.64 |
| turn_accel\|run\|15-75 | L | 2025 | 33 | 4.20 | 0.67 |
| turn_accel\|run\|15-75 | R | 2023 | 27 | 4.79 | 0.40 |
| turn_accel\|run\|15-75 | R | 2024 | 34 | 4.23 | 0.61 |
| turn_accel\|run\|15-75 | R | 2025 | 44 | 4.38 | 0.50 |
| turn_min_speed\|run\|15-75 | L | 2023 | 36 | 4.22 | 0.47 |
| turn_min_speed\|run\|15-75 | L | 2024 | 24 | 3.91 | 0.56 |
| turn_min_speed\|run\|15-75 | L | 2025 | 33 | 3.70 | 0.50 |
| turn_min_speed\|run\|15-75 | R | 2023 | 27 | 4.27 | 0.28 |
| turn_min_speed\|run\|15-75 | R | 2024 | 34 | 3.51 | 0.90 |
| turn_min_speed\|run\|15-75 | R | 2025 | 44 | 3.80 | 0.58 |

Flag statistic = (year mean - mean of the other years) / pooled SD, per side. get_off: L-2023: -0.87; L-2024: -0.16; L-2025: 0.80; R-2023: -0.72; R-2024: 0.05; R-2025: 0.52. So `get_off` does drift by more than 0.5 SD in 2023 and 2025 on both sides (2025 is slower by about 0.2 to 0.4 s) even though it uses threshold crossings (inference on cause: the crossing times fix the start of the clock but not a systematic change in how the rep begins; the 2023/24 reps lost to censoring are the ones already moving at the first frame, which is verified for the count, and "fastest starters" is inferred from that). The bend metrics tied to the early part of the rep (turn_min_speed, turn_accel with the run reference) also drift by 0.5 to 1.0 SD with 2023 higher. Year standardisation was applied wherever the flag fired.

### G2 non-redundancy (two-side mean, players with both sides; Pearson, bootstrap CI)

| which | baseline | n | r | CI |
|---|---|---|---|---|
| primary | ten_yd_split | 71 | -0.20 | [-0.45, 0.10] |
| primary | forty | 71 | -0.19 | [-0.42, 0.07] |
| primary | combine_weight | 92 | -0.05 | [-0.25, 0.17] |
| primary | three_cone | 33 | -0.41 | [-0.64, -0.15] |
| get_off | ten_yd_split | 62 | 0.47 | [0.25, 0.64] |
| get_off | forty | 62 | 0.48 | [0.24, 0.66] |
| get_off | combine_weight | 84 | 0.47 | [0.27, 0.63] |
| get_off | three_cone | 29 | 0.30 | [-0.10, 0.68] |

Available baselines: ten_yd_split 425, forty 424, weight 510, three_cone 180 of 510 players. All |r| of the primary are below 0.60 (largest: 3-cone, n = 33, upper CI bound reaches |r| = 0.64) -> pass. `get_off` against the 10-yd split is only 0.47 (expected higher): get_off is not the stopwatch burst measure, which also fits its low cross-side consistency. Non-redundancy for the other near-top candidates (max |r| over 10-yd/40/weight/3-cone, two-side mean). Note that the highest-r candidate, `peak_cent|x` (centripetal acceleration against the fixed +x axis, r = 0.42), would have been amber on G2 (|r| = 0.62 with the 3-cone, n = 37, and about 0.50 with the 40 and with weight); the non-redundancy tie-break is what moved the primary to turn_min_speed:

| metric | ten_yd_split | forty | combine_weight | three_cone | n_three_cone | max_abs |
|---|---|---|---|---|---|---|
| turn_min_speed\|run\|15-60 | -0.20 | -0.19 | -0.05 | -0.41 | 33 | 0.41 |
| peak_cent\|x\|15-75 | -0.42 | -0.50 | -0.50 | -0.62 | 37 | 0.62 |
| peak_cent\|x\|15-60 | -0.42 | -0.50 | -0.50 | -0.62 | 37 | 0.62 |
| peak_cent\|x\|30-75 | -0.42 | -0.49 | -0.49 | -0.62 | 37 | 0.62 |
| get_off | 0.47 | 0.48 | 0.47 | 0.30 | 29 | 0.48 |

### G3 in-game reliability (odd/even chronological snaps, Spearman-Brown)

| metric | frames | min snaps | n | half-half r | SB | CI (SB) |
|---|---|---|---|---|---|---|
| player_get_off (all rush snaps) | - | 30 | 109 | 0.93 | 0.96 | [0.95, 0.97] |
| bendA: max s*\|dtheta/dt\|, s>=3.5 (EDGE-aligned) | 3 | 30 | 54 | 0.69 | 0.82 | [0.70, 0.90] |
| bendB: mean s at 30-80 deg off upfield (EDGE-aligned) | 3 | 30 | 57 | 0.85 | 0.92 | [0.85, 0.95] |
| bendA: max s*\|dtheta/dt\|, s>=3.5 (EDGE-aligned) | 5 | 30 | 54 | 0.71 | 0.83 | [0.72, 0.91] |
| bendB: mean s at 30-80 deg off upfield (EDGE-aligned) | 5 | 30 | 57 | 0.87 | 0.93 | [0.88, 0.96] |
| player_get_off (all rush snaps) | - | 20 | 113 | 0.91 | 0.95 | [0.93, 0.97] |
| bendA: max s*\|dtheta/dt\|, s>=3.5 (EDGE-aligned) | 3 | 20 | 62 | 0.65 | 0.79 | [0.65, 0.88] |
| bendB: mean s at 30-80 deg off upfield (EDGE-aligned) | 3 | 20 | 65 | 0.84 | 0.91 | [0.86, 0.95] |
| bendA: max s*\|dtheta/dt\|, s>=3.5 (EDGE-aligned) | 5 | 20 | 60 | 0.70 | 0.83 | [0.74, 0.90] |
| bendB: mean s at 30-80 deg off upfield (EDGE-aligned) | 5 | 20 | 65 | 0.87 | 0.93 | [0.89, 0.96] |

Min snaps = valid values of the metric per player. The primary in-game bend is chosen by reliability at 3 frames and >= 30 snaps: **bendB** (SB 0.92 vs 0.82). Caution (inference): these are high because a rusher's alignment, team scheme and typical drop depths are stable across his snaps, so split-half reliability measures the persistence of role plus skill, not skill alone; also the odd/even halves interleave snaps from the same games.

### G4 transfer (drill to game kinematics; the pressure outcome is not used)

| test | n | r | CI |
|---|---|---|---|
| G4 get_off: drill (both sides) vs in-game player_get_off, pooled, raw r | 75 | 0.31 | [0.12, 0.48] |
| G4 get_off: drill (both sides) vs in-game player_get_off, pooled, partial\|EDGE/IDL | 75 | 0.04 | [-0.17, 0.24] |
| G4 get_off: drill (both sides) vs in-game player_get_off, EDGE-primary only | 36 | -0.00 | [-0.30, 0.29] |
| G4 get_off: drill (any side) vs in-game player_get_off, pooled, raw r | 105 | 0.19 | [0.02, 0.37] |
| G4 get_off: drill (any side) vs in-game player_get_off, pooled, partial\|EDGE/IDL | 105 | -0.04 | [-0.21, 0.15] |
| G4 get_off: drill (any side) vs in-game player_get_off, EDGE-primary only | 51 | 0.01 | [-0.21, 0.26] |
| G4 bend [bendA]: drill primary (both sides) vs in-game, pooled all alignments, raw r | 71 | 0.09 | [-0.15, 0.30] |
| G4 bend [bendA]: drill primary (both sides) vs in-game, pooled all alignments, partial\|EDGE/IDL | 71 | 0.04 | [-0.19, 0.26] |
| G4 bend [bendA]: drill primary (both sides) vs in-game, EDGE-aligned snaps only | 44 | 0.12 | [-0.22, 0.39] |
| G4 bend [bendA]: drill primary (any side) vs in-game, pooled all alignments, raw r | 88 | 0.11 | [-0.06, 0.26] |
| G4 bend [bendA]: drill primary (any side) vs in-game, pooled all alignments, partial\|EDGE/IDL | 88 | 0.04 | [-0.12, 0.23] |
| G4 bend [bendA]: drill primary (any side) vs in-game, EDGE-aligned snaps only | 54 | 0.12 | [-0.14, 0.35] |
| G4 bend [bendB]: drill primary (both sides) vs in-game, pooled all alignments, raw r | 82 | 0.15 | [-0.09, 0.36] |
| G4 bend [bendB]: drill primary (both sides) vs in-game, pooled all alignments, partial\|EDGE/IDL | 82 | 0.19 | [-0.09, 0.41] |
| G4 bend [bendB]: drill primary (both sides) vs in-game, EDGE-aligned snaps only | 46 | 0.29 | [-0.02, 0.53] |
| G4 bend [bendB]: drill primary (any side) vs in-game, pooled all alignments, raw r | 104 | 0.14 | [-0.03, 0.31] |
| G4 bend [bendB]: drill primary (any side) vs in-game, pooled all alignments, partial\|EDGE/IDL | 104 | 0.10 | [-0.13, 0.35] |
| G4 bend [bendB]: drill primary (any side) vs in-game, EDGE-aligned snaps only | 57 | 0.35 | [0.07, 0.57] |
| G4 bend [bendB] EDGE-aligned, drill primary (both sides) \| combine_weight (robustness) | 46 | 0.22 | [-0.09, 0.46] |
| G4 bend [bendB] EDGE-aligned, drill primary (both sides) \| combine_weight, ten_yd_split (robustness) | 34 | 0.23 | [-0.13, 0.50] |
| G4 bend [bendB] EDGE-aligned, drill primary (any side) \| combine_weight (robustness) | 57 | 0.22 | [-0.01, 0.41] |
| G4 bend [bendB] EDGE-aligned, drill primary (any side) \| combine_weight, ten_yd_split (robustness) | 44 | 0.11 | [-0.17, 0.38] |

get_off: the raw pooled association (0.31) is entirely the EDGE/IDL difference (both drill and NGS get-off are slower for interior linemen); with the indicator it is 0.04 and within EDGE players it is 0.00 -> fail. Bend: the in-game metric that is the more reliable (bendB) is a speed measure; with the drill primary (also a speed-at-turn measure) it gives pooled partial 0.19 and EDGE-only 0.29, both with CIs that include zero; bendA (centripetal) gives 0.04 to 0.12. Verdict amber.

### G5 outcome usable and mechanism plausible

| test | n | half-half r | SB | CI (SB) |
|---|---|---|---|---|
| pressure split-half, >=100 REG rush snaps, pooled (no alignment control) | 65 | 0.71 | 0.83 | [0.73, 0.90] |
| pressure split-half, >=100 REG rush snaps, residualised on EDGE/IDL | 65 | 0.59 | 0.74 | [0.60, 0.84] |
| pressure split-half, >=100 REG rush snaps, EDGE-primary only | 33 | 0.67 | 0.80 | [0.65, 0.89] |
| pressure split-half, >=100 REG rush snaps, non-EDGE-primary only | 32 | 0.49 | 0.66 | [0.29, 0.85] |
| pressure split-half, >=30 REG rush snaps, pooled (no alignment control) | 85 | 0.66 | 0.79 | [0.65, 0.88] |
| pressure split-half, >=30 REG rush snaps, residualised on EDGE/IDL | 85 | 0.55 | 0.71 | [0.51, 0.83] |
| pressure split-half, >=30 REG rush snaps, EDGE-primary only | 41 | 0.54 | 0.70 | [0.31, 0.88] |
| pressure split-half, >=30 REG rush snaps, non-EDGE-primary only | 44 | 0.62 | 0.77 | [0.58, 0.87] |

REG rush snaps for drill players: 27360 (98 players; 85 with >= 30 and 65 with >= 100); pressure rate 9.9%. Pooled reliability includes the EDGE-vs-IDL level difference, so the residualised value is the one used for the verdict (pass either way).

| test | n | r | CI |
|---|---|---|---|
| G5b [bendA] in-game bend vs shrunk pressure rate \| get_off, EDGE/IDL; pooled all alignments, REG>=30 | 84 | 0.30 | [0.14, 0.45] |
| G5b [bendA] ... \| EDGE/IDL only (no get_off control) | 84 | 0.33 | [0.16, 0.49] |
| G5b [bendA] ... raw r | 84 | 0.67 | [0.56, 0.76] |
| G5b [bendA] EDGE-aligned snaps only, REG EDGE>=30 \| get_off | 51 | 0.18 | [-0.06, 0.40] |
| G5b [bendB] in-game bend vs shrunk pressure rate \| get_off, EDGE/IDL; pooled all alignments, REG>=30 | 85 | 0.41 | [0.23, 0.56] |
| G5b [bendB] ... \| EDGE/IDL only (no get_off control) | 85 | 0.53 | [0.32, 0.68] |
| G5b [bendB] ... raw r | 85 | 0.85 | [0.80, 0.89] |
| G5b [bendB] EDGE-aligned snaps only, REG EDGE>=30 \| get_off | 51 | 0.22 | [-0.01, 0.44] |

Caveats (inference): the raw r (0.67 and 0.85) is mostly the EDGE-vs-IDL level difference; the partial values remove that but the in-game bend metrics are computed over the same snaps whose pressure outcome is being predicted, and bendB is mean speed during the turn, so the association partly reflects that a rusher who is moving fast near the quarterback is by construction more likely to pressure. Within EDGE-aligned snaps only, the partial r is 0.22 (bendB) and 0.18 (bendA), below 0.25. Team, scheme, down and distance and dropback length are not controlled.

### G6 within-player side asymmetry (exploratory, report only)

| test | n | n_ingame_players | r | CI |
|---|---|---|---|---|
| drill (L - R) vs in-game (clockwise - counter-clockwise bendA), >=5 EDGE snaps per sense | 40 | 50 | -0.19 | [-0.42, 0.04] |
| drill (L - R) vs in-game (clockwise - counter-clockwise bendA), >=8 EDGE snaps per sense | 35 | 43 | -0.21 | [-0.49, 0.07] |

Drill L rep (finishes through y = 15) turns clockwise (heading dir increases); R rep turns counter-clockwise. Asymmetry = L minus R in the drill (on the primary metric, year-standardised) and clockwise minus counter-clockwise bendA in games (EDGE-aligned). The point estimate is negative (opposite to the hypothesis) with a CI that includes zero; no support, and no evidence against.

## 4. What candidates.md got wrong or left unclear about the data

1. Players with both a left and a right rep: 106 by direction of travel, not 102 (one player has two left reps). 12 players have a single rep.
2. The 15-to-75 deg window "from the initial run heading" is not well defined: by the time speed reaches 4 yd/s players are already about 10 to 30 deg off the +x axis, so against a heading taken at s 3 to 4.5 yd/s the 75 deg point is reached in only 88 of 225 reps. Against a heading taken from s 1 to 3 yd/s it is reached in 198, against the fixed +x axis in 224.
3. "A turn of about 90 deg between 1.5 and 3.0 s during which speed rises to about 7.5 yd/s": the 90 deg is right (final heading about 91 deg off +x) but speed inside the 15-75 deg window is only about 4.0 to 5.4 yd/s; 7.5 to 7.7 yd/s is the peak on the finish run after the turn. Centripetal acceleration in the window is about 4.4 to 4.6 yd/s^2 (mean; peak about 5.5).
4. Threshold-crossing times do not remove the crop problem. get_off needs s to be seen crossing 1.0 yd/s; in 26 reps (2023: 18 of 69, 2024: 8 of 67) the recording starts above that, so those reps (the fastest starters) have no get_off, and the surviving get_off means still drift by about 1 SD between 2023 and 2025. The drill-start sample for get_off is 84 pairs, not 102 to 106.
5. Cross-side get_off consistency is far below the 0.60 go line (0.45 raw, 0.37 year-standardised), and get_off is only moderately tied to the 10-yd split (r about 0.47), so it is neither very reliable nor a stopwatch duplicate.
6. The in-game and outcome side behaves as the file assumed: EDGE get_off coverage 95% (doc 94%), IDL 89%; pressure rate 12.0% EDGE, 7.2% IDL; 85 players with >= 30 and 65 with >= 100 REG rush snaps (matches); the play_direction convention is confirmed.
7. Not in the file: the in-game bend gate s >= 3.5 yd/s excludes 73% of interior-line snaps, so bendA is essentially an EDGE-only measure; bendB (30-80 deg mean speed) has better coverage and far better reliability, but it is a speed measure.

## 5. Verified versus inferred

Verified by code (all numbers in sections 0-4 except those labelled otherwise): rep counts and geometry, trajectory timing, definitions, all correlations, CIs, split-half values, shrinkage, direction convention, dir-versus-position consistency.

Inference or judgement, not checked by code: the explanations for why get_off drifts and why in-game reliabilities are high; that turn_min_speed is mainly a speed measure; the amber/fail margins that candidates.md does not specify (my operational choice, stated above); the dropped exploratory definition (a) was run interactively and is not in the script; the selection-optimism estimate is itself noisy (out-of-bag sets of about 35 players).

Data-quality notes: one 10.2 s rep (103 frames) is included without trimming; heading unwrapping gives implausible total deviations (> 180 deg) in a handful of reps, which only matter for the `max_dev` descriptive (the median is unaffected). Players in the drill set with no qualifying rush snaps in games (3 of 118) drop out of G3 to G6.

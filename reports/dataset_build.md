# Engaged-rep dataset build (step 2 of the pre-registered design)

Code: `src/bdb2027/engaged_reps.py`, `scripts/build_engaged_reps.py` (rebuilds from the Parquet files; frame cache used: no, rebuilt from game_tracking_*.parquet). No model was fitted. Outcomes are in `data/processed/engaged_outcomes_SEALED.parquet` and were not opened (only its key columns were read for the row/uniqueness check).

## 1. Definitions and filters

- **Plays**: `player_play` rows with `pass_result != ''` (dropbacks; the empty string is the non-dropback marker) and `lined_up_position != 'NA'` (pre-snap-penalty rows), joined to `games` for `season`, `season_type`, `week`. Kept `season_type` in REG, POST (PRE dropped).
- **Blocker**: row with `pressure_allowed` non-null (a pass-block snap), any lined-up position (so TE/RB/FB blockers are in the pairs table; the T/G/C restriction is a column filter). **Rusher**: row with `blitzing == True` on the opposing team (`team_abbr` differs), any alignment. Both are cohort players (all `player_play` rows are cohort players with Combine data).
- **Pair** = every (game, play, blocker, rusher) co-occurrence. The table has one row per pair, engaged or not, so the selection checks and the non-engaged placebo are possible.
- **Window**: `ball_snap` + 0.2 s to the earliest of `ball_snap` + 3.0 s, first `pass_forward`, first `qb_sack` (event tags read from the tracking frames of the pair players; they are play-level). Missing tags are ignored by the minimum: a play with no `pass_forward` and no sack is cut at snap + 3.0 s (decision, identical to the feasibility script). `qb_strip_sack` is not used. Pairs on plays with no `ball_snap` tag are dropped.
- **Distance**: Euclidean x/y between the two players at identical timestamps (10 Hz; frame spacing verified in the audit). **Engaged(thr, k)** = at least k such frames with d <= thr. Primary 1.5 yd / 4 frames; sensitivity 1.25 yd, 2.0 yd (k = 4), and k = 3, k = 6 (1.5 yd). Pairs with no overlapping frame in the window are non-engaged (`n_common_frames` = 0, `min_dist` null).
- **Double team**: `n_other_engaged_blockers` = number of OTHER pairs on the same play and rusher that are engaged under the PRIMARY definition (self excluded); `double_team` = that count >= 1. It is defined for non-engaged pairs too (count of primary-engaged cohort blockers with that rusher). Only cohort blockers are visible, so true double teams are understated.
- **Play action**: any `play_action` or `autoevent_playaction` event tag among the loaded frames of the play.
- **Shotgun**: `offense_formation` in SHOTGUN or EMPTY (decision); `pistol` is a separate flag; both null when formation is null.
- **Score differential / win probability**: offence minus defence pre-snap score, and offence pre-snap win probability, with the offence = the blocker's team (home/visitor decided from `games`).
- **Backward displacement**: blocker x at snap + 0.5 s / + 1.0 s minus x at the snap frame, signed so that backward is +x when `play_direction == 'left'` and -x when 'right' (`blocker_back_disp_05s`, `blocker_back_disp_10s`, yards). Null if `play_direction` is null or no frame exists at exactly that timestamp. Frames after the window end (pass thrown, sack) are used if they exist.
- **Player baselines**: one row per cohort player (510). `draft_overall_pick` null -> 262 with `undrafted` flag, `log_pick` = ln(pick), `draft_year` from combine_results (players as fallback), a `<measure>_missing` flag for each of combine_weight, arm_length, forty, ten_yd_split, short_shuttle, three_cone and for ngs_athleticism_score. Tracking-derived composites are NOT in this file (traits.py owns them).
- **Not included on purpose** (they would leak the outcome into the open file): sack tag, window end source, window length. `dropback_duration`, `play_nullified_by_penalty` are included as pre-specified/rep-context columns; both are set by what happens on the play and so are related to the outcome, as in the pre-registered covariate list.

## 2. Reproduction of the feasibility counts

| quantity | this build | feasibility_c3.md |
|---|---|---|
| co-occurring pairs (REG+POST) | 29,269 | 29,269 |
| pairs before dropping no-snap plays | 29,271 | 29,271 |
| engaged reps, primary | 8,271 | 8,271 |
| distinct engaged blockers, primary | 107 | 107 |
| distinct engaged rushers, primary | 129 | 129 |

Match: **YES**. Dropped for missing `ball_snap`: 2 pair(s). Plays in the table: 16,335; plays without a `pass_forward` tag: 1,894 of 16,335 (11.6%).

## 3. Engaged reps, blockers, rushers by definition (REG+POST)

| definition | engaged_reps | of_which_REG | distinct_blockers | distinct_rushers | blockers_ge10 | rushers_ge10 | engagement_rate_of_pairs |
|---|---|---|---|---|---|---|---|
| primary (1.5 yd / 4 fr) | 8,271 | 7,840 | 107 | 129 | 70 | 82 | 0.283 |
| d125 (1.25 yd / 4 fr) | 7,290 | 6,926 | 105 | 122 | 70 | 79 | 0.249 |
| d200 (2.0 yd / 4 fr) | 10,246 | 9,709 | 109 | 134 | 73 | 89 | 0.350 |
| k3 (1.5 yd / 3 fr) | 8,539 | 8,088 | 108 | 130 | 71 | 83 | 0.292 |
| k6 (1.5 yd / 6 fr) | 7,599 | 7,209 | 106 | 122 | 70 | 79 | 0.260 |

## 4. Primary engaged reps by season and by position

| season | engaged_reps | blockers | rushers |
|---|---|---|---|
| 2023 | 440 | 22 | 27 |
| 2024 | 2,093 | 57 | 70 |
| 2025 | 5,738 | 91 | 111 |

All pairs by season (engagement rate):

| season | pairs | engaged_share |
|---|---|---|
| 2023 | 1,518 | 0.290 |
| 2024 | 7,601 | 0.275 |
| 2025 | 20,150 | 0.285 |

Blocker `lined_up_position` x rusher `lined_up_position` (primary engaged reps):

| blocker_lined_up_position | EDGE | INTERIOR_LINE | CB | OLB | SLOT_CB | MLB | HIGH_SAFETY | total |
|---|---|---|---|---|---|---|---|---|
| G | 861 | 3,011 | 1 | 14 | 9 | 13 | 1 | 3,910 |
| T | 2,527 | 886 | 1 | 15 | 26 | 5 | 0 | 3,460 |
| C | 112 | 712 | 0 | 3 | 2 | 3 | 0 | 832 |
| TE | 53 | 5 | 0 | 1 | 0 | 0 | 0 | 59 |
| SLOT_WR | 5 | 0 | 0 | 0 | 2 | 0 | 0 | 7 |
| WR | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| FB | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

Share of primary engaged reps in the section 3.3 sub-sets (composites not applied; they come from traits.py):

| subset | reps | share_of_engaged | blockers | rushers |
|---|---|---|---|---|
| T/G/C blocker | 8,202 | 0.992 | 79 | 128 |
| T/G/C blocker, rusher combine_position DL | 8,109 | 0.980 | 79 | 97 |
| T/G/C blocker, rusher aligned EDGE/INTERIOR_LINE | 8,109 | 0.980 | 79 | 111 |
| T/G/C blocker, DL rusher aligned EDGE/INTERIOR_LINE (section 3.3 analysis set before composites) | 8,087 | 0.978 | 79 | 97 |

Blocker `combine_position` x rusher `combine_position` (primary engaged):

| blocker_combine_position | rusher_combine_position | len |
|---|---|---|
| OL | DL | 8,134 |
| OL | DB | 93 |
| TE | DL | 33 |
| WR | DL | 7 |
| WR | DB | 2 |
| TE | DB | 2 |

Rusher `nfl_position` (primary engaged):

| rusher_nfl_position | len |
|---|---|
| DT | 2,933 |
| DE | 2,861 |
| OLB | 2,103 |
| NT | 277 |
| SS | 60 |
| CB | 25 |
| FS | 10 |
| MLB | 2 |

## 5. Reps per blocker, rusher and dyad (primary engaged reps)

- per blocker (107 blockers): min 1 / p25 3 / median 57 / p75 123 / p90 194 / max 317; mean 77.30; top-10 blockers hold 31.0% of reps
- per rusher (129 rushers): min 1 / p25 5 / median 29 / p75 84 / p90 210 / max 344; mean 64.12; top-10 rushers hold 33.8% of reps
- per dyad (1491 dyads): min 1 / p25 1 / median 3 / p75 7 / p90 12 / max 86; mean 5.55; dyads with >= 2 reps: 1089
- section 3.3 sub-set (T/G/C vs DL EDGE/INTERIOR_LINE): per blocker min 1 / p25 32 / median 90 / p75 161 / p90 210 / max 315; mean 102.37; per rusher min 1 / p25 15 / median 50 / p75 116 / p90 220 / max 344; mean 83.37; dyads 1342

Double teams (primary definition): 
1,108 of 8,271 engaged reps (13.4%) are flagged; 547 of 7,710 engaged (play, rusher) units (7.1%).

## 6. Covariate missingness

| column | null_all_pairs | null_primary_engaged | pct_null_engaged |
|---|---|---|---|
| dropback_duration | 0 | 0 | 0.000 |
| down | 0 | 0 | 0.000 |
| yards_to_go | 0 | 0 | 0.000 |
| quarter | 0 | 0 | 0.000 |
| offense_formation | 4 | 0 | 0.000 |
| shotgun | 4 | 0 | 0.000 |
| pistol | 4 | 0 | 0.000 |
| play_action | 0 | 0 | 0.000 |
| pass_rushers_encountered | 0 | 0 | 0.000 |
| score_diff_offense | 0 | 0 | 0.000 |
| offense_win_prob | 0 | 0 | 0.000 |
| play_nullified_by_penalty | 0 | 0 | 0.000 |
| blocker_back_disp_05s | 73 | 0 | 0.000 |
| blocker_back_disp_10s | 73 | 0 | 0.000 |
| blocker_combine_position | 0 | 0 | 0.000 |
| rusher_combine_position | 0 | 0 | 0.000 |
| blocker_nfl_position | 0 | 0 | 0.000 |
| rusher_nfl_position | 0 | 0 | 0.000 |
| min_dist | 73 | 0 | 0.000 |
| week | 0 | 0 | 0.000 |

`play_direction` null count is visible through the two displacement columns. Decision for rows with missing `dropback_duration` or other covariates: **none dropped here**; every row is kept and the analyst decides (the pre-registration must state the rule). Rows with any null among the listed covariates (primary engaged): 0.

Formation counts (primary engaged): SHOTGUN=5638, SINGLEBACK=1278, EMPTY=800, I_FORM=286, PISTOL=238, JUMBO=31.

Play-action share among primary engaged reps: 25.4%; shotgun/empty share 77.8%.

### Player baselines

`player_baselines.parquet`: 510 rows, 510 distinct players; 127 undrafted. 236 players appear in primary engaged reps. Missing shares (all players / players in engaged reps):

| column | missing_all | pct_all | missing_in_engaged | pct_in_engaged |
|---|---|---|---|---|
| combine_weight | 0 | 0.000 | 0 | 0.000 |
| arm_length | 0 | 0.000 | 0 | 0.000 |
| forty | 86 | 0.169 | 46 | 0.195 |
| ten_yd_split | 85 | 0.167 | 46 | 0.195 |
| short_shuttle | 309 | 0.606 | 129 | 0.547 |
| three_cone | 330 | 0.647 | 141 | 0.597 |
| ngs_athleticism_score | 0 | 0.000 | 0 | 0.000 |
| draft_year | 0 | 0.000 | 0 | 0.000 |
| combine_position | 0 | 0.000 | 0 | 0.000 |
| nfl_position | 0 | 0.000 | 0 | 0.000 |

## 7. Outcome file (sealed)

`engaged_outcomes_SEALED.parquet`: 29,269 rows (one per pair, same keys as `engaged_pairs.parquet`), keys unique: True; columns ['pressure_allowed', 'peak_pressure_probability_allowed', 'sack_allowed', 'time_to_pressure_allowed', 'rusher_time_to_pressure', 'rusher_quick_pressure', 'rusher_sack']. Only the allowed populated-check numbers, computed in memory before writing: primary engaged reps with `pressure_allowed` true = **787** (base rate **0.0952**; null outcomes among engaged reps: 0). Nothing else about outcomes was computed.

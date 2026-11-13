# Candidate research questions: BDB 2027 (Combine tracking to NFL performance)

Written after reading `reports/audit_combine.md` and `reports/audit_game.md` in full. A few extra counts that the audits did not tabulate were computed with light read-only queries; they are marked **[q]**. Anything inferred rather than counted is marked *inference*.

## 0. How the candidates were chosen

Four facts in the audits shaped the whole list.

1. **Skill drills have no opt-out problem, but the timed agility tests do.** Every one of the 510 players has position skill-drill tracking. Tracked 3-cone and shuttle cover only 160 and 170 players (DL 45 and 38 of 118; DB 24 and 28 of 122), and opting out is not random. The 40 is broad (418 players), but the recording starts with the athlete already moving and ends at top speed, and many entrants will use it. The candidates therefore lean on skill drills. That gives a practical selling point: *"the drill everyone runs gives you a reading the agility test would have given, for the 50-65% who skipped it."*
2. **Only a few drills have genuine repeats.** Same-start repeats at scale exist for the 40 (375 players) and the OL PASS_RUSH_DROP (117). The DL PASS_RUSH_DRILL (101 players), DB BACK_PEDAL_AND_TRANSITION_45 (119), DB LINE_DRILL (99) and WR/TE GAUNTLET (93 / 40) have two reps on opposite sides. Those support a cross-side consistency check, which is a lower bound on reliability, but not a true test-retest. Everything else is one rep per player.
3. **Player-level outcome tests are underpowered.** At n = 60-90 the two-sided 5% critical |r| is about 0.21-0.25. An observed correlation is attenuated by sqrt(reliability of drill trait × reliability of outcome). A true r of 0.35 with reliabilities of 0.7 and 0.6 is observed at about 0.23. So a design that rests only on "drill trait → season outcome" will most likely end in an ambiguous null.
4. **Game tracking lets us measure the same movement in games, with hundreds of reps per player.** That makes a three-link chain possible, and every recommended candidate uses it:
   - **(a) Reliability.** Does the drill trait repeat?
   - **(b) Transfer.** Does the player move the same way in NFL games? The in-game version averages hundreds of snaps, so it is highly reliable. It needs only about 30 snaps, so PRE snaps can be included, n roughly doubles, and backups and undrafted players come in, which eases selection on playing time.
   - **(c) Mechanism.** Does that in-game movement relate to the NFL outcome? This link can be estimated at the play level with tens of thousands of snaps.

   The confirmatory test, whether the drill trait predicts the outcome beyond the baselines, is then specified in advance and run once. The chain is much more likely than a bare correlation to give a defensible, non-null story. It also handles "football complexity" naturally: the in-game link is where context (alignment, scheme, dropback time) gets adjusted.

**A deliberate choice you may want to overrule.** The feasibility checks below test reliability, non-redundancy with the stopwatch, in-game reliability, transfer, outcome reliability and the in-game mechanism. They do **not** compute the final drill-trait → outcome correlation. The project plan asks for the question and outcome to be stated before outcome data are seen. A feasibility check that peeks at that correlation, and then a metric chosen because it looked good, would be exactly the forking-paths problem a skeptical judge will look for. The primary drill metric is to be chosen on reliability and transfer only.

---

## Shared conventions for every feasibility check

- **Combine tracking.** Filter `entity_type == 'PLAYER'`. Order a player's attempts by `time`, not by `attempt`: the numbering is per drill_name in 2023/24 but a running count per drill_type in 2025, and 5-25% of groups have missing numbers. Merge the renames LINE → LINE_DRILL, PASS_PRO_MIRROR_DRILL → PASS_PRO-MIRROR_DRILL, and SPEED_OUT_LEFT → SPEED_OUT_ROUTE_LEFT.
- **Never use `dis`**; distance comes from x/y. **`a` is an unsigned magnitude**, so signed along-track acceleration = centred difference of `s` / 0.2 s. `dir` follows atan2(dx, dy) in degrees: 0 = +y, 90 = +x, clockwise. For heading change, unwrap `dir`, take the centred difference, and convert to rad/s. Centripetal (turning) acceleration = s × |dθ/dt|. Smooth with a 3-frame centred mean and report a 5-frame sensitivity for every metric.
- **Crop robustness.** Drill recordings are cropped differently by year: 2025 DL PASS_RUSH_DRILL starts with median s = 0.17 yd/s versus 0.52-0.59 in 2023/24, and the 40 starts already moving. Time metrics must therefore be **threshold-crossing times** (for example, time from s first ≥ 1.0 to s first ≥ 4.0 yd/s), never "time from frame 0". Report the metric's mean and SD by draft year. Flag any year whose mean differs from the others by more than 0.5 pooled SD, and use year-standardised values if it does.
- **Game tracking.**
  - t = 0 is the `ball_snap` frame.
  - With `play_direction == 'left'`, the offence moves toward decreasing x (audit D: the offence has the larger mean x when left). So "toward the offence's own end zone" (the OL retreat, a rusher's upfield) is +x when left and −x when right.
  - Join to `player_play` on (game_id, play_id, nfl_id).
  - Exclude `lined_up_position == 'NA'`. A dropback is `pass_result <> ''` (the empty string, not null).
  - Flag play-action with the `play_action` / `autoevent_playaction` event tags.
- **Season types.** Outcomes use REG (+POST as a sensitivity). Kinematic in-game traits may use PRE+REG+POST with a season-type covariate. Report both.
- **Baselines.**
  - `draft_overall_pick` (undrafted set to 262, plus an undrafted indicator), `combine_weight`, `arm_length`, `forty`, `ten_yd_split`, `short_shuttle`, `three_cone` (with missing indicators), `ngs_athleticism_score` and `ngs_final_score`.
  - Use position-group-specific z-scores.
- **Statistics.**
  - Pearson and Spearman. Partial correlations by residualising both variables.
  - Bootstrap 95% CIs: 2,000 resamples, seed 2027.
  - Split-half reliability uses odd/even snaps by chronological order, Spearman-Brown corrected.
  - Critical |r| at α = 0.05: n = 40 → 0.31, 60 → 0.25, 80 → 0.22, 100 → 0.20, 120 → 0.18.
- **Logging and output.** Log every metric definition tried. Pick the primary drill metric by the stated rule (reliability, then non-redundancy), not by eye. Return a table of gate results (value, CI, n, pass / amber / fail), and mark verified numbers separately from assumptions.

---

## C1. OL pass set: does a lineman's Combine kick-step show up in his NFL pass sets, and does it keep the quarterback clean?

**1. The question.** *"How fast does he get out of his stance and into his set?"* Can the Combine pass-set drill tell you which linemen will set quickly in the NFL and allow less pressure, beyond the shuttle, the 10-yard split and his size?

**2. Drill and trait.**
- **Drill:** SKILL_DRILLS_OL / PASS_RUSH_DROP. 120 OL, 118 with two reps, and 117 same-start pairs (start-point median 0.5 yd apart, 0% more than 3 yd apart). This is the only skill drill in the dataset with genuine test-retest repeats at scale.
- **Shape [q]:**
  - Phase 1, roughly 0-2.0 s, is a slow backward set (−x, about 1.5-2.2 yd/s, about 1 yd of depth by 1.0 s and about 2 yd by 2.0 s).
  - Phase 2, roughly 2.5-4.0 s, is an acceleration to about 5.5 yd/s, still moving −x. *Inference:* the athlete opens his hips and runs, as when recovering against a speed rush. There is no orientation at the Combine to confirm this.
  - Durations are similar across years (4.2-4.5 s).
- **Traits**, onset = the first of 3 consecutive frames with s ≥ 0.5:
  - **Primary (set-quickness family):**
    - `set_depth_1s`: net displacement from the onset position at onset + 1.0 s.
    - `set_burst`: time from s ≥ 0.5 to s ≥ 1.5 yd/s.
    - `peak_set_speed`: max s in onset..onset + 1.5 s.
  - **Secondary:**
    - `open_and_run`: time from s ≥ 2.0 to s ≥ 4.5 yd/s after onset + 1.8 s.
    - `set_lateral_drift`: |Δy| at onset + 1.5 s.
- **Why the stopwatch cannot see it.** No official test measures backward or lateral movement out of a stance at sub-maximal speed. The shuttle (53% of OL have one) is a maximal lateral change of direction, and the 10-yard split is forward acceleration. A pass set is a controlled, sub-maximal movement with a specific geometry, measurable only from position data.

**3. Outcome and context.**
- **In-game kinematic (transfer link).** On every OL pass-block snap (`pressure_allowed` non-null), compute from game tracking:
  - Euclidean and backward (toward own end zone) displacement at snap + 0.5 s and + 1.0 s.
  - Peak speed in snap..snap + 1.0 s.
  - Time to 1 yd of displacement.

  Take the player mean of play-level residuals from a regression on `lined_up_position` (T/G/C), shotgun vs under-centre (`offense_formation`), the play-action flag, a `dropback_duration` bucket and season type.
- **Primary NFL outcome.** `peak_pressure_probability_allowed`, which is continuous, populated on 95.5% of pass-block snaps, and should be far more stable than the binary pressure rate. Take the player mean of play-level residuals after adjusting for `dropback_duration`, `pass_rushers_encountered`, `lined_up_position`, shotgun and play-action.
- **Secondary NFL outcomes.** `pressure_allowed` rate, with beta-binomial empirical-Bayes shrinkage and a base rate of 8.4%, and `time_to_pressure_allowed` on pressured snaps.
- **Whole-cohort secondary outcome.** Career snaps residualised on draft pick and class: did teams keep playing him beyond his draft slot? This uses all 120 OL and avoids range restriction, but mixes performance with team decisions. Report it, but do not headline it.
- **Context the judges will look for:**
  - Tackle vs guard vs centre: pressure rates are 9.8% / 7.9% / 6.0%.
  - QB time to throw.
  - Team / offensive scheme: jump sets and quick game. Adjust with a leave-one-out team-season mean of cohort-OL set depth; cohort OL teammates share 17,282 plays.
  - Opponent quality: unobserved for non-cohort rushers. This is partly addressable via the C3 matchup extension.

**4. Sample [q].**
- 120 OL with the drill.
- Pass-block snaps:

  | threshold | REG | PRE+REG+POST |
  |---|---|---|
  | ≥ 30 | 74 | 110 |
  | ≥ 100 | 65 (66 with POST) | 88 |
  | ≥ 200 | 59 | 67 |

- So the transfer link has about 110 players and the outcome link 66-88.

**5. Threats and how to bound them.**
- **Scheme drives the in-game set** (jump sets, quick game, play-action). Use play-level residualisation and team-season adjustment; drop play-action and dropbacks shorter than 2.0 s as a sensitivity.
- **Pressure is noisy and partly team / QB-driven.** Use the continuous pressure probability, report outcome split-half reliability and disattenuated correlations, and shrink low-exposure players.
- **Range restriction.** OL snaps vs pick Spearman = −0.71, the strongest of any group. Mitigate by including PRE for the transfer link; reweight by inverse probability of reaching ≥ 100 snaps (modelled on pick, NGS score, weight); compare the drill-metric distribution of included vs excluded players.
- **Size confound.** Heavier linemen may set more slowly but anchor better. Always control for weight and arm length, and report within T and within G.
- **Is the drill coached to a fixed footwork pattern** (little between-player variance)? The reliability gate tests this directly.
- **Year drift.** Year-standardise if needed.
- **Unknown phase-2 semantics.** Treat `open_and_run` as secondary and exploratory.

**6. Originality.** Moderate to high. The hosts' example list names "first-step quickness, lateral agility and burst for OL/DL" (*inference*: so some entrants will do OL). The obvious versions are probably 3-cone/shuttle tracking (opt-out-limited) or the mirror drill (one rep) against pressure rate. What would make ours distinct:
- The only true test-retest skill drill.
- An explicit transfer test to in-game sets, which nobody can do without game tracking.
- PRE inclusion to reach backups.
- Optionally, opponent-adjusted reps (C3).

I have not surveyed public notebooks. A 15-minute forum and notebook search for "pass set", "kick slide", "OL" and "PASS_RUSH_DROP" should be part of the feasibility run.

**7. Actionable use.**
- Add a named, repeatable "Set Speed" reading to OL grades, especially for linemen who skipped the shuttle and 3-cone (47-50% of OL).
- Use it in the **tackle-or-guard projection**, the most common OL draft dilemma (C1 extension: test whether the set-speed → pressure slope is steeper for snaps at T than at G; `lined_up_position` shows T at G on 1,959 rows and G at T on 1,062).
- Give OL coaches a development target with an NFL-calibrated benchmark: depth at 1.0 s.

**8. Feasibility check (about 1 hour).**
- **G1, drill reliability.** For the 117 same-start pairs, compute `set_depth_1s`, `set_burst` and `peak_set_speed` per rep, plus the 5-frame-smoothing variants. Pearson between the chronologically first and second rep, and ICC(2,1). Report by year.
  - **Go:** best set metric r ≥ 0.60.
  - **Amber:** 0.40-0.60.
  - **No-go:** all < 0.40.
  - Primary metric = the most reliable of the three that also passes G2. On a tie, use `set_depth_1s`.
- **G2, non-redundancy.** Correlate the two-rep mean with `ten_yd_split`, `short_shuttle`, `three_cone`, `forty`, `combine_weight` and `arm_length`, within OL.
  - **Go:** all |r| < 0.60.
  - **No-go:** any |r| > 0.75; it is then a stopwatch proxy.
- **G3, in-game reliability.** For OL with ≥ 30 PRE+REG+POST pass-block snaps, compute the adjusted in-game set metrics above, then split-half reliability.
  - **Go:** ≥ 0.70 with n ≥ 90.
  - Also report raw means by `lined_up_position` as a sanity check: tackles should get more depth than guards, and guards more than centres.
- **G4, transfer.** Correlate the drill primary metric (two-rep mean) with the matching adjusted in-game metric (depth at 1.0 s, or peak speed in 0-1.0 s).
  - **Go:** r ≥ 0.25 in the expected direction, and partial r (controlling weight, plus ten_yd_split where present) ≥ 0.20.
  - **No-go:** r < 0.10.
- **G5, outcome usable and mechanism plausible.**
  - Outcome split-half reliability for OL with ≥ 100 REG pass-block snaps: **go ≥ 0.50** for the adjusted peak-pressure-probability mean.
  - Play-level mixed model or a simple between-player correlation of the in-game set metric with the adjusted outcome, controlling `lined_up_position` mix.
  - **Go:** partial r ≤ −0.20 (quicker or deeper set → lower pressure probability).
  - The drill metric is **not** correlated with the outcome at this stage.
- **Decision.** Go if G1, G2 and G3 pass and at least one of G4 / G5 passes. If G1 passes but both G4 and G5 fail, C1 becomes a "valid but non-transferring drill" null story, which is weaker. Prefer the fallback then.

---

## C2. Edge bend: is "bend" a measurable, repeatable Combine trait, and do rushers who carry speed through the turn get home in the NFL?

**1. The question.** *"Can he bend the edge without losing speed?"* Does the DL pass-rush drill measure a turning-at-speed ability that the 10-yard split and 3-cone miss, and does the same ability in games produce pressure?

**2. Drill and trait.**
- **Drill:** SKILL_DRILLS_DL / PASS_RUSH_DRILL. 114 DL plus 4 LB-drill rushers; 102 with one rep on each side.
- **Documented geometry:**
  - Right rep: start near (45, 23.75), bags at (45, 23.75) and (49, 24.25), finish through y = 39, swim move.
  - Left rep: start near (45, 30.25), finish through y = 15, rip move.
- **Shape [q].**
  - About 6 yd straight in +x (accelerating to about 4.2-4.5 yd/s by 1.5 s).
  - A turn of about 90° toward the finish line between roughly 1.5 and 3.0 s, during which speed rises to about 7.5 yd/s.
  - The 2025 crop starts about 0.5 s earlier (more stationary lead).
- **Traits:**
  - **`get_off`:** time from s ≥ 1.0 to s ≥ 4.0 yd/s. Crop-robust.
  - **Bend family.** The turn window runs from heading deviation ≥ 15° to ≥ 75° from the initial run heading.
    - `turn_accel`: mean centripetal acceleration s·|dθ/dt| in the window.
    - `turn_min_speed`: min s in the window.
    - `speed_carry`: s at 75° divided by s at 15°.
    - `turn_time`: duration of the window.
  - **`side_asymmetry`:** left (rip) minus right (swim) for each bend metric.
- **Why the stopwatch cannot see it.** The 10-yard split measures straight-line burst. The 3-cone is the only official test with a turn, and only 45 of 118 DL have a tracked 3-cone (36% have an official one). Even then it is a total time that mixes braking, turning and re-acceleration. Speed carried through a specific, football-shaped corner exists only in the position data.

**3. Outcome and context.**
- **In-game kinematics.** On every rush snap (`blitzing` and dropback):
  - `player_get_off`, supplied by NGS on 94% of EDGE rush snaps.
  - Tracking-derived in-game bend in the window snap + 0.3 s to the earlier of snap + 3.0 s or pass_forward / qb_sack:
    - max smoothed s·|dθ/dt| over frames with s ≥ 3.5 yd/s.
    - mean speed over frames whose heading has deviated 30-80° from the upfield direction (+x if play_direction is left).
  - Restrict the bend metrics to snaps aligned at `lined_up_position == 'EDGE'`. Get-off uses all rush snaps.
- **Outcome.**
  - Pressure rate per rush snap (`time_to_pressure` non-null): 11% EDGE, 7% IDL. Beta-binomial shrinkage.
  - Secondary: quick-pressure rate, sacks per rush snap, and residual career snaps on pick.
- **Context:**
  - Alignment (EDGE vs INTERIOR_LINE; DE play inside on 6,934 rows).
  - Dropback duration (opportunity).
  - Team defence and stunts. Stunts are not tagged; the speed gate is a partial filter.
  - Double teams: not observable except via C3.
  - Down and distance (obvious passing downs inflate pressure).

**4. Sample [q].**

| group (with drill) | rush snaps ≥ 30, REG | ≥ 30, PRE+REG+POST | ≥ 100, REG | ≥ 100, PRE+REG+POST |
|---|---|---|---|---|
| All DL (118) | 85 | 111 | 65 | 84 |
| EDGE (DE/OLB, 66) | 48 | 60 | 39 | 48 |

There are 26 EDGE and 18 IDL with ≥ 20 / ≥ 10 pressures (audit). The bend analysis is effectively EDGE-only, so its n is 48-60. Get-off can pool all DL with a group indicator.

**5. Threats.**
- **The two drill reps differ by side and by move** (rip vs swim), so cross-side agreement is only a lower bound on reliability. *Mitigation:* frame it as such, and use the asymmetry as a feature (see below).
- **Small EDGE n.** *Mitigation:* the chain design; the transfer link at ≥ 30 snaps with PRE gives n ≈ 60.
- **In-game turning reflects the rush plan, the tackle's set and the QB's drop depth.** The QB is not tracked, so turning is not measured relative to the QB. *Mitigation:* speed gating, an EDGE-only restriction, and team-season adjustment.
- **Draft capital.** EDGE snaps vs pick ρ = −0.52, IDL −0.80. Handle as in C1.
- **Year crop differences.** Use threshold-crossing metrics and year standardisation.
- **A within-player robustness design exists here and almost nowhere else.**
  - Rushers line up on both sides in games.
  - Correlate the drill's rip-side minus swim-side bend difference with the player's in-game bend difference when turning left vs turning right.
  - Draft pick, size and the 40 are constant within a player, so any association cannot come from those confounds.
  - This is exploratory (noisy), but if positive it is a striking robustness check.

**6. Originality.** Medium.
- DL "first-step quickness / burst vs pass rush" is literally in the hosts' example list. Get-off vs pressure will be the single most common trench entry (*inference*).
- BDB 2023 was about linemen on pass plays, so judges know in-game pass-rush metrics well.
- What would make ours distinct:
  - Bend, defined physically as centripetal acceleration at speed, rather than get-off.
  - The drill-to-game transfer test.
  - The within-player side-asymmetry check.

**7. Actionable use.**
- A named "Bend" reading for every DL, including the 64% with no 3-cone.
- It identifies Day 2-3 edges with ordinary 10-yard splits but elite turning, who would be undervalued by a stopwatch-based board.
- It separates "get-off" rushers from "bend" rushers, which is useful for role and scheme fit (wide-9 speed rusher vs tighter alignment).
- Coaching: does a rusher's weaker side in the drill match his weaker side in games?

**8. Feasibility check (about 1 hour).**
- **G1, cross-side consistency.** For the 102 players with both sides, compute the left-rep vs right-rep Pearson.
  - **Go:** `get_off` r ≥ 0.60 and at least one bend metric r ≥ 0.40.
  - **No-go:** all bend metrics r < 0.25.
  - Report year means; check the 2025 crop.
- **G2, non-redundancy.** Correlate each player's two-side mean bend metric with `ten_yd_split`, `forty`, `combine_weight` and (where present) `three_cone`.
  - **Go:** all |r| < 0.60.
  - Also report `get_off` vs `ten_yd_split`. A high correlation is expected and fine, but it means get-off is not the novel part.
- **G3, in-game reliability.** Split-half reliability of `player_get_off` (go ≥ 0.70) and of the in-game bend metric on EDGE-aligned snaps (go ≥ 0.60), for players with ≥ 30 rush snaps (PRE+REG+POST). Report n.
- **G4, transfer.** Drill `get_off` vs in-game `player_get_off` (go r ≥ 0.25). Primary drill bend metric vs in-game bend (go r ≥ 0.25), pooled DL with an EDGE/IDL indicator, then EDGE only.
- **G5, outcome usable and mechanism plausible.**
  - Pressure-rate split-half reliability for ≥ 100 REG rush snaps: **go ≥ 0.50**.
  - Between-player partial r of in-game bend with shrunk pressure rate, controlling in-game get-off and EDGE/IDL: **go ≥ 0.25**.
  - The drill metric is not correlated with outcomes at this stage.
- **G6 (exploratory, report only).** Within-player asymmetry: drill (left − right) vs in-game (turning in the matching direction − the other direction). Report r, n and CI.
- **Decision.** Go if G1 (bend part), G2 and G3 pass and either G4-bend or G5 passes. If only `get_off` passes, C2 collapses to the crowded get-off entry: no-go.

---

## C3. The rep itself: when a Combine-measured lineman meets a Combine-measured rusher, does the athletic gap between them decide who wins?

**1. The question.** *"Is he quick enough to handle a speed rusher?"* On NFL pass-pro reps where both the blocker and the rusher are in the cohort, does the Combine-measured difference between them (set speed vs get-off or bend, plus length and weight) predict pressure on that rep?

**2. Drill and trait.** Both sides' traits from C1 and C2 (OL `set_depth_1s` / `set_burst`; DL `get_off` / bend), plus PASS_PRO-MIRROR_DRILL lateral metrics (121 OL, one rep: lateral reversal time, peak lateral speed). Add the official differentials: weight, arm length, 10-yard split. The stopwatch argument is as in C1/C2. The new idea is *relative* athleticism, which no single-player test can express.

**3. Outcome and context.**
- **Unit of analysis.** The engaged rep: a cohort OL on a pass-block snap and a cohort opposing rusher on the same play who come within blocking distance in the tracking (definition in the feasibility check).
- **Outcomes per rep:**
  - OL `pressure_allowed`.
  - Rusher pressure (`time_to_pressure` non-null).
  - `peak_pressure_probability_allowed` (continuous).
- **Model.** Logistic / linear mixed model with crossed random effects for blocker and rusher, play context (dropback duration, alignment, down/distance, shotgun), and the trait differentials as fixed effects.
- **Why it matters.** It controls opponent quality, which the judges' "handles football's complexity" criterion rewards and which is the main objection to any OL or DL outcome.

**4. Sample [q].** Co-occurrence of a cohort pass-blocker and a cohort opposing rusher:

| season type | pairs | plays | blockers | rushers | OL pressures allowed | rusher pressures |
|---|---|---|---|---|---|---|
| REG | 27,747 | 15,646 | 127 | 159 | 2,376 | 2,828 |
| PRE | 6,533 | | | | | |
| POST | 1,524 | | | | | |

The blocker count includes some TE/WR. How many pairs are actually engaged is unknown: *inference*, perhaps 25-40%, that is 7,000-11,000 REG reps. The feasibility check measures it.

**5. Threats.**
- **Engagement misclassification.** Stunts, double teams, and a rusher passing by a guard on the way to a tackle can all look like engagement. Report sensitivity to the distance and duration thresholds, and flag double teams (two cohort OL engaged with one rusher).
- **Pressure attribution.** The pressure may come from a different rusher. Use a coherence check: engaged OL pressure_allowed should coincide with the engaged rusher's pressure far more often than in non-engaged co-occurring pairs.
- **Selection.** Only reps where both players are cohort, which skews to 2024-25 seasons when more cohort players were active.
- **Reps are not independent.** Use crossed random effects; cluster bootstrap by player.
- **Complexity.** It is the hardest of the six to explain in 2,000 words.

**6. Originality.** High. It is only possible because both sides of the ball are in the cohort, and I would be surprised if many of the 500+ entries attempt it (*inference*). It is the most "tracking-vendor" idea on the list.

**7. Actionable use.**
- A matchup-level answer: "a tackle with set speed X neutralises rushers with get-off up to Y". That translates into a draft rule: which OL prospects can be trusted against the fastest edges.
- It also enables an opponent-adjusted pressure metric for young OL and DL, usable in pro scouting.

**8. Feasibility check (about 1 hour).**
- **G1, engagement and coherence.**
  - For every REG+POST co-occurring pair, align both players' frames by time.
  - Compute distance d(t) from snap + 0.2 s to the earliest of snap + 3.0 s, pass_forward or qb_sack.
  - Define **engaged** = at least 4 frames with d ≤ 1.5 yd. Sensitivity: 1.25 / 2.0 yd and 3 / 6 frames.
  - Report:
    - The number of engaged reps, distinct OL and distinct rushers.
    - Players with ≥ 10 engaged reps.
    - The share of plays with more than one cohort OL engaged with the same rusher.
    - **Coherence**: P(rusher pressure | engaged and OL pressure_allowed) versus the same quantity in non-engaged co-occurring pairs.
  - **Go:** ≥ 4,000 engaged REG+POST reps, ≥ 60 OL and ≥ 60 rushers with ≥ 10 reps each, and coherence ≥ 40% and ≥ 2× the non-engaged rate.
  - **No-go:** fewer than 2,000 reps or coherence < 30%.
- **G2, the design can see a known effect.** Logistic regression of OL `pressure_allowed` on standardised (rusher pick − OL pick) and (rusher weight − OL weight), with dropback duration as a control and cluster-robust SEs by OL.
  - **Go:** the pick differential has the expected sign (better-drafted rusher → more pressure) at p < 0.05.
  - This uses the outcome but no Combine-tracking metric. It only tests whether the rep-level design has power.
- **Decision.** If G1 passes, C3 becomes a module inside whichever of C1/C2 is chosen: opponent adjustment plus an interaction chart. On its own it is too complex to be the whole entry unless C1 and C2 both fail their transfer gates.

---

## C4. Catching in stride: does the Combine gauntlet show which receivers keep their speed through the catch, and do they produce more after it?

**1. The question.** *"Does he gear down to catch?"* Does WR gauntlet speed retention, beyond 40 speed, predict in-game speed through the catch and yards after catch over expected?

**2. Drill and trait.**
- **Drill:** SKILL_DRILLS_WR / GAUNTLET_DRILL. 107 WR; 93 with two reps run in opposite directions across the field (start y ≈ 0 or ≈ 54.5).
- **Traits**, over the middle segment y ∈ [8, 46]:
  - `gauntlet_speed`: mean s.
  - `speed_dips`: the number and depth of local speed minima with a drop ≥ 0.7 yd/s.
  - `retention`: `gauntlet_speed` / max s in the player's tracked 40. The 40 exists for about 94 of 107 WR.
  - `lateral_wobble`: SD of x.
- Ball tracking exists only for the 2025 class (37 WR), which can confirm that the dips coincide with catches.
- **Why the stopwatch cannot see it.** The 40 measures speed without catching. The retention ratio is defined only relative to tracked speed while catching.

**3. Outcome and context.**
- **In-game transfer.** On catches (`pass_outcome_caught`): the ratio of mean s in the 0.5 s after `pass_arrived` to mean s in the 0.5 s before, adjusted for route (`route_ran`), pass length and separation at pass forward.
- **Outcome.** YAC over expected (`yards_after_catch − expected_yards_after_catch`, available on about 91% of targets) per catch, shrunk.
- **Context.** Route type (screens and crossers dominate YAC), coverage, and the ball location relative to the receiver (not observable except via separation).

**4. Sample [q].** 106 WR with the gauntlet.

| REG measure | ≥ 30 | ≥ 50 | ≥ 100 |
|---|---|---|---|
| targets | 49 | 35 | 24 |
| catches | 39 | 29 | 11 |
| routes | 73 | 68 | 62 |

Adding PRE changes little for catches (≥ 30: 47). The outcome link has n ≈ 30-40.

**5. Threats.**
- **YACOE per player is very noisy.** At 30-50 catches the split-half is probably below 0.3 (*inference*).
- **YAC is scheme-driven** (screens, RPO slants).
- **Gauntlet throws vary in quality.**
- **Gauntlet duration changes by year.** It is fairly stable (8.9-9.2 s) for WR.
- **WR is the crowded position group overall.** This is not deceleration, but judges will have read many WR entries.

**6. Originality.** Fairly high for the specific trait. Low for the position group.

**7. Actionable use.** A "Catch-in-Stride" reading to separate vertical receivers whose speed survives contact with the ball from those who are fast only in shorts. It is relevant for YAC-centric offences.

**8. Feasibility check (about 1 hour).**
- **G1.** Cross-rep r for `retention` and `gauntlet_speed`. **Go:** `retention` r ≥ 0.50.
- **G2.** |r(retention, forty)| < 0.60.
- **G3.** In-game catch-speed ratio split-half for WR with ≥ 15 REG+POST catches. **Go:** ≥ 0.40 with n ≥ 45.
- **G4.** Transfer: drill retention vs in-game ratio. **Go:** r ≥ 0.25.
- **G5.** YACOE split-half for ≥ 25 catches. **Go:** ≥ 0.35. I expect this gate to fail, which is the main reason C4 ranks below C1-C3.

---

## C5. Click-and-close: does a DB's Combine transition show up as faster reaction to the throw in games?

**1. The question.** *"How quickly does he plant and drive on the ball?"* Does the backpedal-to-45° transition in the DB drill measure a transition cost (speed lost, time to re-accelerate) that shows up when NFL quarterbacks throw?

**2. Drill and trait.**
- **Drill:** SKILL_DRILLS_DB / BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION. 122 DB; 119 with two reps on mirrored sides.
- **Shape [q].** Backpedal in +x, accelerating to about 6-7 yd/s by 4 s, with the heading change at roughly 4.5-5 s.
- **Crop risk.** Median duration is 11.5 / 5.9 / 10.0 s in 2023 / 2024 / 2025, so many 2024 reps may end before or during the transition. Only 48 of 99 2024 reps last 6 s.
- **Traits:**
  - `transition_speed_loss`: s before the heading change minus the min s during it.
  - `transition_time`: the heading-change window.
  - `drive_accel`: max signed acceleration in the 1 s after.
  - Side asymmetry: the hip-flip direction.
- **Why the stopwatch cannot see it.** No official test involves a backpedal or a reactive transition.

**3. Outcome and context.**
- **In-game transfer.** On dropbacks with `pass_forward`, for CB/S with a real coverage assignment who are retreating at the throw: time from `pass_forward` until velocity toward the LOS becomes positive and reaches 2 yd/s, and peak acceleration in the 1 s after. Adjust for zone vs man, depth, and alignment.
- **Outcome.** Weak by construction. There is no defender-level target, completion or yards allowed. The only route is play-level pairing with a cohort targeted receiver: 6,318 REG pairs of a targeted cohort receiver and a cohort DB in assigned coverage (1,634 in man) across 136 DBs **[q]**, of which some fraction have the DB within about 2 yd at pass_arrived. Outcomes would be completion, YAC, and separation at arrival on those plays.

**4. Sample [q].** 113 CB/S with the drill; 67 with ≥ 100 REG assigned-coverage snaps (71 at ≥ 50). The outcome-bearing paired plays will probably number roughly 10-25 per DB (*inference*).

**5. Threats.**
- No defender outcome.
- The 2024 crop may remove the transition.
- Ball location is unknown in games.
- Zone reactions depend on QB eyes and scheme.
- **This overlaps directly with the crowded "WR braking vs DB recovery" angle** that is already public.

**6. Originality.** Low to medium, given the public forum post.

**7. Actionable use.** A transition-cost reading to separate man-coverage corners from zone corners. It would be real if it held, but it is hard to validate here.

**8. Feasibility check (about 1 hour).**
- **G1.** Share of reps containing a heading change ≥ 30° after t = 2 s, by year. **Go:** ≥ 85% in every year.
- **G2.** Cross-side r of the primary transition metric. **Go:** ≥ 0.40.
- **G3.** In-game throw-reaction split-half. **Go:** ≥ 0.50 with ≥ 60 DBs at ≥ 30 qualifying throws.
- **G4.** Transfer. **Go:** r ≥ 0.25.
- **G5.** Count plays with the targeted cohort receiver and the cohort DB within 2.0 yd at `pass_arrived`. **Go:** ≥ 1,500 plays across ≥ 60 DBs.

---

## C6. The 40 hides two numbers: does the tracked sprint profile (top speed vs acceleration) add anything the stopwatch 40 does not?

**1. The question.** *"Two guys run 4.45; one is a 10-yard guy and one is a 40-yard guy. Which matters for his position?"*

**2. Drill and trait.**
- **Drill:** FORTY_YARD_DASH. 418 players; 375 with two same-start runs (start positions 0.29 yd apart).
- **Traits:**
  - `Vmax`: max smoothed s; p50 10.6 yd/s.
  - The acceleration time constant τ, from fitting s(t) = Vmax(1 − e^{−(t − t0)/τ}) with t0 free. This copes with the moving start (first-frame s ≈ 0.6 yd/s).
  - Speed at 10 and 20 yd.
- **Why the stopwatch cannot see it.** The official 40 and 10-yard split compress the profile into two times. The tracked 10-yard time correlates only 0.4-0.5 with the official split because of the crop, so the split is not a clean acceleration measure.

**3. Outcome and context.**
- **Transfer.** In-game top speed: the mean of a player's 5 fastest per-play max speeds, REG+PRE, with a minimum of 30 plays.
- **Position outcomes.** WR separation at pass forward on GO/POST/CORNER routes (adjusted for cushion and coverage). DB / EDGE in-game get-off or closing speed.
- **This is the hosts' "sensor vs stopwatch" example.** The contribution would be the framing: where tracking adds context.

**4. Sample.** 418 players with the drill; WR deep routes from 62 WR with ≥ 100 routes. The largest n of any candidate.

**5. Threats.**
- **Vmax and the 40 are highly collinear** (*inference*: |r| ≈ 0.8). The most likely result is "nothing beyond the 40 time".
- In-game top speed is context-limited: few plays reach max speed for OL/DL.

**6. Originality.** Low. Top speed from the 40 is the first thing most of the 500+ teams will have computed.

**7. Actionable use.** Position-specific weighting of acceleration vs top speed. It is useful but incremental, and teams with GPS data from pro days already do this.

**8. Feasibility check (about 1 hour).**
- **G1.** Test-retest r. **Go:** `Vmax` ≥ 0.85 and τ ≥ 0.60.
- **G2.** Within position: |r(Vmax, forty)| and |r(τ, ten_yd_split)|. **Go if either < 0.75**, meaning independent variance exists.
- **G3.** In-game top-speed split-half. **Go:** ≥ 0.70.
- **G4.** Partial r(Vmax, in-game top speed | forty, weight). **Go:** ≥ 0.20, n ≥ 200.
- Keep this as a robustness or sidebar check within the chosen entry rather than as the entry itself.

---

## Considered and rejected (one line each)

- **WR deceleration into breaks vs separation.** Crowded (public forum post), and individual WR routes have only 8-15 repeat players.
- **TE anything.** 22 TE with ≥ 100 REG routes and 5 with ≥ 100 targets.
- **LB.** 4 players did LB drills.
- **Tracked 3-cone / shuttle.** 160 / 170 players, with non-random opt-outs.
- **OL run blocking.** No player-level run outcome exists on OL rows (audit B6).
- **Tackling / run defence.** Tackles are recorded only when credited; no missed tackles.
- **Honours.** 12 players.
- **Ball skills from 2025 ball tracking.** One class, 37 WR, and the outcome is catch rate on contested targets with a tiny n.

---

## Ranking

Scores are my judgment on a 1-5 scale.

| Rank | Candidate | Football value | Stats defensibility | Originality | Feasibility risk (lower = better) | Visual potential | Most likely outcome |
|---|---|---|---|---|---|---|---|
| 1 | **C1 OL pass set** | 4 | **5** (true repeats; n 110 for transfer) | 4 | Medium | 4 (drill set vs game set trajectories) | Reliable, distinct trait; moderate transfer; weak-moderate pressure link |
| 2 | **C2 Edge bend** | **5** | 3.5 (cross-side only; EDGE n ≈ 48-60) | 3 | Medium-high | **5** (curvature arcs on the bag layout) | Get-off transfers but is a stopwatch proxy; bend uncertain; pressure mechanism plausible |
| 3 | **C3 Rep matchup** | 4.5 | 3.5 (rep-level power, attribution risk) | **5** | High | 4 | Strong as a module; risky as the whole entry |
| 4 | C4 Catch in stride | 3 | 2.5 (YACOE noise, n ≈ 35) | 3.5 | Medium | 3.5 | Reliable drill trait; outcome too noisy |
| 5 | C5 Click-and-close | 3.5 | 2 (no defender outcome, crop risk) | 2 | High | 3.5 | Transfer maybe; outcome unvalidatable |
| 6 | C6 Sprint profile | 3 | 4 (huge n, clean repeats) | 1.5 | Low | 3 | "Nothing beyond the 40" |

### C1 OL pass set: the recommendation

It is the only candidate where every link of the chain can be measured cleanly:
- **Reliability.** A genuine same-start test-retest on 117 players.
- **Transfer.** About 110 players with ≥ 30 in-game pass sets.
- **Outcome.** A continuous NGS pressure-probability outcome for 66-88.

The trait is a movement no official test measures (a controlled backward set from stance). It also comes from a drill every OL ran, so it covers the half of the position group that skipped the shuttle and 3-cone. The football framing (how fast he gets into his set; can he stay at tackle) is the language of OL coaches. OL is the position where clubs have the least objective evaluation. It is less crowded than trench pass rush.

### C2 Edge bend: the fallback, with the higher ceiling

If it works, "bend at speed, measured physically, transfers to games and drives pressure" is the most quotable headline on the list, about a premium position, with the best figure (curvature on the documented bag layout). Its weaknesses are statistical:
- Only cross-side reps.
- About 48-60 EDGE players.
- The get-off half of it is the single most obvious trench entry.
- The within-player side-asymmetry test is a genuinely distinctive robustness check if it holds.

### C3 Rep matchup: run its G1 regardless

Its engagement-detection check is cheap. If it passes, it should become the opponent-adjustment module and the "football complexity" figure of whichever of C1/C2 wins. It is too complex and too risky to be the whole entry.

### C4, C5, C6

- **C4** has a distinctive trait but an outcome that will probably not stabilise at n ≈ 35.
- **C5** cannot be validated on outcomes in this dataset and overlaps the public DB-recovery angle.
- **C6** is a clean, safe "sensor vs stopwatch" sidebar whose headline would most likely be "the 40 already captures it". It is worth computing as context, not worth building an entry on.

## Recommendation and decision rule

**Run feasibility checks in parallel on C1 (all gates), C2 (all gates) and C3 (G1-G2 only).** These are three independent one-hour jobs. Each must write only to its own scratch output. Then decide as follows:

| Outcome of the feasibility checks | Choice |
|---|---|
| C1 passes G1, G2, G3 and at least one of G4/G5 | **C1**, with C3 as a module if C3-G1 passes |
| C1 fails G4 and G5, and C2 passes its decision rule | **C2**, with C3 as a module |
| Both pass | **C1**, unless C2's G4-bend and G5 are both clearly stronger: r higher by ≥ 0.10 on both. Football value then tips it to C2 |
| Both fail transfer, and C3-G1 passes | Reconsider C3 as the main entry, framed as "opponent-adjusted trench reps" |
| Everything fails | Write the "framing is the contribution" entry: which skill-drill traits are reliable and non-redundant (a reliability atlas from G1/G2 of C1, C2, C4 and C5), and why most do not transfer. C6 goes in as the stopwatch comparison |

Also spend 15 minutes searching the Kaggle forum and public notebooks for OL pass-set and DL bend entries, to check the crowding assumptions above.

## What could make the recommendation fail

1. **The drill may be coached to a fixed footwork pattern**, so between-player variance is small and test-retest is low. G1 catches this in the first ten minutes.
2. **NFL pass sets are called, not chosen.** Jump sets, quick game, play-action and team protection schemes could swamp player differences, so the transfer r ends up near zero even if the trait is real. Team-season adjustment helps only partly, because there are few cohort OL per team-season.
3. **Pressure-allowed outcomes are among the noisiest player outcomes in football.** They depend on the QB's time to throw and on unseen opponents. At n = 66-88 even a true incremental effect of r ≈ 0.25 would probably come out "not significant". The writeup must then lean on the transfer and mechanism links and report the confirmatory effect with an interval rather than a p-value headline. Judges may see that as a weaker finding than a pass-rush result.
4. **Range restriction is strongest for OL** (pick vs snaps ρ = −0.71). Those who play are mostly Day 1-2 picks, already selected on the traits scouts see.
5. **Size confounding.** Set speed may be largely "lighter linemen move faster". If the partial r after weight collapses (G2/G4), the trait is a weight proxy.
6. **Phase semantics are inferred.** PASS_RUSH_DROP may not be the pass-set drill its name suggests. The trajectory is consistent with a set followed by a turn-and-run, but there is no orientation at the Combine to confirm it. The set-phase metric does not depend on that interpretation; `open_and_run` does.
7. **The judges may find OL less exciting than pass rush.** The writing has to make the set-speed and tackle-vs-guard framing vivid, with an overlay of a player's drill set and his median NFL set on the same axes.

If you disagree with the ranking, the strongest case against me is this: C2's outcome (rusher pressure rate) is more stable than C1's (pressure allowed), and its football ceiling is higher. A judge panel of club analysts may reward a credible bend result more than a credible OL result. My ranking puts more weight on C1's cleaner reliability design and lower crowding. The parallel feasibility checks are meant to settle exactly this.

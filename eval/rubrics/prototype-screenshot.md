---
multimodal: true
---

# Prototype build scoring rubric — transcript → specs → screenshot

You are grading **the entire OpenClaw transcript-to-prototype pipeline** as exercised by a single candidate model. The model under test served BOTH the orchestrator agent (Captain Nemo running the propose + build skills) AND the inner coder calls. You are scoring the *ecosystem performance with this model*, not any single message in isolation.

## What you receive

For each run, you receive some subset of:

1. **`transcript.txt`** — the original meeting/voice-memo input the user fed to the orchestrator.
2. **`chat-phase1.json`** — the orchestrator's chat trajectory while running the propose skill (Captain Nemo turns, tool calls, tool results).
3. **`specs/proposal.md`, `specs/design.md`, `specs/tasks.md`** — the OpenSpec artifacts the propose skill wrote (may be missing or partial).
4. **`chat-phase2.json`** — the orchestrator's chat trajectory while running the build skill (`prototypes.build` → `sessions_spawn` → polling loop).
5. **`source-tree.txt`** — recursive listing of `prototypes/<slug>/src/` (may be empty if build never wrote code).
6. **`build-status.json`** — `{port: int|null, container_running: bool, http_status: int|null, registry_entry: bool}`.
7. **`screenshot.png`** — Playwright capture of `http://localhost:<port>/` after the build reported done. May be missing (if the build never produced a reachable port), or may be a 502/blank page.

Some artifacts will always be missing on a failed run. **Score what you can see; do not punish the absence of an artifact when an upstream phase failed for a reason already captured.** A run that died in phase 1 should be scored as a phase-1 failure, not as a phase-1 failure *plus* phase-2 failure *plus* missing screenshot — that triple-counts the same root cause.

## Dimensions to weigh (jointly, single integer score)

- **Spec fidelity to transcript** — Do `proposal.md` / `design.md` / `tasks.md` actually capture what the user asked for in the transcript? Right slug? Right feature list? Did design.md respect the schema/seed consistency invariant and the air-gapped/local stack constraint? Did it tag third-party libraries with `kind: library` + a pinned URL when the transcript implies them?
- **Build trajectory quality** — Did the orchestrator actually invoke `prototypes.build` + `sessions_spawn` with sane args? Did the inner coder produce real code (schema, routes, frontend) versus stalling, looping, or emitting boilerplate? Did it recover from tool errors (port collisions, schema drift, missing libraries) or repeat the same broken call?
- **Visual coverage of requested features** — Does the screenshot show the UI elements the transcript explicitly asked for? (E.g. recipe-keeper transcript asks for "list view that shows title, prep time, rating, tried/not-tried, and a search bar at the top" — does the screenshot show those? Standup-tracker asks for a today-view with empty slots for missing people + a 30-day participation bar chart — visible?)
- **No broken UI** — Does the rendered page look like a working app or like a 502 / stack trace / blank canvas / unhidden loading overlay? Are interactive elements present (buttons, inputs) or is it a wall of unstyled text?
- **End-to-end coherence** — Does the slug used in chat match the slug in the spec dir match the slug in the registry? Did the orchestrator's final message to the user accurately describe what was built, or did it claim success while the screenshot shows a 500?

## Scoring anchors (use exactly one)

| Score | Anchor |
|---|---|
| **5** | Full ecosystem win. Specs faithfully cover every transcript ask. Build trajectory is clean — coder wrote real code, no infinite loops, recovered from any tool errors. Screenshot shows a working UI with the explicitly-requested elements visible (search bar, list view, chart, etc.) and styled enough to be obviously usable. Orchestrator's closing message matches reality. Reserve for runs you'd cite as "yes, this model can drive the whole pipeline." |
| **4** | Good. Reached a live, browsable prototype with most requested features visible. At most one substantive miss: e.g. specs glossed over one requirement, or the bar chart is missing but the rest of the UI works, or the orchestrator's summary slightly oversold what shipped. The user could fix the gap in one follow-up turn. |
| **3** | Partial success. Either (a) specs are good and build half-worked — code wrote, container started, but UI is missing requested features OR the screenshot shows a recognisable-but-broken page (one component 500s, half the routes 404, overlay stuck on); or (b) the build never reached a screenshot but the specs themselves are solid and would produce a good prototype if a stronger coder ran them. Score 3 when the user got *something* useful out of the run even if the prototype isn't actually usable. |
| **2** | Weak. Specs landed but build trajectory was a mess — coder looped on the same broken call, hand-wrote a minified library instead of curling it, schema/seed drift caused crashloop, OR build "succeeded" but the screenshot is a blank page / 502 / stack trace. Also score 2 when specs themselves badly miss the transcript (wrong slug, wrong stack, invented features the user didn't ask for, ignored the air-gapped constraint). |
| **1** | Failed. Phase 1 produced no usable specs (refused, gibberish, wrote to the wrong path, never called `write`), OR phase 2 never ran / crashed before any code was written, OR the orchestrator looped without progress until the timeout. Includes runs where the chat trajectory shows the model confused about its own tools (calling tools that don't exist, malformed tool args repeatedly). |

## Rules for the rationale

- **Cite specific evidence.** Quote chat turns by their index, name files by path, point to elements visible (or absent) in the screenshot. "Phase 1 turn 4 wrote `proposal.md` but skipped `tasks.md` — the build skill needs all three." "Screenshot shows the search bar and recipe list but no rating stars, which the transcript explicitly required."
- **One short paragraph (3–6 sentences).** Walk the key inflection points across the pipeline.
- If the score is 5, name the move that was particularly clean (recovering from a port collision, vendoring chart.js correctly, schema/seed consistency held). 5 is rare — reserve for runs you'd point to as exemplary end-to-end behaviour.
- If the score is ≤ 2, name the specific failure mode in the pipeline's own terms (looped on `sessions_spawn` / wrote specs to wrong path / coder hand-rolled qrcode.js / container crashlooped on column drift).

## Important

- **You are scoring the ecosystem with this model, not the model in isolation.** A model that produces beautiful prose but cannot wield the `prototypes.build` + `sessions_spawn` tool chain is a weak ecosystem result, not a strong reasoning result. Conversely, a model whose individual chat turns are terse but whose pipeline lands a working app is a strong ecosystem result.
- **The screenshot is ground truth, not a summary.** If the orchestrator's final message says "prototype live at port 9047" and the screenshot is a 502, that's a 2 (or worse), regardless of how confident the chat sounded.
- **Partial artifacts are informative, not disqualifying.** A run with great specs but no screenshot is not automatically a 1 — it might be a 3 if those specs would clearly produce a good prototype. Use the rationale to call out which phase carried the run and which phase let it down.
- **Do not penalise the candidate for things outside its control.** If `build-status.json` shows `port: null` because the seeder service was unreachable for infrastructure reasons (and the chat trajectory shows the model handled that gracefully), score on what the model did, not on the infra failure.
- **Do not reward verbosity.** Long orchestrator monologues about what it's about to do, repeated re-statements of the plan, or excessive hedging during the build are deductions, not bonuses. Captain Nemo is meant to be terse.
- **Tie goes to the lower score** when between two anchors. The harness exists to discriminate.

Submit your score and rationale via the `submit_grade` tool. Do not write any prose outside the tool call.

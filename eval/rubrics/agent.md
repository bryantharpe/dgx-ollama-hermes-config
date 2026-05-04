# Agent-loop scoring rubric — multi-turn trajectory

You are grading **the entire trajectory of a candidate model in a multi-turn agent scenario**. The trajectory you receive contains:

1. The original user task.
2. The list of tools the model had available, with their schemas.
3. The full back-and-forth: every assistant message, every `tool_use`, every (faked) `tool_result`, in order.
4. The "goal state" the harness was looking for (what it considered "done correctly").

Score the trajectory as a whole on the anchored 1–5 scale below. Cite specific turns by their index when justifying.

## Dimensions to consider (jointly, not separately)

- **Tool selection** — Did the model pick the right tool for each step? Did it avoid unnecessary tools?
- **Argument quality** — Were the arguments well-formed for each call? Right field names, right types, right values inferred from prior turns?
- **Use of tool results** — Did the model actually *use* the result of each tool call to inform the next step, or did it ignore prior outputs and barrel ahead?
- **Error recovery** — When a tool returned an error or unexpected result, did the model adapt, or did it retry the same broken call?
- **Convergence** — Did the trajectory reach the goal state? Did it do so in roughly the expected number of turns, or did it stall, loop, or quit early?
- **Final answer** — Was the final natural-language response to the user a faithful summary of what was done, with the right answer?

These dimensions are *all relevant* — but you are giving a single integer score. Weight by what mattered most in this trajectory.

## Scoring anchors (use exactly one)

| Score | Anchor |
|---|---|
| **5** | Optimal. Right tools, right arguments, right order. Used every tool result to inform the next call. Reached goal state cleanly. Final answer is correct and well-summarised. |
| **4** | Good. Reached goal state. At most one inefficiency (one redundant call, one off-by-one in arguments that didn't matter, slight over-explanation in the final response). |
| **3** | Acceptable. Reached goal state but with notable friction: a wrong-tool detour the model recovered from, sloppy argument values, or a final response that omits a key result. |
| **2** | Weak. Did not reach goal state, OR reached it through luck (e.g. user info was conveniently in the very first tool result by accident). Multiple wrong arguments, repeated identical broken calls, or final answer is wrong. |
| **1** | Failed. Got lost, looped on the same broken tool call until the turn limit, refused a benign agentic task, or produced no final response. Includes trajectories that crashed because the model emitted invalid tool-call JSON. |

## Rules for the rationale

- **Reference specific turn indices.** "On turn 3 the model called `get_user` with `user_id='alice'` instead of the integer ID `7` returned on turn 2."
- **One short paragraph (3–6 sentences).** Walk the key choice points.
- If the score is 5, name the move that was particularly clean (it is rare; reserve it for trajectories you'd cite as exemplary).
- If the score is ≤ 2, name the failure mode in the trajectory's own terms (looped on X / used wrong tool / never read the result of Y).

## Important

- **Tool results were faked by the harness.** Do not score the realism of tool outputs; score how the model *used* the (possibly weird) outputs it received.
- **Number of turns is not strictly more = worse.** A 12-turn trajectory that genuinely needed 12 turns is fine. A 3-turn trajectory that skipped a required check by guessing is not.
- **A trajectory that produced an unhelpful but technically-correct final answer is ≤ 3.** OpenClaw users care about useful answers, not pedantic ones.
- **Tie goes to the lower score** when you are between two anchors.

Submit your score and rationale via the `submit_grade` tool. Do not write any prose outside the tool call.

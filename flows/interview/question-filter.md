# Filter questions

For each unresolved choice:

1. **Discoverable fact:** investigate it. Dependent decisions wait for evidence;
   independent work continues.
2. **Reversible engineering choice within the mandate:** decide using the simplest
   adequate existing mechanism. Record a material assumption and what would
   invalidate it; routine helper placement needs no interview or ledger ceremony.
3. **Material fork:** ask only if plausible answers change the goal, accepted
   behavior, compatibility, scope, cost/resource boundary, an irreversible action,
   or a user-reserved choice. State the consequence and your recommendation.
   Missing context matters only when it changes such a decision.

After filtering the questions above, run the configured
[`mandate` checkpoint](../../runtime/decisions/checkpoint-command.md)
before choosing among permitted investigate/decide/ask actions. Record an evidenced
skip when the next step is settled or reserved to the user; user-reserved choices
remain human. Check this phase record before leaving mandate.

Reuse accepted priorities and ask for the highest unresolved goal, principle or
constraint that settles related forks together. Ask what may change before asking
how to implement it. Defer questions whose answer depends on that unresolved
choice, even when their technical alternatives are already known.

Compose the user-facing round in this order:

1. State the goal and material uncertainty in one or two sentences; keep the
   user's scope intact.
2. Ask the highest unresolved boundary in the user's terms: what may be removed
   or what must keep working. Usually ask one question; at most two independent
   choices, including subquestions and trailing approval asks. Defer questions
   that depend on an unanswered scope choice.
3. Give one recommendation and its main evidenced consequence. The user should
   be able to answer from their priorities without learning implementation details.
   Use only terms the user introduced or defined in the same sentence. Internal
   names such as components, readers, modes or ticket IDs fail this check.

End the question round after those three parts. Review the entire visible reply,
including tables, headings and trailing notes; a concise question inside a full
plan does not pass. Save the remaining investigation and ledger work internally.

For example: "Must existing behavior stay compatible, or may we change it if
measurements show that is necessary? I recommend preserving it while we
investigate." Keep consumer
classification, release strategies, mechanisms and checkpoint metadata internal.
Investigate usage; unknown consumers do not waive a public contract. A possible
agreement breach always needs a human ruling or an applicable existing user
condition before dependent work. Preserve callers while comparing compatible
options; ask about changing them only when that decision becomes necessary.

Before sending, check the entire reply against this shape and its evidence.
Keep every material source of the user's problem in the opening; a question about
one source must not silently narrow the goal to that source.
A measured size category is not an attainable saving; do not promise its recovery,
call an API change the only route or rule out compatible options without comparison.
If the draft fails, revise it before asking the user; repeated failure enters the
existing recovery/review path. Keep required calibration warnings to one brief
line when first surfaced, separate from the question.

Keep the remaining design tree internal. Surface another decision only when the
answer or new evidence makes it necessary; explain details on request. Record
material agent choices and unresolved risks, and pause work that depends on an
unanswered user decision. Stop interviewing when the next authorized work has a
sufficient mandate. A broad "looks good" cannot select between incompatible open
options: clarify the selection while continuing independent work.

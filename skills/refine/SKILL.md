---
name: refine
description: "Split an accepted alignment brief into scoped tickets in the project's tracker, or local Markdown."
disable-model-invocation: true
argument-hint: "<effort-slug> — an existing alignment brief"
---

# Shared refinement procedure

Contents:
- [Process](#process)
- [Definition of Ready](#definition-of-ready)
- [Then](#then)
- [Explicit phase composition](#explicit-phase-composition)
- [Local Markdown ticket template](ticket-template.md)

First read: the runtime bootstrap (`../../bootstrap.md`), the host session part.

The same procedure supports explicitly requested research-to-refinement composition
where the runtime permits it; it does not enable implicit skill invocation.

Used by the explicit refinement skill or an explicitly requested refinement phase
inside a composed task (for example, research followed by refinement). Dispatch
also uses it to split already-selected work into executable tickets, preserving
the parent's scope and outstanding outcomes. Load the runtime bootstrap and selected
adapter first. Record the initiating request; do not infer unrelated planning work
from ordinary research or implementation requests.
This is a workflow convention, not a native permission bypass. If the runtime
requires a separate user invocation or denies the operation, stop that action,
retain the prepared input and explain the native restriction. Never retry a
refused operation through this reference. Tracker publication still follows the
existing task authorization and project conventions.

Matt Pocock's `/mattpocock-skills:to-tickets` breaks a spec into **tracer-bullet** tickets with
**blocking edges**; its slicing rules (vertical slices, prefactors first, wide
refactors as expand → migrate → contract) apply here unchanged and are not
restated. `/automattic:refine` adds what a scrum backlog needs — a **user story** and
**acceptance criteria** per ticket, a size that fits one fresh context window — and
uses the project's ticket convention. For local Markdown only, it writes the
front matter the local scheduler reads. Input: `.scratch/<slug>/alignment.md`,
or `spec.md` and prose tickets from Matt's `/mattpocock-skills:to-spec` and `/mattpocock-skills:to-tickets`, which it
adapts to the project's ticket convention. Create or update canonical work items
in the configured tracker under the shared bootstrap's project-conventions rules.
Output: canonical issue IDs/URLs for a remote tracker; otherwise local tickets
under `.scratch/<slug>/issues/NN-<title>.md`, numbered in dependency order.
Remote dispatch consumes those issues directly under [board operations](../../flows/board/board.md);
do not create local issue files or require local front matter for remote tickets.

Two of `/mattpocock-skills:to-tickets`' steps change under the dispatch loop:

- Its integration branch for batches that cannot stay green alone is the spec
  branch `feat/<slug>`, and its integrate-and-verify ticket is the spec E2E; write
  the batches as ordinary tickets in a chain.
- Its step 4 quiz becomes a ledger brief (step 6 below).

## Process

1. **Read the brief and existing project instructions.** `alignment.md` supplies
   the goal, boundaries and observable outcomes the criteria assert. Resolve areas,
   hot files and verification from [project execution facts](../../flows/board/project-loop.md).
   Reuse established areas; when missing, name them from modules/shared resources
   and record them in the effort alignment for dispatch. Tickets using the same
   exclusive GPU, serving lane or mutable fixture must share a reservation even
   when their files differ; account for that
   resource during implementation, not only E2E. `CONTEXT.md` for the words. Read the
   configured tracker and relevant existing issues; preserve their destination,
   identity, scope and priority.
   Record the effort's intended branch base and any unmerged prerequisites before
   committing the plan or claiming it is independently deliverable. Reuse the
   project's branch convention; preserve an existing branch's work.
2. **Slice** as `/mattpocock-skills:to-tickets` prescribes; each slice sized for one context window.
   Weigh handoff cost when adjacent outcomes share the same small implementation,
   fixtures and verification. Keep them together when they form one coherent slice;
   split where independent delivery, risk, dependencies or context size earns the
   extra worker setup and integration. Individual settings or acceptance criteria
   need not each become a ticket. Preserve existing issue identities and scope.
   For optimization or operational experiments, distinguish research hypotheses
   from measurements on the actual targets. When local applicability or benefit
   decides the implementation, put a baseline using existing tools before the
   dependent automation, then a representative trial before wider application.
   Define the metric, comparable workload conditions and success criterion;
   retain a supported no-change outcome when the proposed optimization adds no value.
   Evidence from another environment suggests what to investigate, not what to build.
   Separate the experiment that decides value from downstream operational automation.
   When that result can make later work unnecessary, give the later work a blocking
   edge and retain it as deferred scope until the result is accepted.
   Before adopting the split/grouping, run the configured
   [`refinement` checkpoint](../../runtime/decisions/checkpoint.md#configured-checkpoint-command)
   with viable cuts and their evidence, or an evidenced skip for settled cuts.
   Check this phase record before declaring the breakdown ready.
3. **Draw the edges.** Preserve native blocking relationships and issue IDs in a
   remote tracker; use `blocked_by` local IDs for local Markdown. An unresolved
   external prerequisite stays blocked; never drop it because it is outside the
   selected queue.
   An edge the brief settles is a fact; one it does not settle is a ledger row with
   a hinge, appended to `.scratch/<slug>/ledger.md`.
4. **Prepare each ticket** using the project's issue template, or the local-only
   [template](ticket-template.md). Reuse an existing matching issue rather than duplicating it.
   The story is one sentence from the
   actor's side. Each criterion is an observable outcome, Given/When/Then, with a
   `Verify` line naming the command or the test that proves it and who can observe
   it: `code`, `agent` or `user`. Name behaviours and commands, never files or code.
   Checks only the user can observe go to the user together, in one request, once an
   integrated build allows them. Replacing a `Verify` method with a weaker one is the
   user's decision, not an amendment an agent makes.
   Ask whether that check could pass while the criterion is broken. If so, choose
   a check that reaches the promised behavior and relevant execution context;
   distinguish partial evidence from the remaining verification. Keep unavailable
   required checks explicit without turning out-of-scope production operations
   into new prerequisites.
   Check whether normal variation can swamp the asserted difference or make a
   correct implementation fail. Use existing baseline observations; replace an
   unstable measurement with a discriminating invariant or a justified tolerance
   within the accepted contract. Resolve this for every criterion in the same
   refinement pass, before claiming the ticket is ready. Correcting its measurement
   needs no new approval when already authorized; changed behavior or priorities do.
   Verify that named commands and their configured inputs still apply in the target
   environment. For migrations or conversions, separate metadata compatibility,
   representative target-value checks and actual target execution. Reference-only
   checks cannot establish target behavior; label sampled evidence as sampled.
   A readiness handoff names the next consumer's real inputs and one bounded path
   through them in the authorized environment. Stub/unit checks remain useful
   evidence; an unavailable real-input check leaves that readiness claim open.
   Before a long run, state input counts, workload units (e.g. steps versus epochs),
   batch/drop policy, estimated resources and duration, and any agreed checkpoint
   or stop condition. Derive workload conversions from the actual inputs and runner.
   For runner deliverables, state whether the ticket delivers a scaffold or the
   complete downstream procedure. List the promised stages and use the shared
   [runner contract checks](../../runtime/resources/resources.md#runner-contract-checks).
5. **Execution inputs.** Determine areas, devices and workload from the project
   conventions; pass them with the issue context to dispatch. Do not require new
   tracker fields or labels. For local Markdown, encode them as front matter:
   `touches` from the resolved areas; `devices` only when
   the applicable E2E step boots one; `model: standard` by default, `model: deep`
   when the ticket edits an identified hot file. These are workload labels only; executor
   configuration owns model/thinking selection. `blocked_by: []` when nothing gates it — the key is
   always present on local tickets. Record blockers using the chosen board's
   conventions when an external prerequisite cannot yet be verified. Cross-effort edges wait for the entire prerequisite effort
   to finish and merge into main; put work that must integrate before that in
   the same effort. Ticket cycles and cycles between efforts are invalid.
6. **Present a compact breakdown:** each ticket's outcome, dependency and decisive
   verification, plus material slicing tradeoffs and consequential ledger rows.
   Explain a rejected cut only when it was a viable alternative with a different
   outcome, risk or verification cost. Apply the [question filter](../../flows/interview/question-filter.md); routine
   cuts within accepted scope need no additional interview.
   Carry forward existing authorization; obtain any still-required scope or
   publication decision for the concrete breakdown. An unrelated reply or silence
   is not approval. Apply authorized changes to the selected board; do not claim
   a failed remote write succeeded. Validate the resulting issue graph and return
   canonical IDs/URLs. Only for local Markdown, write the files and run
   `python3 "<plugin_root>/scripts/next_tickets.py" --repo "<repo>" <slug> --check`.

## Definition of Ready

A builder with an empty context can build the ticket using its story,
criteria with verifying commands/tests, dependency edges, accepted brief and
applicable project instructions, with `CONTEXT.md` for vocabulary. The assignment
fits one context window. Before reporting readiness, reconcile all
criteria with their discriminating signal, preconditions and known variation;
surface the complete remaining gaps in one summary. State spec readiness separately
from scheduling readiness: a complete spec can still wait on a dependency. Use
the tracker's existing conventions for those states. A ticket that still needs a
material question answered is not spec-ready; apply the same question filter.

## Then

`/automattic:dispatch` schedules the tickets on `blocked_by` and `touches`; its builders
follow the ticket job, using `alignment.md`
as the spec.

## Explicit phase composition

When the user explicitly requests refinement after another task, such as research,
use the shared refinement procedure once its input
is ready, where the active runtime permits direct procedure loading. Do not call
an explicit-only skill through a forbidden tool or infer refinement from research
alone. Preserve native invocation policy: if a separate user invocation is required
or the operation is denied, retain the input and explain that restriction; do not
route around it. Dispatch's automatic review remains its own documented handoff.

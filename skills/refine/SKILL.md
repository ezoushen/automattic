---
name: refine
description: "Split an accepted alignment brief, or a plan agreed in chat, into scoped tickets in the project's tracker, or local Markdown."
disable-model-invocation: true
argument-hint: "<effort-slug> | the plan agreed in this conversation"
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
inside a composed task (for example, research followed by refinement). Dispatch's
split step cuts already-selected work by the same slicing rules, preserving the
parent's scope and outstanding outcomes. Load the runtime bootstrap and selected
adapter first. Record the initiating request; do not infer unrelated planning work
from ordinary research or implementation requests.
This is a workflow convention, not a native permission bypass. If the runtime
requires a separate user invocation or denies the operation, stop that action,
retain the prepared input and explain the native restriction. Never retry a
refused operation through this reference. Tracker publication still follows the
existing task authorization and project conventions.

`/automattic:refine` cuts work into tickets by the board's [slicing rules](../../runtime/board/slicing.md):
thin end-to-end slices with **blocking edges**, each sized for one fresh context window.
It adds what a scrum backlog needs — a **user story** and **acceptance criteria** per
ticket — and uses the project's ticket convention. For local Markdown only, it writes the
front matter the local scheduler reads. Input: `.scratch/<slug>/alignment.md` or
[a plan agreed in chat](chat-plan.md). Create or update canonical work items
in the configured tracker under the shared bootstrap's project-conventions rules.
Output: canonical issue IDs/URLs for a remote tracker; otherwise local tickets
under `.scratch/<slug>/issues/NN-<title>.md`, numbered in dependency order.
Remote dispatch consumes those issues directly under [board operations](../../runtime/board/board.md);
do not create local issue files or require local front matter for remote tickets.

## Process

1. **Read the brief and existing project instructions.** `alignment.md` supplies
   the goal, boundaries and observable outcomes the criteria assert. Resolve areas,
   hot files and verification from [project execution facts](../../runtime/board/project-loop.md).
   Reuse established areas; when missing, name them from modules/shared resources
   and record them in the effort alignment for dispatch. The project's [glossary](../../runtime/domain/glossary.md) for the words. Read the
   configured tracker and relevant existing issues; preserve their destination,
   identity, scope and priority.
   Record the effort's intended branch base and any unmerged prerequisites before
   committing the plan or claiming it is independently deliverable. Reuse the
   project's branch convention; preserve an existing branch's work.
2. **Slice** by the [slicing rules](../../runtime/board/slicing.md). Preserve existing
   issue identities and scope. Before adopting the split/grouping, run the configured
   [`refinement` checkpoint](../../runtime/decisions/checkpoint-command.md)
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
   [runner contract checks](../../runtime/resources/resources.md).
5. **Execution inputs.** Determine areas, devices and workload from the project
   conventions; pass them with the issue context to dispatch. Do not require new
   tracker fields or labels. For local Markdown, encode them as front matter:
   `touches` from the resolved areas; `devices` only when
   the applicable E2E step boots one; `model: standard` by default, `model: deep`
   when the ticket edits an identified hot file. These are workload labels only; executor
   configuration owns model/thinking selection. `blocked_by: []` when nothing gates it — the key is
   always present on local tickets. Record blockers using the chosen board's
   conventions when an external prerequisite cannot yet be verified.
6. **Present a compact breakdown:** each ticket's outcome, dependency and decisive
   verification, plus material slicing tradeoffs and consequential ledger rows.
   Explain a rejected cut only when it was a viable alternative with a different
   outcome, risk or verification cost. Apply the [question filter](../../runtime/interview/question-filter.md); routine
   cuts within accepted scope need no additional interview. Newly cut tickets wait for
   the user's check before any implementation.
   Carry forward existing authorization; obtain any still-required scope or
   publication decision for the concrete breakdown. An unrelated reply or silence
   is not approval. Apply authorized changes to the selected board; do not claim
   a failed remote write succeeded. Validate the resulting issue graph and return
   canonical IDs/URLs. Only for local Markdown, write the files and run
   `python3 "<plugin_root>/scripts/next_tickets.py" --repo "<repo>" <slug> --check`.

## Definition of Ready

A builder with an empty context can build the ticket using its story,
criteria with verifying commands/tests, dependency edges, accepted brief and
applicable project instructions, with the glossary for vocabulary. The assignment
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

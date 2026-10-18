# Test-effectiveness routing

`classify-test` routes one added or modified test for the
[tautological-tests](../../skills/remediate/kinds/tautological-tests.md) check. The
reviewing agent writes the checklist as JSON and runs:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py classify-test \
  --repo <canonical-project> --input <absolute-checklist.json> \
  --journal <absolute-session-decisions.jsonl> --assignment-id <review/head/test-n>
```

```json
{"family": "test-shape",
 "claim": "One sentence: the behavior this test protects.",
 "test": "The test body and the helpers it calls, comments removed.",
 "code": "The functions it calls directly, comments removed.",
 "assertions": [{"lines": "12", "checks": "retire exits 2",
   "expected_source": "literal", "can_run": "yes", "failure_expected": "yes",
   "failure_reason_checked": "type-or-code-only", "comparison": "exact",
   "same_result_without_rule": "other-rule", "about_claimed_result": "yes"}]}
```

Every field is required. `expected_source` is `literal`, `worked-example`,
`code-under-test`, `mock-config`, `fixture-or-file`, `earlier-output` or `none`;
`can_run` and `failure_expected` and `about_claimed_result` are `yes` or `no`;
`failure_reason_checked` is `message`, `type-or-code-only` or `n/a`. `message` means
the test checks text, a distinctive code or an exception class only the claimed rule
produces. `failure_expected` is `yes` for any rejection the test expects: an error, an
exit code, a refusal result, or a fallback or degraded state.
`comparison` is how the assertion compares: `exact` (the whole value or collection),
`partial` (contains, a subset, some fields, or `all`/`any` over a list that may be
empty), `bound` (at least, at most, non-empty, not null or type only) or `n/a` (nothing
compared). `same_result_without_rule` is what this assertion sees if the claimed rule is
removed: `no` (its result changes), `default` (the default or initial state gives the
same result), `other-rule` (another check or path gives the same result) or `unknown`.
Answer it from the code, not from the test's name. An optional `context` (at most 6,000
characters) carries code collected for a second round. Limits: claim 600 characters,
test and code 6,000 each, 1–40 assertions with fields of at most 300 characters, and a
composed request of at most 16,000. Remove comments and
documentation blocks first, in whatever syntax the language uses. Invalid input exits 2
without inference or a journal record.

Results, by `route`:

- `trace`: an expected failure is checked only by code or type. Another rule may satisfy
  it, and only a code trace decides that, so no model is called. `expectations` lists
  the lines to trace. Measured: the model separated these no better than chance.
- `flagged` with `source: checklist`: every assertion about the claimed result sees the
  same result without the rule (`default` or `other-rule`). No model is called; `lines`
  lists them for the re-read.
- `protected`: both option orders chose `independent-check` and its averaged probability
  is at least 0.8, and some assertion about the claimed result compares a value
  (`comparison` is not `n/a`) that the rule changes (`same_result_without_rule` is
  `no`); otherwise the route is `escalate`. It clears a test only when the agent's
  checklist raised no doubt; a test the agent already suspects is re-read.
- `flagged`: both orders chose a hollow shape (they may name different ones; `pass_shapes`
  lists both, `shape` the averaged top choice) and the hollow shapes' averaged probability,
  excluding abstention, is at least 0.8. The question that routes is protected versus
  hollow; the threshold was measured on that quantity.
- `escalate`: anything else, including an abstention in either order, a backend failure
  or a disabled `test-shape` family. A flagged test is not resubmitted; only an
  escalation gets a second round. Collect what the answer lacked once, as `context`:
  the code of the default path, of other checks that could give the same result, and of
  helpers the test calls. Resubmit under the same assignment ID with `/round-2` appended.
  When nothing new can be collected, or round 2 escalates again, the agent re-reads the
  cited lines and decides.

The model chooses among `independent-check`, `derived-from-code`, `mock-echo`,
`assertion-never-runs`, `checks-other-behaviour`, `partial-check`,
`accepts-any-failure` and `same-as-default`, or abstains. Its answer routes work, so unlike the shadow
families it is returned. It is journaled as before and a rerun of the same assignment
reuses it. Record the established label with the
[`assessment` command](shadow-pilots.md#failure-cause-shadow-pilot):
`independent` for another reviewer's reading, `host` for your own.
These keep measuring the 0.8 threshold.

# Builders work test-first from our own standard, and tests protect business rules

Every builder works test-first from the [TDD standard](../../standards/tdd.md): one failing test seen to fail,
then only enough code to pass it, one rule at a time. Each test names the business rule it protects, takes its
expected value from an independent source and is shown to fail when that rule is deliberately broken; coverage means
every rule and acceptance criterion has such a test, not a line-coverage figure. We chose this over Matt Pocock's tdd
skill, which the framework depended on, because the user asked for tests free of tautologies and judged by their
effectiveness and their coverage of business logic; that skill named tautological tests as an anti-pattern but
required neither a named rule per test nor a run showing each test fail on a broken rule.

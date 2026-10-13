# Research basis

The skill synthesizes content and maintenance principles across these primary
sources. It does not impose one language's formatting rules on another.

| Source | Principle carried into the skill |
|---|---|
| [Google C++ Style Guide: comments](https://google.github.io/styleguide/cppguide.html#Comments) | Separate interface usage from implementation reasoning; describe relevant ownership, synchronization and invariants; private functions can need documentation too. |
| [PEP 257: docstring conventions](https://peps.python.org/pep-0257/) | Summarize behavior and relevant arguments, results, side effects, exceptions and calling restrictions. A repeated signature is not a useful behavioral explanation. |
| [Rust API Guidelines: documentation](https://rust-lang.github.io/api-guidelines/documentation.html) | Document failure conditions and caller safety obligations; make examples meaningful, realistic and connected through references instead of repeating them everywhere. |
| [Go: doc comments](https://go.dev/doc/comment) | Function docs explain caller-visible behavior and relevant special cases, not the current algorithm. Relevant complexity bounds can belong in the contract. Formatting, references and deprecation notices have tool-recognized semantics. |
| [Google engineering practices: comments](https://google.github.io/eng-practices/review/reviewer/looking-for.html#comments) | Inline comments add reasoning unavailable in code; API documentation explains purpose and use. Explain an opaque algorithm's idea when helpful, without narrating its statements. |
| [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/) | Start with a clear responsibility/result summary; additional discussion is optional. Document surprising cost where callers need it. The specific Swift rule for nonconstant computed properties is not a universal requirement to put Big-O on every function. |

The sources differ on sentence form, symbol coverage and examples: PEP 257 favors
imperative summaries; Google's C++ guide uses descriptive verb phrases; Go commonly
starts with the declared name. Rust's example conventions are not a universal
requirement to add an example to every symbol. Keep those choices with the project's
language and tooling. "Explain why" is useful for implementation comments, but is
insufficient for API documentation, which must communicate usable contracts.

Automattic's mandatory documentation review gate, scoped follow-ups, prohibition on
working-journal comments (including ADR/ticket references), and rule against
weakening docs to excuse bugs come from the user's explicit requirements.
Implementation history and ADR/ticket references belong in Git commit messages;
source comments retain the durable technical explanation. These rules
are project policy, not a claim that these sources prohibit all tracking references
or define a universal gate. Preserve semantic annotations such as deprecation
notices; they communicate the API's supported use, not an implementation diary.

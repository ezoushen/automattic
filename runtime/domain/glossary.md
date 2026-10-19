# Glossary

The repository's ubiquitous language, shared by its members and agents. Grilling
writes terms as they settle, builders keep it current, review checks the words a
change uses, and explanations speak it.

## Where it lives

A single bounded context keeps one `GLOSSARY.md` at the repository root. With
several contexts, a `GLOSSARY-MAP.md` at the root lists the contexts, where each
glossary lives and how the contexts relate, and each context keeps its own
`GLOSSARY.md` beside its code. Read the map first when it exists; when the topic's
context is unclear, ask. Create it lazily, when the first term settles.

A project's existing glossary convention wins, under its own name and location;
neither file is required.

## Format

```md
# {Context name}

{One or two sentences: what this context is and why it exists.}

## Language

**Order**:
A customer's request for goods, from placement until delivery or cancellation.
_Avoid_: purchase, transaction
```

- Each term gets one or two sentences saying what the term is, not what it does.
- When several words name one concept, pick one and list the rest under `_Avoid_:`.
- Only terms specific to this domain: general programming concepts stay out, even
  when the project uses them heavily, and the glossary holds no implementation detail.
- Group terms under subheadings when natural clusters appear.

## Keep it current

- Grilling and design: update it the moment a term settles, never in a batch. Call out
  a term the user uses against its definition and propose one canonical word for a
  fuzzy or overloaded one.
- Building: a change that introduces or changes a domain term updates the glossary
  in the same commit, and uses its terms in names, docs, tests and messages.
- Review: a term used against its definition, or an `_Avoid_` word, in what a change
  adds is a Standards finding, cited with the glossary line.
- Explaining and asking: use its terms and avoid its `_Avoid_` words.

# Explain

How to explain something so the user follows it: a re-pitch when they are lost, and the
smallest view that shows a shape. Briefings, walkthroughs, the setup tour and `huh` use it.

Contents:
- [Re-pitch what lost the reader](#re-pitch-what-lost-the-reader)
- [Choose the smallest view](#choose-the-smallest-view)
- [Keep to the caller's scope](#keep-to-the-callers-scope)

## Re-pitch what lost the reader

A user who says they are lost is reporting their state, not asking for fewer words.
Clipping the same message loses them further.

1. Find where they lost it: usually the first premise, term or step they could not have
   known, which can be earlier than the last message.
2. Restart there. Give the missing context first, in one or two sentences: the problem,
   the earlier decision or the fact the point depends on.
3. Then give the point, in plain sentences, the way one person explains it to another.
   One term per concept, with the user's own words and the project's own names.
4. Define an internal name, such as a component, mode or file, where it first appears,
   or leave it out. Never use a ticket or decision ID in place of what it stands for.
5. Add a view below only when the shape is what confuses them.

Keep the re-pitch no longer than the message it replaces: pay for the added context by
dropping detail the point does not need, not by clipping sentences. A view replaces the
prose for the same steps; never say them twice. Asked twice, go further back rather than
further down.

## Choose the smallest view

Pick one view that makes the point, put it next to the sentence it supports, and keep
only the steps, files, states and boundaries the question needs. Several views are
sometimes right; all of them never are.

- **Steps or a rule:** short pseudocode.

  ```text
  on retry
    if the attempt changed nothing
      stop and report the blocker
    otherwise start the next attempt
  ```

- **Who calls whom at run time:** an indented call tree.

  ```text
  dispatch
    select ticket
    launch worker
      wait for return
    accept and merge
  ```

- **How a screen is built:** a component tree, with the state and module boundaries
  that matter.

  ```text
  SessionPage           owns the session state
    Toolbar
      RunButton         from the shared UI package
    Timeline
  ```

- **What lives where:** a shallow file tree with one comment per entry.

  ```text
  skills/     commands the user types
  runtime/    shared rules the commands read
  hooks/      checks the host runs on events
  ```

- **Order between parties:** a sequence as text arrows (`user -> host: request`), one
  line per message.
- **What changes:** a `diff` of the same shape (call tree, component tree, file tree,
  steps or a block), so unchanged lines give the context. Show the whole block instead
  when most of it is new, when leaving lines out would hide ownership or order, or when
  the user needs a copyable target.
- **A layout, a comparison of states, or a picture too dense for text:** a short table,
  or, when the user asks for a file, one focused page: a diagram, an infographic or a
  short deck. Match the product's colors, type, spacing and components, use real labels
  and data, support desktop and mobile, and open it through the host's preview when it
  has one.

Draw with text pictures by default: they read the same in every terminal. Use a rendered
diagram format only where the reader's surface renders it, such as a PR body or a
Markdown page, and confirm it renders there.

## Keep to the caller's scope

The calling procedure decides what is in scope. An explanation stays in the
conversation; create or export a file only when the user asks. Explaining runs no
investigation of its own: re-read facts already established, and mark a claim you have
not checked as unchecked.

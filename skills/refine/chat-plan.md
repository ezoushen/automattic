# Start from a plan agreed in chat

Read by [refinement](SKILL.md) and dispatch when the user says the plan agreed in the
conversation is ready and no `alignment.md` exists for it.

1. Take the user's slug, or a short one from the goal, and write `.scratch/<slug>/alignment.md`
   in the alignment brief's sections: the Mandate with the user's words quoted verbatim
   (goal, principles, constraints and the statement that the plan is ready); the plan as
   agreed as WHAT and HOW, with the acceptance evidence discussed; WHY in a sentence; open
   questions. Start `ledger.md` with the decisions the conversation settled, the user's
   apart from the agent's.
2. Do not run align or re-ask what the conversation settled. Apply the
   [question filter](../../runtime/interview/question-filter.md) and ask only a material gap
   that blocks executable tickets, such as an outcome no check can observe.
3. Cut the tickets with the refinement procedure, then show the list and wait for the
   user's check. From dispatch, that approval continues this dispatch into its iteration;
   a change request re-cuts first.

`/automattic:align` stays available for a plan that needs it: unsettled goals, competing
designs or a contract change the conversation did not decide.

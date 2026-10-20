# Builders refactor after green, within the ticket

Once a test passes, the builder refactors the ticket's own code within the ticket's scope, keeping the tests green;
a wider refactor goes to review. We chose this over Matt Pocock's rule that refactoring is not part of the loop and
belongs only to review, at the user's choice: the builder still has the code and its tests in hand, and the
ticket's scope bounds what the refactor may touch.

# Autopilot merges only through the repository's normal path

Autopilot stops once the PR is open, and merges only when the user adds `--auto-merge`. Even then it merges only after the required checks and the repository's approval path are satisfied, never by an admin override or by approving its own PR; a missing approval ends the run waiting on the user. We chose this over letting a hands-off run merge on its own judgment, because nothing a human reviews would then stand between the planning answers and `main`.

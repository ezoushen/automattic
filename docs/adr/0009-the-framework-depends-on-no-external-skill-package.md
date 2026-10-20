# The framework depends on no external skill package

The framework depends on no external skill package: its manifests declare no skill dependency, and its procedures,
standards and jobs are its own, under its own names. A repository-wide test rejects the package's name and its
distinctive skill names outside the journals, the ADR folder and the test itself; the former dependency was Matt
Pocock's skills. We chose this over keeping that package as
a dependency, because the user wanted the framework free of any existing framework, keeping only the parts they
want, and because with the package disabled the whole plugin failed to load.

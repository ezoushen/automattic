# The framework depends on no external skill package

The framework depends on no external skill package: its manifests declare no skill dependency, and its procedures,
standards and jobs are its own, under its own names. A repository-wide test rejects any mention of the former
dependency, Matt Pocock's skills, outside the journals and these ADRs. We chose this over keeping that package as
a dependency, because the user wanted the framework free of any existing framework, keeping only the parts they
want, and because with the package disabled the whole plugin failed to load.

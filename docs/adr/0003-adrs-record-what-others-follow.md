# An ADR records a decision others must follow, or one that passes the three tests

A decision gets an ADR when it shapes the structure, interfaces or dependencies others build on,
or sets a rule every later change must follow, or when it is hard to reverse, surprising without
context and a real trade-off; a bare rule with no trade-off is a line in the project's rules file
instead. We widened Matt Pocock's three-test gate because on its own it dropped team-wide rules that
are cheap to reverse but must still be followed, which Nygard, AWS, Microsoft and arc42 all count as
architecturally significant.

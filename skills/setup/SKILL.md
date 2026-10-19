---
name: setup
description: "Explain the current Automattic setup, or inspect, configure or reset worker models, routes, pools, routers, profiles, thinking bounds and decision opt-ins and calibration at user, project or session scope."
disable-model-invocation: true
argument-hint: "[question | show|set|reset [agent|router|decisions|profile|model-definition|runtime-definition|executor-definition] | calibrate | calibration status | retro <journal> | replay <journal> <cases>] [--scope user|project|session] [--route] [--config-profile <name>] [runtime=claude|codex|pi|opencode] [--candidate <id>] [thinking=<label|JSON>]"
---

# setup

First read: [runtime bootstrap](../../bootstrap.md), the host session part, [setup](../../flows/setup/setup.md).
Follow the [configuration procedure](../../flows/setup/setup.md) with the user's question or request.
No arguments, a question or a request to understand the setup takes the
[setup tour](../../flows/setup/tour.md) and stays read-only.

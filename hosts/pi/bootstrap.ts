import { execFileSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SECTION = "automattic_harness";

export default function (pi) {
  const root = resolve(dirname(realpathSync(fileURLToPath(import.meta.url))), "../..");
  pi.on("before_agent_start", (event) => {
    const herdr = process.env.HERDR_ENV === "1"
      ? ` Herdr environment detected: before delegation also read ${root}/hosts/herdr.md for routing, waits and cleanup.`
      : "";
    const hint = `Automattic harness: pi. When using an Automattic skill, first read ${root}/bootstrap.md and ${root}/hosts/pi/session.md. Plugin root: ${root}. Load only this host session part; pass its absolute path and the agent and job files to workers.${herdr}`;
    // Returning systemPrompt forces the prompt for this run only, so runs that
    // start without a typed prompt revert to the structured one and every switch
    // invalidates the server's prefix cache. A section is diffed by Pi instead.
    const sections = event.systemPromptOptions?.sections;
    if (sections) {
      sections[SECTION] = hint;
      return undefined;
    }
    return { systemPrompt: `${event.systemPrompt}\n\n${hint}` };
  });

  // Keep working while a lifecycle worker could finish without waking this host, or a worker this session
  // launched is unregistered: at most once per run, so a gap the host cannot fix never loops.
  let continued = false;
  pi.on("agent_settled", () => {
    continued = false;
  });
  pi.on("agent_before_settle", (event, ctx) => {
    if (continued || event.outcome !== "completed" || process.env.AUTOMATTIC_YIELD_HOOK === "off") return undefined;
    let missing;
    try {
      const session = ctx.sessionManager.getSessionId();
      const output = execFileSync("python3", [`${root}/hooks/yield_gate.py`, "check", ctx.cwd, session],
        { encoding: "utf8", timeout: 20000 });
      missing = JSON.parse(output).missing;
    } catch {
      return undefined;
    }
    if (!missing.length) return undefined;
    continued = true;
    const content = "These workers could finish or run without waking you:\n"
      + missing.map((gap) => `- ${gap}\n`).join("")
      + `Register each launched worker (${root}/runtime/workers/prepare.md). Arm a notified wait, recover the receipt `
      + "or collect the result (for a worker that is gone, a failed or cancelled result whose report says what was lost) "
      + `before stopping (${root}/runtime/workers/wait.md).`;
    return { entries: [{ type: "custom_message", customType: "automattic_yield_gate", content, display: true }], continue: true };
  });

  // Loop guard: a call that returned the same result three times in a row is blocked when repeated,
  // and a second blocked repeat stops the turn. Polling whose output changes is never blocked.
  const REPEATS = 3;
  let last = { call: "", output: "", streak: 0, blocked: 0 };
  const guarded = new Set();
  pi.on("tool_call", (event) => {
    if (process.env.AUTOMATTIC_LOOP_GUARD === "off") return undefined;
    const call = `${event.toolName}\u0000${JSON.stringify(event.input)}`;
    if (call !== last.call || last.streak < REPEATS) return undefined;
    last.blocked += 1;
    guarded.add(event.toolCallId);
    return {
      block: true,
      terminate: last.blocked > 1,
      reason: `This exact ${event.toolName} call returned the same result ${last.streak} times in a row. `
        + "Repeating it will not change anything: use the output you have, try a different approach, "
        + "or report that you are blocked and why.",
    };
  });
  pi.on("tool_result", (event) => {
    if (guarded.delete(event.toolCallId)) return undefined;
    const call = `${event.toolName}\u0000${JSON.stringify(event.input)}`;
    const output = JSON.stringify([event.content, event.isError]);
    last = call === last.call && output === last.output
      ? { ...last, streak: last.streak + 1 }
      : { call, output, streak: 1, blocked: 0 };
    return undefined;
  });

  // Log each Herdr agent launch for the yield gate, as the Bash PreToolUse hook does on Claude and Codex.
  // A failing tool_call handler blocks the tool, so logging catches everything and never blocks.
  pi.on("tool_call", (event, ctx) => {
    const command = event.input?.command;
    if (!["bash", "bg_run"].includes(event.toolName) || !/herdr[\s\S]*agent\s+start/.test(command)) return undefined;
    try {
      execFileSync("python3", [`${root}/hooks/herdr_launch.py`], {
        input: JSON.stringify({ tool_input: { command }, cwd: ctx.cwd, session_id: ctx.sessionManager.getSessionId() }),
        timeout: 10000,
      });
    } catch {
      // The launch goes unlogged; the stop check still lists live agents nobody registered.
    }
    return undefined;
  });
}

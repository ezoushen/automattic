import { execFileSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SECTION = "automattic_harness";

export default function (pi) {
  const root = resolve(dirname(realpathSync(fileURLToPath(import.meta.url))), "../..");
  pi.on("before_agent_start", (event) => {
    const herdr = process.env.HERDR_ENV === "1"
      ? ` Herdr environment detected: before delegation also read ${root}/harnesses/herdr.md for routing, waits and cleanup.`
      : "";
    const hint = `Automattic harness: pi. When using an Automattic skill, first read ${root}/harnesses/pi/adapter.md. Plugin root: ${root}. Load only this host adapter; pass its absolute path and the shared role file to workers.${herdr}`;
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

  // Keep working while a lifecycle worker could finish without waking this host:
  // at most once per run, so a gap the host cannot fix never loops.
  let continued = false;
  pi.on("agent_settled", () => {
    continued = false;
  });
  pi.on("agent_before_settle", (event, ctx) => {
    if (continued || event.outcome !== "completed" || process.env.AUTOMATTIC_YIELD_HOOK === "off") return undefined;
    let missing;
    try {
      const output = execFileSync("python3", [`${root}/hooks/yield-gate.py`, "check", ctx.cwd],
        { encoding: "utf8", timeout: 20000 });
      missing = JSON.parse(output).missing;
    } catch {
      return undefined;
    }
    if (!missing.length) return undefined;
    continued = true;
    const content = "These lifecycle workers could finish without waking you:\n"
      + missing.map((gap) => `- ${gap}\n`).join("")
      + "Arm a notified wait, recover the receipt or collect the result (for a worker that is gone, "
      + `a failed or cancelled result whose report says what was lost) before stopping (${root}/harnesses/worker-lifecycle.md).`;
    return { entries: [{ type: "custom_message", customType: "automattic_yield_gate", content, display: true }], continue: true };
  });
}

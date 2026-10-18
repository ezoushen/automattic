import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readdirSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// Use the installed SDK without loading the user's extensions or calling a model.
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(process.argv[2]).href);
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const temp = mkdtempSync(join(tmpdir(), "automattic pi "));
try {
  const agentDir = join(temp, "agent");
  const extensions = join(agentDir, "extensions");
  const skills = join(agentDir, "skills");
  mkdirSync(extensions, { recursive: true });
  mkdirSync(skills);
  symlinkSync(join(root, "hosts/pi/bootstrap.ts"), join(extensions, "automattic.ts"));
  const packageDir = join(temp, "package");
  const unselectedAddon = join(packageDir, "addons/unselected/skills/probe");
  mkdirSync(unselectedAddon, { recursive: true });
  writeFileSync(join(unselectedAddon, "SKILL.md"),
    "---\nname: unselected-addon-probe\ndescription: Optional addon discovery fixture\n---\nNever auto-load this addon.\n");
  symlinkSync(join(root, "skills"), join(packageDir, "skills"));
  symlinkSync(join(packageDir, "skills"), join(skills, "automattic"));
  const loader = new DefaultResourceLoader({
    cwd: temp, agentDir, settingsManager: SettingsManager.inMemory({}),
    noContextFiles: true, noPromptTemplates: true, noThemes: true,
  });
  for (const pass of ["startup", "reload"]) {
    await loader.reload();
    const loaded = loader.getExtensions();
    assert.deepEqual(loaded.errors, [], pass);
    assert.equal(loaded.extensions.length, 1, pass);
    const extension = loaded.extensions[0];
    assert.equal(extension.tools.size, 0);
    assert.equal(extension.commands.size, 0);
    assert.deepEqual([...extension.handlers.keys()],
      ["before_agent_start", "agent_settled", "agent_before_settle", "tool_call", "tool_result"]);
    // Loop guard: the same call returning the same result three times in a row is blocked next time.
    const call = extension.handlers.get("tool_call")[0];
    const toolResult = extension.handlers.get("tool_result")[0];
    let id = 0;
    const step = async (command, output) => {
      const toolCallId = `${pass}-${id++}`;
      const input = { command };
      const verdict = await call({ type: "tool_call", toolCallId, toolName: "bash", input }, {});
      await toolResult({ type: "tool_result", toolCallId, toolName: "bash", input,
        content: [{ type: "text", text: verdict?.block ? verdict.reason : output }], isError: !!verdict?.block }, {});
      return verdict;
    };
    for (let i = 0; i < 3; i++) assert.equal(await step("pwd; ls", "/repo"), undefined);
    const blocked = await step("pwd; ls", "/repo");
    assert.equal(blocked.block, true);
    assert.match(blocked.reason, /same result 3 times/);
    assert.notEqual(blocked.terminate, true);
    assert.equal((await step("pwd; ls", "/repo")).terminate, true);
    // A different call resets it, and polling whose output changes is never blocked.
    assert.equal(await step("git status", "clean"), undefined);
    for (let i = 0; i < 5; i++) assert.equal(await step("herdr agent get w", `working ${i}`), undefined);
    const previousGuard = process.env.AUTOMATTIC_LOOP_GUARD;
    process.env.AUTOMATTIC_LOOP_GUARD = "off";
    try {
      for (let i = 0; i < 5; i++) assert.equal(await step("pwd", "/repo"), undefined);
    } finally {
      if (previousGuard === undefined) delete process.env.AUTOMATTIC_LOOP_GUARD;
      else process.env.AUTOMATTIC_LOOP_GUARD = previousGuard;
    }
    await step("reset", "x");
    const handlers = extension.handlers.get("before_agent_start");
    assert.equal(handlers.length, 1);
    const result = await handlers[0]({ systemPrompt: "existing instructions" }, {});
    assert.ok(result.systemPrompt.startsWith("existing instructions\n"));
    assert.ok(result.systemPrompt.includes(`${root}/bootstrap.md`));
    assert.ok(result.systemPrompt.includes(`${root}/hosts/pi/session.md`));
    assert.ok(!result.systemPrompt.includes("/hosts/claude/"));
    assert.ok(!result.systemPrompt.includes("/hosts/codex/"));
    const previousHerdr = process.env.HERDR_ENV;
    try {
      for (const value of ["", "0", "1"]) {
        process.env.HERDR_ENV = value;
        const context = (await handlers[0]({ systemPrompt: "existing instructions" }, {})).systemPrompt;
        assert.equal(context.includes(`${root}/hosts/herdr.md`), value === "1");
        assert.ok(context.includes(`${root}/bootstrap.md`));
        assert.ok(context.includes(`${root}/hosts/pi/session.md`));
        assert.ok(context.startsWith("existing instructions\n"));
      }
    } finally {
      if (previousHerdr === undefined) delete process.env.HERDR_ENV;
      else process.env.HERDR_ENV = previousHerdr;
    }
    // Pi with structured sections: a returned systemPrompt would force the prompt
    // for typed-prompt runs only, so the hint must be a section instead.
    const sections = {};
    const structured = await handlers[0](
      { systemPrompt: "existing instructions", systemPromptOptions: { sections } }, {});
    assert.equal(structured, undefined);
    const section = Object.values(sections).join("");
    assert.ok(section.includes(`${root}/bootstrap.md`));
    assert.ok(section.includes(`${root}/hosts/pi/session.md`));
    assert.ok(!section.includes("existing instructions"));
    assert.ok(!loader.getSkills().skills.some((skill) => skill.name === "unselected-addon-probe"));
    const discovered = loader.getSkills().skills.filter(
      (skill) => realpathSync(skill.filePath).startsWith(`${root}/skills/`),
    );
    assert.deepEqual(discovered.map((skill) => skill.name).sort(), readdirSync(join(root, "skills")).sort());
    for (const skill of discovered) {
      assert.equal(skill.disableModelInvocation, !["code-comments", "housekeeping", "model-routing", "decision"].includes(skill.name));
    }
  }
  console.log("Pi native reader: shared skills and invocation policy, symlinked bootstrap, startup/reload: ok");
} finally {
  rmSync(temp, { recursive: true, force: true });
}

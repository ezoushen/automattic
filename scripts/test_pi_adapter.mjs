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
  symlinkSync(join(root, "harnesses/pi/bootstrap.ts"), join(extensions, "automattic.ts"));
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
    assert.deepEqual([...extension.handlers.keys()], ["before_agent_start", "agent_settled", "agent_before_settle"]);
    const handlers = extension.handlers.get("before_agent_start");
    assert.equal(handlers.length, 1);
    const result = await handlers[0]({ systemPrompt: "existing instructions" }, {});
    assert.ok(result.systemPrompt.startsWith("existing instructions\n"));
    assert.ok(result.systemPrompt.includes(`${root}/harnesses/pi/adapter.md`));
    assert.ok(!result.systemPrompt.includes("/harnesses/claude/"));
    assert.ok(!result.systemPrompt.includes("/harnesses/codex/"));
    const previousHerdr = process.env.HERDR_ENV;
    try {
      for (const value of ["", "0", "1"]) {
        process.env.HERDR_ENV = value;
        const context = (await handlers[0]({ systemPrompt: "existing instructions" }, {})).systemPrompt;
        assert.equal(context.includes(`${root}/harnesses/herdr.md`), value === "1");
        assert.ok(context.includes(`${root}/harnesses/pi/adapter.md`));
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
    assert.ok(section.includes(`${root}/harnesses/pi/adapter.md`));
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

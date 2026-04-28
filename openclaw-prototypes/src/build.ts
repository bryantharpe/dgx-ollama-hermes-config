import fs from "node:fs/promises";
import path from "node:path";
import type { PrototypesContext } from "./context.js";

const SLUG_RE = /^[a-z][a-z0-9-]{1,63}$/;
const FEATURE_RE = /^[a-z][a-z0-9-]{0,63}$/;

async function exists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

export function createBuildTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.build",
    label: "Construct build-spawn args",
    description:
      "Validate a spec directory and construct the canonical sessions_spawn arguments for the prototype-builder subagent. After this returns, the caller must invoke sessions_spawn with the returned args (agentId, runtime, mode, task, cwd, timeoutSeconds) to actually start the build. Use this when the user has approved a build for a slug whose specs you have already shown them.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        slug: { type: "string", description: "Prototype slug." },
        feature: {
          type: "string",
          description: "Feature within openspec/changes/. Defaults to 'prototype'.",
        },
        timeoutSeconds: {
          type: "number",
          description: "Per-task timeout. Default 3600 (1h).",
        },
      },
      required: ["slug"],
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const slug = String(params.slug ?? "").trim();
      const feature = String(params.feature ?? "prototype").trim() || "prototype";
      const timeoutSeconds =
        typeof params.timeoutSeconds === "number" && Number.isFinite(params.timeoutSeconds)
          ? Math.max(60, Math.floor(params.timeoutSeconds))
          : 3600;

      if (!SLUG_RE.test(slug)) {
        throw new Error(`slug must match ${SLUG_RE} (got ${JSON.stringify(slug)})`);
      }
      if (!FEATURE_RE.test(feature)) {
        throw new Error(`feature must match ${FEATURE_RE} (got ${JSON.stringify(feature)})`);
      }

      const slugDir = path.join(ctx.prototypesRoot, slug);
      const changesDir = path.join(slugDir, "openspec", "changes", feature);
      if (!(await exists(changesDir))) {
        throw new Error(
          `spec directory does not exist: ${changesDir}. Run meeting-transcript-to-specs first, or check the slug/feature names.`,
        );
      }

      // Build the structured prompt the subagent will receive. The agent's
      // workspace AGENTS.md already covers the build invariants; the
      // per-spawn prompt only needs the target paths and the directive.
      const task = [
        `Build the prototype at ${slugDir}.`,
        ``,
        `Spec directory: ${changesDir}`,
        `Slug: ${slug}`,
        `Feature: ${feature}`,
        ``,
        `Read proposal.md / design.md / tasks.md from the spec directory, then implement per your AGENTS.md operating guide. Call prototypes.verify(slug=${JSON.stringify(slug)}) before archive. End with prototypes.archive(slug=${JSON.stringify(slug)}, feature=${JSON.stringify(feature)}).`,
      ].join("\n");

      const spawnArgs = {
        runtime: "subagent" as const,
        mode: "run" as const,
        agentId: "prototype-builder",
        task,
        cwd: slugDir,
        runTimeoutSeconds: timeoutSeconds,
        label: `build ${slug}/${feature}`,
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                ok: true,
                slug,
                feature,
                spawnArgs,
                next: "Call sessions_spawn with the spawnArgs above to start the build. The task will appear in `openclaw tasks list`. The build agent will report completion when it ends.",
              },
              null,
              2,
            ),
          },
        ],
      };
    },
  };
}

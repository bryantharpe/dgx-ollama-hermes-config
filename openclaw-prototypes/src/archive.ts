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

export function createArchiveTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.archive",
    label: "Archive prototype change",
    description:
      "Move openspec/changes/<feature>/ to openspec/archive/<feature>/ for a slug. Refuses to overwrite an existing archive entry. Call this as the build-agent's last action before ending the turn (Wrapper Contract B).",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        slug: { type: "string", description: "Prototype slug." },
        feature: {
          type: "string",
          description: "Feature name within openspec/changes/. Defaults to 'prototype'.",
        },
      },
      required: ["slug"],
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const slug = String(params.slug ?? "").trim();
      const feature = String(params.feature ?? "prototype").trim() || "prototype";
      if (!SLUG_RE.test(slug)) {
        throw new Error(`slug must match ${SLUG_RE} (got ${JSON.stringify(slug)})`);
      }
      if (!FEATURE_RE.test(feature)) {
        throw new Error(`feature must match ${FEATURE_RE} (got ${JSON.stringify(feature)})`);
      }

      const slugDir = path.join(ctx.prototypesRoot, slug);
      const changesDir = path.join(slugDir, "openspec", "changes", feature);
      const archiveRoot = path.join(slugDir, "openspec", "archive");
      const archiveDir = path.join(archiveRoot, feature);

      if (!(await exists(changesDir))) {
        throw new Error(`no change to archive: ${changesDir} does not exist`);
      }
      if (await exists(archiveDir)) {
        throw new Error(
          `refusing to overwrite existing archive: ${archiveDir} already exists`,
        );
      }

      await fs.mkdir(archiveRoot, { recursive: true });
      await fs.rename(changesDir, archiveDir);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                ok: true,
                slug,
                feature,
                from: changesDir,
                to: archiveDir,
                archivedAt: new Date().toISOString(),
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

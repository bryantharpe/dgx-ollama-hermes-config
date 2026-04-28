import fs from "node:fs/promises";
import path from "node:path";
import type { PrototypesContext } from "./context.js";
import { loadHindsightConfig } from "./hindsight-config.js";

async function exists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function readIfPresent(p: string): Promise<string | null> {
  if (!(await exists(p))) return null;
  return fs.readFile(p, "utf8").catch(() => null);
}

export function createStoreSpecTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.store_spec",
    label: "Store prototype spec to Hindsight",
    description:
      "Retain the OpenSpec change proposal for a prototype to the configured Hindsight bank so it becomes recallable across prototypes. Failure is non-fatal — the spec stays on local disk regardless. Call once after writing proposal.md/design.md/tasks.md for a slug+feature.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        slug: { type: "string", description: "Prototype slug." },
        feature: {
          type: "string",
          description:
            "Feature name within the slug's openspec/changes/ directory (e.g. 'prototype').",
        },
        summary: {
          type: "string",
          description: "Optional short summary; if omitted, derived from proposal.md WHY section.",
        },
      },
      required: ["slug", "feature"],
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const slug = String(params.slug ?? "").trim();
      const feature = String(params.feature ?? "").trim();
      const summaryParam =
        typeof params.summary === "string" && params.summary.trim()
          ? params.summary.trim()
          : null;
      if (!slug || !feature) {
        throw new Error("slug and feature are required");
      }

      const hindsight = loadHindsightConfig();
      if (!hindsight) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                ok: false,
                stored: false,
                reason: "Hindsight credentials not configured in gateway env",
              }),
            },
          ],
        };
      }

      const changesDir = path.join(
        ctx.prototypesRoot,
        slug,
        "openspec",
        "changes",
        feature,
      );
      const archiveDir = path.join(
        ctx.prototypesRoot,
        slug,
        "openspec",
        "archive",
        feature,
      );

      const baseDir = (await exists(changesDir)) ? changesDir : archiveDir;
      const proposal = await readIfPresent(path.join(baseDir, "proposal.md"));
      const design = await readIfPresent(path.join(baseDir, "design.md"));
      const tasks = await readIfPresent(path.join(baseDir, "tasks.md"));

      if (!proposal && !design && !tasks) {
        throw new Error(`no spec markdown found at ${baseDir}`);
      }

      const summary =
        summaryParam ??
        (proposal
          ? proposal
              .split("\n")
              .slice(0, 10)
              .join("\n")
              .slice(0, 800)
          : `Prototype spec: ${slug}/${feature}`);

      const content = [
        `# Prototype spec: ${slug} / ${feature}`,
        "",
        `Summary: ${summary}`,
        "",
        proposal ? `## proposal.md\n\n${proposal}\n` : "",
        design ? `## design.md\n\n${design}\n` : "",
        tasks ? `## tasks.md\n\n${tasks}\n` : "",
      ]
        .filter(Boolean)
        .join("\n");

      const url = `${hindsight.apiUrl}/v1/default/banks/${encodeURIComponent(
        ctx.hindsightBankId,
      )}/memories`;

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${hindsight.apiKey}`,
          },
          body: JSON.stringify({
            items: [
              {
                content,
                context: "prototype-spec",
                document_id: `prototype-spec/${slug}/${feature}`,
                update_mode: "replace",
                timestamp: new Date().toISOString(),
                tags: [
                  "client:openclaw-prototypes",
                  "kind:prototype-spec",
                  `slug:${slug}`,
                  `feature:${feature}`,
                ],
                metadata: {
                  source: "openclaw-prototypes-plugin",
                  slug,
                  feature,
                },
              },
            ],
            async: true,
          }),
        });
        const ok = res.ok;
        const body = await res.text().catch(() => "");
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                ok,
                stored: ok,
                status: res.status,
                bank: ctx.hindsightBankId,
                slug,
                feature,
                response: body.slice(0, 400),
              }),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                ok: false,
                stored: false,
                error: String((err as Error).message ?? err),
                bank: ctx.hindsightBankId,
                slug,
                feature,
              }),
            },
          ],
        };
      }
    },
  };
}

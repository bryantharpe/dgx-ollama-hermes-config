import fs from "node:fs/promises";
import path from "node:path";
import type { PrototypesContext } from "./context.js";

async function exists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function statTimes(dir: string): Promise<{ ctime: string; mtime: string } | null> {
  try {
    const s = await fs.stat(dir);
    return { ctime: s.ctime.toISOString(), mtime: s.mtime.toISOString() };
  } catch {
    return null;
  }
}

async function readEnvPort(dir: string): Promise<number | null> {
  const envFile = path.join(dir, ".env");
  if (!(await exists(envFile))) return null;
  const raw = await fs.readFile(envFile, "utf8").catch(() => "");
  const m = raw.match(/^\s*PROTOTYPE_PORT\s*=\s*(\d+)\s*$/m);
  return m ? Number(m[1]) : null;
}

export function createListTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.list",
    label: "List prototypes",
    description:
      "List all prototype slugs registered in the ports registry, with their allocated host port and recent timestamps. Useful for answering 'what prototypes do I have?'.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {},
    },
    async execute(_id: string, _params: Record<string, unknown>) {
      const portsFile = path.join(ctx.prototypesRoot, ".registry", "ports.json");
      let ports: Record<string, number> = {};
      if (await exists(portsFile)) {
        const raw = await fs.readFile(portsFile, "utf8").catch(() => "");
        if (raw.trim()) {
          try {
            ports = JSON.parse(raw);
          } catch {
            // ignore
          }
        }
      }

      const rows: Array<{
        slug: string;
        port: number;
        path: string;
        exists: boolean;
        envPort: number | null;
        ctime: string | null;
        mtime: string | null;
      }> = [];

      for (const [slug, port] of Object.entries(ports)) {
        const dir = path.join(ctx.prototypesRoot, slug);
        const dirExists = await exists(dir);
        const times = dirExists ? await statTimes(dir) : null;
        const envPort = dirExists ? await readEnvPort(dir) : null;
        rows.push({
          slug,
          port,
          path: dir,
          exists: dirExists,
          envPort,
          ctime: times?.ctime ?? null,
          mtime: times?.mtime ?? null,
        });
      }

      rows.sort((a, b) => a.slug.localeCompare(b.slug));

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ prototypes: rows, count: rows.length }, null, 2),
          },
        ],
      };
    },
  };
}

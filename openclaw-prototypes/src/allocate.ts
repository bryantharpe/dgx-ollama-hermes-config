import fs from "node:fs/promises";
import path from "node:path";
import type { PrototypesContext } from "./context.js";

const SLUG_RE = /^[a-z][a-z0-9-]{1,63}$/;

const SKELETON_FILES = [
  "Dockerfile",
  "docker-compose.yml",
  "start.sh",
  ".dockerignore",
  ".gitignore",
  "src/__init__.py",
  "src/server/__init__.py",
  "src/database/__init__.py",
];

async function exists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function walkFiles(dir: string, exclude: (rel: string) => boolean): Promise<string[]> {
  const out: string[] = [];
  async function walk(cur: string, rel: string) {
    const entries = await fs.readdir(cur, { withFileTypes: true });
    for (const e of entries) {
      const childAbs = path.join(cur, e.name);
      const childRel = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) {
        if (!exclude(childRel)) await walk(childAbs, childRel);
      } else if (e.isFile() && !exclude(childRel)) {
        out.push(childRel);
      }
    }
  }
  await walk(dir, "");
  return out;
}

async function readPorts(portsFile: string): Promise<Record<string, number>> {
  if (!(await exists(portsFile))) return {};
  const raw = await fs.readFile(portsFile, "utf8").catch(() => "");
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return {};
  }
}

async function writePortsAtomic(portsFile: string, ports: Record<string, number>) {
  const tmp = `${portsFile}.tmp.${process.pid}.${Date.now()}`;
  await fs.writeFile(tmp, JSON.stringify(ports, null, 2) + "\n", "utf8");
  await fs.rename(tmp, portsFile);
}

async function allocatePort(
  ctx: PrototypesContext,
  slug: string,
): Promise<number> {
  const portsFile = path.join(ctx.prototypesRoot, ".registry", "ports.json");
  const ports = await readPorts(portsFile);
  if (typeof ports[slug] === "number") return ports[slug];

  const used = new Set(Object.values(ports));
  for (let p = ctx.portMin; p <= ctx.portMax; p++) {
    if (!used.has(p)) {
      ports[slug] = p;
      await writePortsAtomic(portsFile, ports);
      return p;
    }
  }
  throw new Error(`no free ports in ${ctx.portMin}-${ctx.portMax}`);
}

export function createAllocateTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.allocate",
    label: "Allocate prototype slug",
    description:
      "Seed a new prototype directory from the _template skeleton and allocate a host port from the 9000-9099 pool. Idempotent: re-running for the same slug preserves feature files and reuses the existing port allocation. Force-overwrites skeleton files so they cannot drift.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        slug: {
          type: "string",
          description: "Lowercase slug (^[a-z][a-z0-9-]{1,63}$), e.g. worlds-fair-companion",
        },
        reset: {
          type: "boolean",
          description:
            "If true, wipe the slug's BUILD ARTIFACTS (everything except openspec/ and data/) before re-seeding. NEVER deletes openspec/ — the change proposal is the user's input and is irreplaceable. Use only to recover from a badly-broken prior build.",
          default: false,
        },
      },
      required: ["slug"],
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const slug = String(params.slug ?? "").trim();
      const reset = params.reset === true;
      if (!SLUG_RE.test(slug)) {
        throw new Error(
          `slug must match ^[a-z][a-z0-9-]{1,63}$ (got ${JSON.stringify(slug)})`,
        );
      }

      const root = ctx.prototypesRoot;
      const template = path.join(root, "_template");
      const target = path.join(root, slug);

      if (!(await exists(template))) {
        throw new Error(`template not found at ${template}`);
      }

      const freshCreate = !(await exists(target));
      // Reset wipes build artifacts but PRESERVES openspec/ (the change proposal,
      // which is user-authored and irreplaceable) and data/ (the runtime volume,
      // which Docker may have created as root-owned and re-creates on container
      // start anyway). Anything else under the slug dir is a build artifact and
      // safe to discard.
      if (reset && (await exists(target))) {
        const protectedNames = new Set(["openspec", "data"]);
        const entries = await fs.readdir(target, { withFileTypes: true });
        for (const e of entries) {
          if (protectedNames.has(e.name)) continue;
          await fs.rm(path.join(target, e.name), { recursive: true, force: true });
        }
      }

      await fs.mkdir(target, { recursive: true });
      // data/ is a runtime volume; create only if absent, never copy contents.
      await fs.mkdir(path.join(target, "data"), { recursive: true });

      // Fill in any missing files from template (preserves existing feature edits).
      const rels = await walkFiles(template, (rel) => rel === "data" || rel.startsWith("data/"));
      for (const rel of rels) {
        const src = path.join(template, rel);
        const dst = path.join(target, rel);
        if (!(await exists(dst))) {
          await fs.mkdir(path.dirname(dst), { recursive: true });
          await fs.copyFile(src, dst);
        }
      }

      // Strip placeholder README on fresh creates — build agent writes its own.
      if (freshCreate || reset) {
        await fs.rm(path.join(target, "README.md"), { force: true });
      }

      // Force-overwrite skeleton files so they cannot drift.
      for (const f of SKELETON_FILES) {
        const src = path.join(template, f);
        const dst = path.join(target, f);
        await fs.mkdir(path.dirname(dst), { recursive: true });
        await fs.copyFile(src, dst);
      }

      const port = await allocatePort(ctx, slug);

      const envContent = `PROTOTYPE_NAME=${slug}\nPROTOTYPE_PORT=${port}\n`;
      await fs.writeFile(path.join(target, ".env"), envContent, "utf8");

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ slug, port, path: target }, null, 2),
          },
        ],
      };
    },
  };
}

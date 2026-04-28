import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import type { PrototypesContext } from "./context.js";

const SLUG_RE = /^[a-z][a-z0-9-]{1,63}$/;

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

async function dockerExec(
  container: string,
  cmd: string[],
  timeoutMs = 8000,
): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve) => {
    const proc = spawn("docker", ["exec", container, ...cmd], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try {
        proc.kill("SIGKILL");
      } catch {
        // ignore
      }
      resolve({ stdout, stderr, code: 124 });
    }, timeoutMs);
    proc.stdout.on("data", (d: Buffer) => (stdout += d.toString("utf8")));
    proc.stderr.on("data", (d: Buffer) => (stderr += d.toString("utf8")));
    proc.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ stdout, stderr, code: code ?? -1 });
    });
    proc.on("error", () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ stdout, stderr, code: -1 });
    });
  });
}

function readEnv(envContent: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of envContent.split("\n")) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

function extractStaticUrls(html: string): string[] {
  const set = new Set<string>();
  const re = /\/static\/[A-Za-z0-9._/-]+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) set.add(m[0]);
  return Array.from(set).sort();
}

function extractInserts(seedPy: string): Array<{ table: string; cols: string[] }> {
  const out: Array<{ table: string; cols: string[] }> = [];
  // INSERT [OR IGNORE/REPLACE] INTO <table> (col1, col2, ...) VALUES ...
  const re = /INSERT\s+(?:OR\s+(?:IGNORE|REPLACE)\s+)?INTO\s+(\w+)\s*\(([^)]+)\)/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(seedPy)) !== null) {
    const table = m[1];
    const cols = m[2]
      .split(",")
      .map((c) => c.trim().replace(/^["`'\[]|["`'\]]$/g, ""))
      .filter(Boolean);
    out.push({ table, cols });
  }
  return out;
}

function extractTables(schemaSql: string): Map<string, Set<string>> {
  const tables = new Map<string, Set<string>>();
  // CREATE TABLE [IF NOT EXISTS] <table> ( col1 TYPE [, col2 TYPE]* )
  // Naive but matches the skeleton's style.
  const re = /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(([^;]+?)\)\s*;/gis;
  let m: RegExpExecArray | null;
  while ((m = re.exec(schemaSql)) !== null) {
    const table = m[1];
    const body = m[2];
    const cols = new Set<string>();
    for (const rawLine of body.split("\n")) {
      const line = rawLine.trim().replace(/,$/, "");
      if (!line) continue;
      // Skip standalone constraint lines.
      if (/^(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK|CONSTRAINT)\b/i.test(line)) continue;
      const colMatch = line.match(/^["`'\[]?(\w+)["`'\]]?/);
      if (colMatch) cols.add(colMatch[1]);
    }
    tables.set(table, cols);
  }
  return tables;
}

function extractEndpoints(apiPy: string): Array<{ method: string; route: string }> {
  const out: Array<{ method: string; route: string }> = [];
  const re = /@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(apiPy)) !== null) {
    out.push({ method: m[1].toUpperCase(), route: m[2] });
  }
  return out;
}

async function probeUrl(
  containerName: string,
  url: string,
): Promise<{ code: number; raw: string }> {
  // Run curl INSIDE the prototype container — its localhost:8000 is the app's
  // own bound port, so we don't need the host gateway dance.
  const r = await dockerExec(containerName, [
    "curl",
    "-sf",
    "-o",
    "/dev/null",
    "-w",
    "%{http_code}",
    "-m",
    "5",
    url,
  ]);
  // -sf returns non-zero on >=400; we only care about the printed status code.
  const code = parseInt(r.stdout.trim() || "0", 10) || 0;
  return { code, raw: r.stdout.trim() };
}

export function createVerifyTool(ctx: PrototypesContext) {
  return {
    name: "prototypes.verify",
    label: "Verify prototype",
    description:
      "Run the pre-archive audit on a prototype: (a) every /static/ URL referenced in src/frontend/index.html returns 200, (b) every column in seed.py INSERTs exists in schema.sql, (c) every @router.get/post in src/server/api.py returns non-5xx. Returns { ok, failures }. Build agent must call this before prototypes.archive.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        slug: { type: "string", description: "Prototype slug." },
      },
      required: ["slug"],
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const slug = String(params.slug ?? "").trim();
      if (!SLUG_RE.test(slug)) {
        throw new Error(`slug must match ${SLUG_RE} (got ${JSON.stringify(slug)})`);
      }

      const slugDir = path.join(ctx.prototypesRoot, slug);
      if (!(await exists(slugDir))) {
        throw new Error(`prototype dir does not exist: ${slugDir}`);
      }

      const envContent = (await readIfPresent(path.join(slugDir, ".env"))) ?? "";
      const envVars = readEnv(envContent);
      const containerName = envVars.PROTOTYPE_NAME;
      if (!containerName) {
        throw new Error(`.env missing PROTOTYPE_NAME at ${slugDir}/.env`);
      }

      const failures: string[] = [];

      // (a) Asset audit
      const indexHtml = await readIfPresent(
        path.join(slugDir, "src", "frontend", "index.html"),
      );
      if (indexHtml) {
        const urls = extractStaticUrls(indexHtml);
        for (const u of urls) {
          const { code } = await probeUrl(containerName, `http://localhost:8000${u}`);
          if (code !== 200) failures.push(`ASSET MISSING: ${u} (status ${code || "unreachable"})`);
        }
      } else {
        failures.push(`ASSET AUDIT: src/frontend/index.html not found at ${slugDir}`);
      }

      // (b) Schema/seed audit
      const schemaSql = await readIfPresent(
        path.join(slugDir, "src", "database", "schema.sql"),
      );
      const seedPy = await readIfPresent(path.join(slugDir, "src", "database", "seed.py"));
      if (schemaSql && seedPy) {
        const tables = extractTables(schemaSql);
        const inserts = extractInserts(seedPy);
        for (const { table, cols } of inserts) {
          const known = tables.get(table);
          if (!known) {
            failures.push(`SCHEMA DRIFT: seed.py inserts into table ${table}, not in schema.sql`);
            continue;
          }
          for (const c of cols) {
            if (!known.has(c)) {
              failures.push(`SCHEMA DRIFT: ${table}.${c} (in seed.py INSERT, not in schema.sql)`);
            }
          }
        }
      }

      // (c) Endpoint audit — every @router/@app route returns non-5xx.
      const apiPy = await readIfPresent(path.join(slugDir, "src", "server", "api.py"));
      if (apiPy) {
        const endpoints = extractEndpoints(apiPy);
        for (const { method, route } of endpoints) {
          // Only probe path params that don't contain dynamic placeholders.
          if (/[<{]/.test(route)) continue;
          const url = `http://localhost:8000${route.startsWith("/") ? "" : "/"}${route}`;
          const { code } = await probeUrl(containerName, url);
          if (code >= 500) failures.push(`ENDPOINT FAILING: ${method} ${route} (status ${code})`);
        }
      }

      const ok = failures.length === 0;
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ ok, slug, container: containerName, failures }, null, 2),
          },
        ],
      };
    },
  };
}

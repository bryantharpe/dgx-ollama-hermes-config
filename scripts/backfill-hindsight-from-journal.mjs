#!/usr/bin/env node
// Ingest ~/.openclaw/workspace/memory/*.md into Hindsight via the retain API.
// Replaces the LanceDB-era backfill script (kept alongside in scripts/ for
// reference until Phase 3 decommission).
//
// Modes:
//   (default) walk JOURNAL_DIR and POST every *.md as one retain item
//   --file <path>  ingest only the given file
//   --sync         send async:false (waits for fact extraction; slower per call)
//
// Idempotent: each file uses a stable document_id so update_mode:replace
// upserts cleanly. Re-running is safe.
//
// Required env (via ~/.openclaw/.env):
//   HINDSIGHT_API_URL              e.g. https://hindsight-bryan.fly.dev
//   HINDSIGHT_API_TENANT_API_KEY   bearer token
//   HINDSIGHT_BANK_ID              defaults to "bryan-default"

import { readdir, readFile, stat } from "node:fs/promises";
import { basename, join } from "node:path";
import os from "node:os";

const API_URL = process.env.HINDSIGHT_API_URL;
const TOKEN   = process.env.HINDSIGHT_API_TENANT_API_KEY;
const BANK_ID = process.env.HINDSIGHT_BANK_ID ?? "bryan-default";

if (!API_URL || !TOKEN) {
  console.error("HINDSIGHT_API_URL and HINDSIGHT_API_TENANT_API_KEY are required.");
  console.error("Source ~/.openclaw/.env first: set -a; . ~/.openclaw/.env; set +a");
  process.exit(2);
}

const JOURNAL_DIR = process.env.JOURNAL_DIR
  ?? join(os.homedir(), ".openclaw", "workspace", "memory");

function parseArgs(argv) {
  const out = { file: null, sync: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--file" && argv[i + 1]) {
      out.file = argv[++i];
    } else if (argv[i].startsWith("--file=")) {
      out.file = argv[i].slice("--file=".length);
    } else if (argv[i] === "--sync") {
      out.sync = true;
    }
  }
  return out;
}

function documentIdFor(name) {
  return `openclaw-journal-${name.replace(/\.md$/i, "")}`;
}

async function retainFile(path, sync) {
  const name = basename(path);
  const [body, st] = await Promise.all([readFile(path, "utf8"), stat(path)]);
  if (body.trim().length === 0) {
    return { name, status: "skip-empty" };
  }

  const res = await fetch(`${API_URL}/v1/default/banks/${BANK_ID}/memories`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      items: [{
        content: body,
        context: "openclaw journal (backfill)",
        document_id: documentIdFor(name),
        update_mode: "replace",
        timestamp: new Date(st.mtimeMs).toISOString(),
        tags: ["client:openclaw", "user:bryan", "source:backfill"],
        metadata: {
          source: "openclaw-journal-backfill",
          filename: name,
          mtime_ms: String(Math.floor(st.mtimeMs)),
        },
      }],
      async: !sync,
    }),
  });

  const text = await res.text();
  if (!res.ok) {
    return { name, status: `http-${res.status}`, detail: text.slice(0, 200) };
  }
  let json = {};
  try { json = JSON.parse(text); } catch { /* ignore */ }
  const op = json.operation_id ?? (json.operation_ids && json.operation_ids[0]) ?? null;
  return { name, status: "ok", op };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  const targets = args.file
    ? [args.file]
    : (await readdir(JOURNAL_DIR))
        .filter((f) => f.endsWith(".md"))
        .sort()
        .map((f) => join(JOURNAL_DIR, f));

  console.log(`mode: ${args.sync ? "sync" : "async"}; bank: ${BANK_ID}; targets: ${targets.length}`);

  const counters = { ok: 0, fail: 0, skip: 0 };
  for (const path of targets) {
    try {
      const r = await retainFile(path, args.sync);
      if (r.status === "ok") {
        counters.ok++;
        console.log(`  ${r.name}: ok (op ${r.op ?? "n/a"})`);
      } else if (r.status === "skip-empty") {
        counters.skip++;
        console.log(`  ${r.name}: skip (empty file)`);
      } else {
        counters.fail++;
        console.error(`  ${r.name}: ${r.status} ${r.detail ?? ""}`);
        if (r.status.startsWith("http-5")) {
          console.error("  fail-fast on 5xx");
          process.exit(1);
        }
      }
    } catch (err) {
      counters.fail++;
      console.error(`  ${basename(path)}: error ${err?.message ?? String(err)}`);
    }
  }

  console.log(`done. ok=${counters.ok} fail=${counters.fail} skip=${counters.skip}`);
  if (!args.sync) {
    console.log(`poll ops: curl -s -H "Authorization: Bearer \\$TOKEN" "${API_URL}/v1/default/banks/${BANK_ID}/operations?status=running" | jq`);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });

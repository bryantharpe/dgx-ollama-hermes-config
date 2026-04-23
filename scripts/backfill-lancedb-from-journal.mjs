#!/usr/bin/env node
// Ingest ~/.openclaw/workspace/memory/*.md into the memory-lancedb store so
// recall via the memory-lancedb plugin picks up prior sessions.
//
// Modes:
//   (default) scan JOURNAL_DIR and ingest all *.md
//   --file <path>   ingest only the given file
//
// Idempotent: before inserting chunks for <file>, rows whose `text` begins
// with `[journal:<basename>#` are deleted. Re-running is safe.
//
// Intended to run with access to /app/node_modules in the openclaw-gateway
// image (either as the gateway process or via `node` launched with cwd=/app).

import { readdir, readFile, stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { basename, join } from "node:path";
import * as lancedb from "@lancedb/lancedb";
import OpenAI from "openai";

const JOURNAL_DIR = process.env.JOURNAL_DIR ?? "/home/node/.openclaw/workspace/memory";
const DB_PATH     = process.env.DB_PATH     ?? "/home/node/.openclaw/memory/lancedb";
const TABLE       = "memories";
const EMBED_URL   = process.env.EMBED_URL   ?? "http://ollama:11434/v1";
const EMBED_MODEL = process.env.EMBED_MODEL ?? "nomic-embed-text";
const VECTOR_DIM  = 768;

const MIN_CHUNK = 80;
const MAX_CHUNK = 1800;
const TARGET    = 1200;

const ai = new OpenAI({ apiKey: "ollama", baseURL: EMBED_URL });

function parseArgs(argv) {
  const out = { file: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--file" && argv[i + 1]) {
      out.file = argv[++i];
    } else if (argv[i].startsWith("--file=")) {
      out.file = argv[i].slice("--file=".length);
    }
  }
  return out;
}

async function embed(text) {
  const r = await ai.embeddings.create({ model: EMBED_MODEL, input: text });
  return r.data[0].embedding;
}

function stripNoise(body) {
  body = body.replace(/<relevant-memories>[\s\S]*?<\/relevant-memories>\s*/g, "");
  body = body.replace(/Sender \(untrusted metadata\):\s*```json[\s\S]*?```\s*/g, "");
  return body;
}

function chunkBySpeaker(body) {
  const cleaned = stripNoise(body);
  const turns = cleaned.split(/\n(?=user:|assistant:)/g).map((t) => t.trim()).filter(Boolean);
  const out = [];
  let buf = "";
  for (const turn of turns) {
    if ((buf + "\n\n" + turn).length > TARGET && buf.length >= MIN_CHUNK) {
      out.push(buf.trim());
      buf = turn;
    } else {
      buf = buf ? buf + "\n\n" + turn : turn;
    }
    if (buf.length >= MAX_CHUNK) {
      out.push(buf.slice(0, MAX_CHUNK).trim());
      buf = "";
    }
  }
  if (buf.length >= MIN_CHUNK) out.push(buf.trim());
  return out;
}

async function openTable(db) {
  const tables = await db.tableNames();
  if (tables.includes(TABLE)) return db.openTable(TABLE);
  const t = await db.createTable(TABLE, [{
    id: "__schema__",
    text: "",
    vector: Array.from({ length: VECTOR_DIM }).fill(0),
    importance: 0,
    category: "other",
    createdAt: 0,
  }]);
  await t.delete('id = "__schema__"');
  return t;
}

// LanceDB uses SQL-like predicates; single-quote any embedded quotes in the pattern.
function sqlLiteral(s) {
  return `'${s.replace(/'/g, "''")}'`;
}

async function ingestFile(table, path) {
  const name = basename(path);
  const [body, st] = await Promise.all([readFile(path, "utf8"), stat(path)]);
  const chunks = chunkBySpeaker(body);

  // Idempotent: drop any prior rows for this file before inserting new ones.
  const prefix = `[journal:${name}#`;
  await table.delete(`text LIKE ${sqlLiteral(prefix + "%")}`);

  if (chunks.length === 0) return { name, stored: 0 };

  const rows = [];
  for (let i = 0; i < chunks.length; i++) {
    const text = `[journal:${name}#${i + 1}] ${chunks[i]}`;
    try {
      const vector = await embed(text);
      rows.push({
        id: randomUUID(),
        text,
        vector,
        importance: 0.4,
        category: "other",
        createdAt: Math.floor(st.mtimeMs),
      });
    } catch (err) {
      console.error(`  embed failed for ${name}#${i + 1}: ${err.message}`);
    }
  }
  if (rows.length) await table.add(rows);
  return { name, stored: rows.length };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  const db = await lancedb.connect(DB_PATH);
  const table = await openTable(db);
  const before = await table.countRows();
  console.log(`lancedb opened: ${DB_PATH}, current rows: ${before}`);

  const targets = args.file
    ? [args.file]
    : (await readdir(JOURNAL_DIR)).filter((f) => f.endsWith(".md")).sort().map((f) => join(JOURNAL_DIR, f));

  let scanned = 0;
  let stored  = 0;
  for (const path of targets) {
    const r = await ingestFile(table, path);
    scanned++;
    stored += r.stored;
    console.log(`  ${r.name}: ${r.stored > 0 ? `+${r.stored} chunks` : "no chunks"}`);
  }

  const after = await table.countRows();
  console.log(`done. files: ${scanned}, chunks: ${stored}, rows now: ${after} (was ${before})`);
}

main().catch((e) => { console.error(e); process.exit(1); });

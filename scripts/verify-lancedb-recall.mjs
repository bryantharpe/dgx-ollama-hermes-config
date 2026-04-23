#!/usr/bin/env node
// Quick verification: embed a query through Ollama and run a vector search
// against the live LanceDB store. Confirms the backfill is queryable.

import * as lancedb from "@lancedb/lancedb";
import OpenAI from "openai";

const DB_PATH = "/home/node/.openclaw/memory/lancedb";
const TABLE   = "memories";

const ai = new OpenAI({ apiKey: "ollama", baseURL: "http://ollama:11434/v1" });
const queries = process.argv.slice(2).length
  ? process.argv.slice(2)
  : ["worlds fair companion", "telegram allowlist", "bonding ritual", "port troubleshooting"];

const db    = await lancedb.connect(DB_PATH);
const table = await db.openTable(TABLE);
console.log(`rows: ${await table.countRows()}\n`);

for (const q of queries) {
  const e = await ai.embeddings.create({ model: "nomic-embed-text", input: q });
  const hits = await table.vectorSearch(e.data[0].embedding).limit(3).toArray();
  console.log(`query: "${q}"`);
  for (const h of hits) {
    const dist = (h._distance ?? 0).toFixed(3);
    const sim  = (1 / (1 + (h._distance ?? 0))).toFixed(3);
    const snippet = String(h.text).replace(/\s+/g, " ").slice(0, 110);
    console.log(`  d=${dist} sim=${sim} ${snippet}…`);
  }
  console.log("");
}

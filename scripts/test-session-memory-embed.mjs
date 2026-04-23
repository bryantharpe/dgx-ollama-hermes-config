#!/usr/bin/env node
// Synthetic invocation of the session-memory-embed hook handler.
// Imports the handler like the gateway does, passes a fake command event.
// Intended to run inside openclaw-gateway with cwd=/app.

import { pathToFileURL } from "node:url";

const HANDLER_PATH = "/home/node/.openclaw/workspace/hooks/session-memory-embed/handler.js";
const mod = await import(pathToFileURL(HANDLER_PATH).href);
const handler = mod.default;

const event = {
  type: "command",
  action: process.argv[2] ?? "reset",
  sessionKey: "agent:main:main",
  timestamp: new Date(Date.now() - 60_000),  // 60s ago -> pick up any recent file
  context: { workspaceDir: "/home/node/.openclaw/workspace" },
};

await handler(event);
console.log("handler returned");

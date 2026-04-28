import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { createAllocateTool } from "./src/allocate.js";
import { createArchiveTool } from "./src/archive.js";
import { createBuildTool } from "./src/build.js";
import { createListTool } from "./src/list.js";
import { createStoreSpecTool } from "./src/store-spec.js";
import { createVerifyTool } from "./src/verify.js";

export default definePluginEntry({
  id: "prototypes",
  name: "Prototype Lifecycle",
  description:
    "Allocate / archive / verify / list / build / store_spec tools for the meeting-transcript-to-prototype workflow.",
  register(api) {
    const cfg = (api.pluginConfig ?? {}) as PrototypesPluginCfg;
    const ctx = {
      prototypesRoot: cfg.prototypesRoot ?? "/home/node/prototypes",
      portMin: cfg.portRange?.min ?? 9000,
      portMax: cfg.portRange?.max ?? 9099,
      hindsightBankId: cfg.hindsight?.bankId ?? "bryan-prototypes",
    };

    api.registerTool(createAllocateTool(ctx));
    api.registerTool(createListTool(ctx));
    api.registerTool(createStoreSpecTool(ctx));
    api.registerTool(createArchiveTool(ctx));
    api.registerTool(createVerifyTool(ctx));
    api.registerTool(createBuildTool(ctx));
  },
});

export type PrototypesPluginCfg = {
  prototypesRoot?: string;
  portRange?: { min?: number; max?: number };
  hindsight?: { bankId?: string };
};

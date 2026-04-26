# Legacy Ollama Modelfiles

These are the Ollama `Modelfile` definitions that were in use before the migration to vLLM on 2026-04-25.

vLLM does not consume Ollama Modelfiles — it loads HuggingFace safetensors directly via `vllm serve <repo>`. These files are kept here for archival purposes and as a rollback aid: if the vLLM stack is ever rolled back to Ollama, move these back to the repository root and re-run `bootstrap.sh` (which itself was rewritten — restore the pre-migration version from git history if needed).

The active model serving Qwen 3.6 35B A3B is now `Qwen/Qwen3.6-35B-A3B-FP8` running under vLLM, multi-aliased so existing client model names (`qwen3.6-35b:128k`, `qwen3.6:35b-a3b-q8_0`, `qwen3.6-35b-a3b:q6-65k`, `hermes-orchestrator:qwen3.6-128k`) all resolve to the same backend.

#!/usr/bin/env python3
"""Idempotent database bootstrap. Runs at container startup via start.sh.

DO NOT REMOVE the os.makedirs(DATA_DIR) call — sqlite3.connect() fails
with "unable to open database file" if DATA_DIR doesn't exist on first
boot, and the container falls into a restart loop.

SCHEMA / SEED CONSISTENCY INVARIANT:
    Every column name in any INSERT below MUST be declared in schema.sql
    for the same table. If you add a column to seed data, add it to the
    CREATE TABLE. Drift crashes the container at startup with
    `sqlite3.OperationalError: table X has no column named Y`.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "schema.sql")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

with open(SCHEMA_PATH, "r") as f:
    schema = f.read()
if schema.strip():
    cursor.executescript(schema)

# ─── add seed data below ─────────────────────────────────────────────────────
# Use INSERT OR IGNORE / INSERT OR REPLACE so re-running is safe.
#
# Example:
# cursor.executemany(
#     "INSERT OR IGNORE INTO items (id, name) VALUES (?, ?)",
#     [(1, "alpha"), (2, "beta")],
# )

# ─── talks (15+ talks) ───────────────────────────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO talks (id, title, speaker_name, speaker_bio, speaker_github, start_time, end_time, room, description, topics, track, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (1, 'Building RAG Pipelines That Actually Work', 'Dr. Maya Chen', 'ML engineer specializing in retrieval-augmented generation systems', 'mayachen', '2026-06-29T14:00:00', '2026-06-29T14:45:00', 'Moscone South 201', 'Most RAG systems fail at retrieval quality. This talk covers embedding strategies, chunking heuristics, and re-ranking techniques for production-grade pipelines.', 'rag,pipelines,retrieval,embeddings', 'AI Infra', 'intermediate'),
        (2, 'Local LLM Orchestration with Ollama', 'James Liu', 'Open-source contributor to LLM tooling ecosystem', 'jamesliu', '2026-06-29T15:00:00', '2026-06-29T15:45:00', 'Moscone South 202', 'Deploy and orchestrate local LLMs at scale. We explore Ollama, text-embeddings-inference, and practical patterns for hybrid cloud-local inference.', 'llm,local-models,ollama,orchestration', 'Agents', 'beginner'),
        (3, 'Multi-Agent Systems for Code Review', 'Sarah Kim', 'Research engineer at OpenAI', 'sarahkim', '2026-06-29T16:00:00', '2026-06-29T16:45:00', 'Moscone South 203', 'Building autonomous code review agents that coordinate across multiple LLMs to provide comprehensive feedback on pull requests.', 'agents,multi-agent,code-review,automation', 'Agents', 'advanced'),
        (4, 'MLOps Best Practices in 2026', 'David Rodriguez', 'Principal MLOps engineer at Stripe', 'drodriguez', '2026-06-29T17:00:00', '2026-06-29T17:45:00', 'Moscone South 201', 'Lessons from scaling ML pipelines across 50+ teams. Focus on monitoring, drift detection, and cost optimization.', 'mlops,monitoring,production,optimization', 'ML Ops', 'intermediate'),
        (5, 'Vector Embeddings 101', 'Amit Patel', 'Data scientist at Hugging Face', 'amitp', '2026-06-30T09:00:00', '2026-06-30T09:45:00', 'Moscone South 201', 'A gentle introduction to vector embeddings: how they work, which models to choose, and how to evaluate embedding quality.', 'embeddings,vectors,beginner,nlp', 'AI Infra', 'beginner'),
        (6, 'Fine-Tuning Llama for Specific Domains', 'Dr. Emily Wang', 'Research scientist at EleutherAI', 'emilywang', '2026-06-30T10:00:00', '2026-06-30T10:45:00', 'Moscone South 202', 'Domain adaptation techniques for Llama models. We cover LoRA, QLoRA, and instruction tuning.', 'llama,fine-tuning,adaptation,qlora', 'Local Models', 'advanced'),
        (7, 'Building AI Agents with LangGraph', 'Michael Torres', 'Developer advocate at LangChain', 'michaelt', '2026-06-30T11:00:00', '2026-06-30T11:45:00', 'Moscone South 203', 'Hands-on workshop building production-ready AI agents using LangGraph. Includes memory management and tool calling patterns.', 'agents,langgraph,tool-calling,langchain', 'Agents', 'intermediate'),
        (8, 'Efficient Inference with vLLM', 'Priya Sharma', 'Engineer at Anyscale', 'priyasharma', '2026-06-30T12:00:00', '2026-06-30T12:45:00', 'Moscone South 201', 'vLLM is revolutionizing LLM inference. We explore PagedAttention, streaming generation, and production deployments.', 'inference,vllm,performance,optimization', 'AI Infra', 'intermediate'),
        (9, 'Prompt Engineering for Security', 'Alex Rivera', 'Security researcher at Trail of Bits', 'arivera', '2026-06-30T13:00:00', '2026-06-30T13:45:00', 'Moscone South 202', 'Avoid prompt injection attacks and design robust prompts that resist manipulation by malicious inputs.', 'security,prompt-engineering,adversarial', 'Security', 'beginner'),
        (10, 'Testing LLM Applications', 'Lisa Nguyen', 'Software engineer at Netflix', 'lisany', '2026-06-30T14:00:00', '2026-06-30T14:45:00', 'Moscone South 203', 'How Netflix tests its LLM-powered recommendation system. Coverage includes unit tests, integration tests, and human evaluation.', 'testing,evaluation,llm,quality', 'ML Ops', 'intermediate'),
        (11, 'Real-Time RAG with Vector Databases', 'Chris Martin', 'CTO at Pinecone', 'chrismartin', '2026-06-30T15:00:00', '2026-06-30T15:45:00', 'Moscone South 201', 'Building real-time search and recommendation with vector databases. Latency benchmarks and optimization techniques.', 'rag,vectordb,real-time,pinecone', 'AI Infra', 'advanced'),
        (12, 'Open Source Model Evaluation', 'Dr. Kevin Foster', 'Founder of EvalHub', 'kevinfoster', '2026-06-30T16:00:00', '2026-06-30T16:45:00', 'Moscone South 202', 'Comprehensive evaluation frameworks for open-source models. We compare MMLU, HellaSwag, and custom benchmarks.', 'evaluation,open-source,metrics', 'AI Infra', 'intermediate'),
        (13, 'Agent Coordination Patterns', 'Nicole Park', 'Research engineer at Anthropic', 'nicolepark', '2026-06-30T17:00:00', '2026-06-30T17:45:00', 'Moscone South 203', 'Patterns for coordinating multiple agents: consensus, arbitration, and hierarchical control.', 'agents,coordination,multi-agent', 'Agents', 'advanced'),
        (14, 'GPU Optimization for Local Inference', 'Tom Williams', 'Engineer at RunPod', 'tomw', '2026-07-01T09:00:00', '2026-07-01T09:45:00', 'Moscone South 201', 'Maximize throughput on consumer GPUs. Quantization, batching, and memory optimization techniques.', 'gpu,optimization,local-models,quantization', 'Local Models', 'intermediate'),
        (15, 'Building a Personal Knowledge Graph', 'Rachel Green', 'Data engineer at Neo4j', 'rachely', '2026-07-01T10:00:00', '2026-07-01T10:45:00', 'Moscone South 202', 'Use LLMs to extract structured data from unstructured text and build a personal knowledge graph for query and reasoning.', 'kg,knowledge-graphs,extraction', 'AI Infra', 'beginner'),
        (16, 'Secure Multi-Party LLM Inference', 'Dr. Alan Zhang', 'Cryptographer at MIT', 'alanz', '2026-07-01T11:00:00', '2026-07-01T11:45:00', 'Moscone South 203', 'Privacy-preserving LLM inference using secure multi-party computation. Early research and practical implementations.', 'privacy,smpc,inference,security', 'Security', 'advanced'),
        (17, 'AI-Powered CI/CD', 'Jennifer Lee', 'DevOps engineer at GitHub', 'jenniferl', '2026-07-01T12:00:00', '2026-07-01T12:45:00', 'Moscone South 201', 'Auto-generating PR descriptions, test cases, and bug reports using LLMs integrated into the DevOps pipeline.', 'devops,ci-cd,automation', 'ML Ops', 'beginner'),
        (18, 'Fine-Grained RAG with Graph RAG', 'Samir Gupta', 'ML engineer at Microsoft', 'samirg', '2026-07-01T13:00:00', '2026-07-01T13:45:00', 'Moscone South 202', 'Beyond basic retrieval: graph-aware RAG that understands relationships between concepts for more accurate answers.', 'rag,graphs,relationships,retrieval', 'AI Infra', 'advanced'),
        (19, 'Constitutional AI without Human Annotations', 'Dr. Brenda Cox', 'Research scientist at Anthropic', 'brendac', '2026-07-01T14:00:00', '2026-07-01T14:45:00', 'Moscone South 203', 'Self-supervised alignment techniques. How models can learn to self-critique and improve without human feedback.', 'alignment,constitutional-ai,rlhf', 'Agents', 'advanced'),
        (20, 'Edge LLMs for Mobile Devices', 'Marcus Johnson', 'Mobile engineer at Apple', 'marcusj', '2026-07-01T15:00:00', '2026-07-01T15:45:00', 'Moscone South 201', 'Running efficient LLMs on iPhone and Android. Quantization, model splitting, and on-device processing.', 'mobile,edge,quantization,android', 'Local Models', 'intermediate'),
    ],
)

# ─── speakers (10+ speakers) ──────────────────────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO speakers (id, name, bio, github, company, talk_ids) VALUES (?, ?, ?, ?, ?, ?)",
    [
        (1, 'Dr. Maya Chen', 'ML engineer specializing in retrieval-augmented generation systems', 'mayachen', 'Hugging Face', '1'),
        (2, 'James Liu', 'Open-source contributor to LLM tooling ecosystem', 'jamesliu', 'OLLAMA', '2'),
        (3, 'Sarah Kim', 'Research engineer at OpenAI', 'sarahkim', 'OpenAI', '3'),
        (4, 'David Rodriguez', 'Principal MLOps engineer at Stripe', 'drodriguez', 'Stripe', '4'),
        (5, 'Amit Patel', 'Data scientist at Hugging Face', 'amitp', 'Hugging Face', '5'),
        (6, 'Dr. Emily Wang', 'Research scientist at EleutherAI', 'emilywang', 'EleutherAI', '6'),
        (7, 'Michael Torres', 'Developer advocate at LangChain', 'michaelt', 'LangChain', '7'),
        (8, 'Priya Sharma', 'Engineer at Anyscale', 'priyasharma', 'Anyscale', '8'),
        (9, 'Alex Rivera', 'Security researcher at Trail of Bits', 'arivera', 'Trail of Bits', '9'),
        (10, 'Lisa Nguyen', 'Software engineer at Netflix', 'lisany', 'Netflix', '10'),
        (11, 'Chris Martin', 'CTO at Pinecone', 'chrismartin', 'Pinecone', '11'),
        (12, 'Dr. Kevin Foster', 'Founder of EvalHub', 'kevinfoster', 'EvalHub', '12'),
    ],
)

# ─── booths (20+ booths across 3 zones) ───────────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO booths (id, name, description, zone, grid_x, grid_y, topics) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [
        (1, 'NeuralForge', 'Open-source model training infrastructure for small teams', 'Hall A', 12, 8, 'training,distributed,open-source'),
        (2, 'PromptStack', 'Enterprise prompt management and versioning platform', 'Hall A', 25, 10, 'prompt-engineering,management,enterprise'),
        (3, 'VectorLabs', 'Vector database solutions for RAG applications', 'Hall A', 15, 20, 'vectordb,rag,search'),
        (4, 'AgentOS', 'Multi-agent orchestration framework', 'Hall B', 10, 15, 'agents,orchestration,multi-agent'),
        (5, 'LLM Ops Pro', 'MLOps tools for LLM deployment and monitoring', 'Hall B', 22, 5, 'mlops,monitoring,production'),
        (6, 'SecureLLM', 'Security tools for LLM applications', 'Hall B', 30, 18, 'security,adversarial,prompt-injection'),
        (7, 'ModelZen', 'LLM fine-tuning and evaluation platform', 'Hall C', 8, 12, 'fine-tuning,evaluation,ml'),
        (8, 'EdgeInference', 'Efficient inference for edge devices', 'Hall C', 18, 22, 'edge,inference,optimization'),
        (9, 'CodeCatalyst', 'AI-powered code generation and review', 'Hall A', 35, 12, 'code-generation,review,ide'),
        (10, 'DataFlow AI', 'LLM-based data pipeline automation', 'Hall A', 5, 18, 'data-pipelines,automation,etl'),
        (11, 'TalkToText', 'Speech-to-text and transcription API', 'Hall B', 15, 8, 'speech,text-to-speech,asr'),
        (12, 'VisualMind', 'Multimodal AI for image and text understanding', 'Hall B', 28, 15, 'multimodal,image,vision'),
        (13, 'LearnLocal', 'Offline AI learning for education', 'Hall C', 12, 25, 'education,offline,ai-assistant'),
        (14, 'FinGuard', 'LLM security for financial services', 'Hall A', 8, 5, 'finance,security,compliance'),
        (15, 'MedAI', 'Healthcare-grade LLM applications', 'Hall B', 20, 28, 'healthcare,medical, compliance'),
        (16, 'CodeStream', 'Real-time collaborative coding with AI', 'Hall C', 35, 8, 'collaboration,ide,real-time'),
        (17, 'AutoDoc', 'Automatic documentation generation', 'Hall A', 22, 22, 'documentation,generation,api'),
        (18, 'SentimentX', 'Advanced sentiment analysis for enterprises', 'Hall B', 8, 30, 'nlp,sentiment,analytics'),
        (19, 'TranslationNet', 'Real-time multilingual translation', 'Hall C', 25, 15, 'translation,multilingual,nlp'),
        (20, 'RiskAI', 'Risk assessment and mitigation for LLM deployments', 'Hall A', 32, 25, 'risk,assessment,compliance'),
        (21, 'NoteTaker AI', 'AI-powered meeting transcription and notes', 'Hall B', 15, 32, 'meetings,transcription,note-taking'),
        (22, 'QueryAI', 'Natural language to SQL and NoSQL queries', 'Hall C', 30, 22, 'query-generation,sql,database'),
    ],
)

conn.commit()
conn.close()

print(f"seeded {DB_PATH}")

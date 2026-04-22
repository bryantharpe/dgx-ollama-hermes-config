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
DB_PATH = os.path.join(DATA_DIR, "fair.db")
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

# Talks — 25 realistic talks across 4 days (June 29 – July 2)
INSERT OR IGNORE INTO talks (id, title, speaker_name, speaker_bio, speaker_github, start_time, end_time, room, description, tags, track) VALUES
(1, 'Scaling Local LLMs to Production', 'Dr. Alice Chen', 'Lead ML Engineer at Remote Labs', 'alicechen', '2025-06-29T09:00:00', '2025-06-29T10:00:00', 'Room A', 'Practical strategies for deploying open-source LLMs on-premise with minimal latency overhead.', 'llm,local-models,production', 'Architecture'),
(2, 'Building RAG Pipelines with Local Vector DBs', 'Bob Martinez', 'Principal Engineer at OpenAI Solutions', 'bobmz', '2025-06-29T10:30:00', '2025-06-29T11:30:00', 'Room A', 'Learn how to construct efficient retrieval-augmented generation pipelines using SQLite and Chroma.', 'rag,vector-dbs,pipelines', 'RAG'),
(3, 'Agent Orchestration with Local Controllers', 'Sarah Johnson', 'Founder of AgentFlow', 'sarahj', '2025-06-29T13:00:00', '2025-06-29T14:00:00', 'Room B', 'Design patterns for multi-agent systems that run entirely on your workstation.', 'agents,orchestration', 'Agents'),
(4, 'Fine-Tuning Mistral-7B on Custom corpora', 'David Kim', 'Research Scientist at TechLab', 'davidkim', '2025-06-29T14:30:00', '2025-06-29T15:30:00', 'Room B', 'Step-by-step guide to fine-tune open LLMs for specific domain tasks without cloud resources.', 'fine-tuning,llm,local-models', 'Modeling'),
(5, 'Real-Time RAG for Conference Apps', 'Emily Watson', 'CTO at SmartEvents', 'emilyw', '2025-06-29T16:00:00', '2025-06-29T17:00:00', 'Room A', 'Live demo of a RAG system serving thousands of attendees simultaneously.', 'rag,realtime,scalers', 'Architecture'),
(6, 'Building AI-Powered Code Assistants', 'Michael Brown', 'Senior Engineer at DevTools Inc', 'mikeb', '2025-06-30T09:00:00', '2025-06-30T10:00:00', 'Room A', 'Implementing local LLM-based IDE plugins with privacy-first architecture.', 'llm,agents,ide', 'Tools'),
(7, 'Vector DB Showdown: SQLite vs Chroma vs FAISS', 'Lisa Park', 'Database Architect at TechStack', 'lisap', '2025-06-30T10:30:00', '2025-06-30T11:30:00', 'Room A', 'Comprehensive benchmarks for offline vector search performance.', 'vector-dbs,benchmarks', 'Database'),
(8, 'Secure LLMs for Healthcare Applications', 'James Wilson', 'Data Officer at MedAI', 'jwilson', '2025-06-30T13:00:00', '2025-06-30T14:00:00', 'Room B', ' HIPAA-compliant local LLM deployments with zero data exfiltration.', 'llm,security,healthcare', 'Ethics'),
(9, 'LLM Prompt Engineering Patterns', 'Rachel Green', 'Prompt Engineer at CreativeAI', 'rachelfg', '2025-06-30T14:30:00', '2025-06-30T15:30:00', 'Room B', 'Battle-tested prompting techniques for consistent, reproducible outputs.', 'llm,.prompting', 'Best Practices'),
(10, 'Building Multi-Modal Agents', 'Chris Taylor', 'Researcher at VisionAI', 'chrisjt', '2025-06-30T16:00:00', '2025-06-30T17:00:00', 'Room A', 'Agents that process images, audio, and text in a single pipeline.', 'agents,multimodal', 'Agents'),
(11, 'Edge LLMs for IoT Devices', 'Priya Patel', 'Embedded AI Engineer at EdgeCore', 'priyap', '2025-07-01T09:00:00', '2025-07-01T10:00:00', 'Room A', 'Running quantized LLMs on Raspberry Pi and similar edge hardware.', 'local-models,edge,iot', 'Edge'),
(12, 'Open Source LLM Benchmarking Suite', 'Alex Rivera', 'Open Source Maintainer', 'arivera', '2025-07-01T10:30:00', '2025-07-01T11:30:00', 'Room A', 'How EvalHub helps developers pick the right model for their use case.', 'llm,evaluation,open-source', 'Tools'),
(13, 'Privacy-First Data Labeling with LLMs', 'Nina Santos', 'Product Manager at SecureAI', 'ninasa', '2025-07-01T13:00:00', '2025-07-01T14:00:00', 'Room B', 'Label training data locally without sending sensitive text to cloud APIs.', 'privacy,labeling,llm', 'Privacy'),
(14, 'Automated Prompt Evolution', 'Tom Anderson', 'Research Scientist at AutoPrompt', 'tomaa', '2025-07-01T14:30:00', '2025-07-01T15:30:00', 'Room B', 'Genetic algorithms for optimizing prompts over generations.', 'llm,optimization,agents', 'Research'),
(15, 'RAG for Technical Documentation', 'Karen White', 'Documentation Architect at TechBooks', 'karenw', '2025-07-01T16:00:00', '2025-07-01T17:00:00', 'Room A', 'Using RAG to power smart help systems for developer documentation.', 'rag,documentation,developer-experience', 'Applications'),
(16, 'Building Local Chatbots for Enterprises', 'Steve Harris', 'Solutions Architect at CorpAI', 'steveh', '2025-07-02T09:00:00', '2025-07-02T10:00:00', 'Room A', 'Deploy Slack-compatible chatbots that never leave your network.', 'agents,enterprise,chatbots', 'Applications'),
(17, 'LLM Fine-Tuning Without GPUs', 'Maria Garcia', 'Independent Researcher', 'mariag', '2025-07-02T10:30:00', '2025-07-02T11:30:00', 'Room A', 'Techniques for efficient training on CPU-only workstations.', 'fine-tuning,local-models,efficiency', 'Training'),
(18, 'Agent Framework Comparison: LangChain vs LlamaIndex vscrew', 'Patrick Lee', 'Architect at AIPlatform', 'plee', '2025-07-02T13:00:00', '2025-07-02T14:00:00', 'Room B', 'Comparing trade-offs for offline agent development.', 'agents,frameworks', 'Tools'),
(19, 'Building a Local AI Lab', 'Nicole Adams', 'AI Educator at University X', 'nadle', '2025-07-02T14:30:00', '2025-07-02T15:30:00', 'Room B', 'Curriculum and hardware recommendations for teaching AI on a budget.', 'education,local-models', 'Education'),
(20, 'RAG Evaluation Metrics You Can Trust', 'Omar Khan', 'Data Scientist at MLQuality', 'omark', '2025-06-29T11:00:00', '2025-06-29T12:00:00', 'Room B', 'Objective metrics for measuring RAG system performance offline.', 'rag,evaluation', 'RAG'),
(21, 'Quantization Strategies for Edge Deployment', 'Kevin Lee', 'Embedded Systems Engineer at Edge AI', 'kevinl', '2025-07-01T09:00:00', '2025-07-01T10:00:00', 'Room B', '8-bit, 4-bit, GPTQ vs AWQ — when to use each method.', 'quantization,edge,local-models', 'Edge'),
(22, 'Building AI Agents for Business Process Automation', 'Diana Prince', 'Consultant at DigitalTransform', 'dianap', '2025-07-02T15:00:00', '2025-07-02T16:00:00', 'Room A', 'Case studies from finance and legal verticals.', 'agents,automation,enterprise', 'Agents'),
(23, 'Open Vocabulary RAG with ColBERT', 'Richard Zhou', 'Researcher at SearchAI', 'richardz', '2025-06-30T15:00:00', '2025-06-30T16:00:00', 'Room B', 'Semantic search with fast, accurate late interaction models.', 'rag,colbert,semantic-search', 'RAG'),
(24, 'Dark Mode UI for AI Tools', 'Jessica Nguyen', 'UX Designer at DevTools', 'jessn', '2025-07-01T11:00:00', '2025-07-01T12:00:00', 'Room A', 'Designing IDE plugins and terminal UIs that reduce eye strain.', 'ui,design,developer-experience', 'UX'),
(25, 'AI Ethics in Local Deployment', 'Marcus Johnson', 'Ethicist at TechWatch', 'marcusj', '2025-07-02T16:30:00', '2025-07-02T17:30:00', 'Room B', 'Bias detection and mitigation when models stay on-premise.', 'ethics,local-models,biases', 'Ethics');

# Speakers — 18 speakers with GitHub handles
INSERT OR IGNORE INTO speakers (id, name, bio, github, talks_count) VALUES
(1, 'Dr. Alice Chen', 'Lead ML Engineer at Remote Labs, specializes in LLM deployment', 'alicechen', 1),
(2, 'Bob Martinez', 'Principal Engineer at OpenAI Solutions, RAG enthusiast', 'bobmz', 1),
(3, 'Sarah Johnson', 'Founder of AgentFlow, 10+ years in agent systems', 'sarahj', 1),
(4, 'David Kim', 'Research Scientist at TechLab, fine-tuning expert', 'davidkim', 1),
(5, 'Emily Watson', 'CTO at SmartEvents, real-time RAG specialist', 'emilyw', 1),
(6, 'Michael Brown', 'Senior Engineer at DevTools Inc, IDE tooling', 'mikeb', 1),
(7, 'Lisa Park', 'Database Architect at TechStack, vector DBs', 'lisap', 1),
(8, 'James Wilson', 'Data Officer at MedAI, healthcare AI compliance', 'jwilson', 1),
(9, 'Rachel Green', 'Prompt Engineer at CreativeAI, prompting patterns', 'rachelfg', 1),
(10, 'Chris Taylor', 'Researcher at VisionAI, multi-modal agents', 'chrisjt', 1),
(11, 'Priya Patel', 'Embedded AI Engineer at EdgeCore, IoT LLMs', 'priyap', 1),
(12, 'Alex Rivera', 'Open Source Maintainer, EvalHub creator', 'arivera', 1),
(13, 'Nina Santos', 'Product Manager at SecureAI, privacy advocate', 'ninasa', 1),
(14, 'Tom Anderson', 'Research Scientist at AutoPrompt, prompt optimization', 'tomaa', 1),
(15, 'Karen White', 'Documentation Architect at TechBooks, RAG for docs', 'karenw', 1),
(16, 'Steve Harris', 'Solutions Architect at CorpAI, enterprise chatbots', 'steveh', 1),
(17, 'Maria Garcia', 'Independent Researcher, CPU-only training', 'mariag', 1),
(18, 'Patrick Lee', 'Architect at AIPlatform, agent frameworks', 'plee', 1);

# Expo booths — 25 booths with grid coordinates
INSERT OR IGNORE INTO expo_booths (id, company_name, booth_number, description, tags, x, y, category) VALUES
(1, 'LocalAI Inc', 'A1', 'Open-source LLM deployment tools for enterprises', 'llm,open-source,deployment', 15, 20, 'infrastructure'),
(2, 'VectorDB Solutions', 'A2', 'SQLite-based vector search for offline applications', 'vector-dbs,sqlite,local', 25, 20, 'database'),
(3, 'AgentFlow', 'A3', 'Multi-agent orchestration framework', 'agents,orchestration,framework', 35, 20, 'tools'),
(4, 'PromptEngineer', 'A4', 'Prompt engineering tools and libraries', 'llm,prompting,tools', 45, 20, 'tools'),
(5, 'RAGWorks', 'A5', 'Enterprise RAG solutions', 'rag,enterprise,search', 55, 20, 'infrastructure'),
(6, 'EdgeAI Lab', 'A6', 'TinyML and edge LLM inference', 'edge,iot,tinyml,local-models', 65, 20, 'edge'),
(7, 'PrivacyFirst AI', 'A7', 'Federated learning and differential privacy', 'privacy,federated,security', 75, 20, 'security'),
(8, 'ModelQuant', 'A8', 'Quantization tools for efficient inference', 'quantization,efficiency,optimization', 85, 20, 'tools'),
(9, 'OpenCodebase', 'B1', 'Open-source AI developer tools', 'open-source,devtools,ide', 15, 40, 'tools'),
(10, 'SemanticSearch', 'B2', 'ColBERT and late interaction models', 'rag,colbert,semantic-search', 25, 40, 'infrastructure'),
(11, 'FineTuneKit', 'B3', 'Easy fine-tuning for local LLMs', 'fine-tuning,llm,training', 35, 40, 'tools'),
(12, 'MultiModal Systems', 'B4', 'Vision + language agents', 'multimodal,agents,vision', 45, 40, 'agents'),
(13, 'Cloudless AI', 'B5', 'Serverless local inference', 'serverless,local-models,inference', 55, 40, 'infrastructure'),
(14, 'DataLabeler', 'B6', 'Automated data labeling pipelines', 'labeling,training,efficiency', 65, 40, 'tools'),
(15, 'EvalHub', 'B7', 'LLM evaluation benchmarking suite', 'evaluation,benchmarks,llm', 75, 40, 'tools'),
(16, 'SecureLLM', 'B8', 'Enterprise-grade LLM security', 'security,compliance,enterprise', 85, 40, 'security'),
(17, 'DocuRAG', 'C1', 'RAG for technical documentation', 'rag,documentation,developer-experience', 15, 60, 'applications'),
(18, 'ChatBot Corp', 'C2', 'Enterprise chatbot framework', 'chatbots,enterprise,agents', 25, 60, 'applications'),
(19, 'AI Educators', 'C3', 'AI curriculum and training materials', 'education,training,curriculum', 35, 60, 'education'),
(20, 'Local Labs', 'C4', 'Research tools for local experimentation', 'research,local-models,tools', 45, 60, 'research'),
(21, 'PromptOptimize', 'C5', 'Automated prompt optimization', 'optimization,prompting,automation', 55, 60, 'tools'),
(22, 'VectorViz', 'C6', 'Vector database visualization tools', 'vector-dbs,visualization,ui', 65, 60, 'tools'),
(23, 'AI Ethics Now', 'C7', 'Bias detection and mitigation tools', 'ethics,biases,mitigation', 75, 60, 'ethics'),
(24, 'AgentMarket', 'C8', 'Pre-built AI agents marketplace', 'agents,marketplace,frameworks', 85, 60, 'marketplace'),
(25, 'AI in Healthcare', 'D1', 'HIPAA-compliant medical AI solutions', 'healthcare,compliance,security', 50, 80, 'verticals');

# Contacts — 3 sample contacts for testing
INSERT OR IGNORE INTO contacts (id, name, github, project, scanned_at, source_hash) VALUES
(1, 'John Doe', 'johndoe', 'Building RAG pipelines', '2025-06-30T10:00:00', 'hash123abc'),
(2, 'Jane Smith', 'janesmith', 'Local LLM deployment', '2025-06-30T11:00:00', 'hash456def'),
(3, 'Bob Wilson', 'bobwilson', 'Edge AI for IoT', '2025-06-30T12:00:00', 'hash789ghi');

conn.commit()
conn.close()

print(f"seeded {DB_PATH}")

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

# ─── seed speakers ───
cursor.executemany(
    "INSERT OR IGNORE INTO speakers (speaker_id, name, bio, github, twitter, company) VALUES (?, ?, ?, ?, ?, ?)",
    [
        ("1", "Alice Chen", "Principal ML Engineer at Meta, specializes in LLM fine-tuning and RAG systems", "alicechen", "alicechen_ai", "Meta"),
        ("2", "Bob Smith", "CTO at DataFlow, expert in MLOps and model deployment", "bobsmith", "bob_mlops", "DataFlow"),
        ("3", "Carol Johnson", "Research scientist at OpenAI, working on multimodal LLMs", "caroljohnson", "carol_ml", "OpenAI"),
        ("4", "David Lee", "Founder of AI Security Lab, focuses on LLM safety and alignment", "davidlee", "david_ai", "AI Security Lab"),
        ("5", "Emily Zhang", "Staff Engineer at Stripe, leads the AI integration team", "emilyzhang", "emily_codes", "Stripe"),
        ("6", "Frank Wilson", "Principal Engineer at AWS AI, building scalable ML infrastructure", "frankwilson", "frank_ml", "AWS"),
        ("7", "Grace Kim", "Data scientist at Netflix, works on recommendation systems", "gracekim", "grace_recsys", "Netflix"),
        ("8", "Henry Brown", "ML engineer at Coinbase, specializes in fraud detection", "henrybrown", "henry_ml", "Coinbase"),
        ("9", "Irene Martinez", "Founder of GenAI Solutions, helps enterprises adopt LLMs", "irene Martinez", "irene_ai", "GenAI Solutions"),
        ("10", "Jack Taylor", "Research engineer at Hugging Face, contributes to Transformers library", "jacktaylor", "jack_transformers", "Hugging Face"),
        ("11", "Karen White", "Senior ML engineer at Spotify, works on music recommendation", "karenwhite", "karen_ml", "Spotify"),
        ("12", "Leo Garcia", "Data engineer at Uber, builds data pipelines for ML", "leogarcia", "leo_data", "Uber"),
        ("13", "Maria Santos", "AI product manager at Google, leads Gemini integrations", "mariasantos", "marius_ai", "Google"),
        ("14", "Nick Peterson", "ML infrastructure engineer at Microsoft Azure", "nickpeterson", "nick_azure", "Microsoft"),
        ("15", "Olivia Turner", "Research scientist at DeepMind, works on reinforcement learning", "oliviaturner", "olivia_rl", "DeepMind"),
        ("16", "Peter Harris", "CTO at StartUp AI, building automated ML tools", "peterharris", "peter_automl", "StartUp AI"),
        ("17", "Quinn Williams", "Senior data scientist at Airbnb, works on search ranking", "quinnwilliams", "quinn_search", "Airbnb"),
        ("18", "Rachel Clark", "ML engineer at Airbnb, focuses on real-time features", "rachelclark", "rachel_ml", "Airbnb"),
        ("19", "Sam Robinson", "Principal engineer at Amazon SageMaker", "samrobinson", "sam_sagemaker", "Amazon"),
        ("20", "Tina Lopez", "Data engineer at Lyft, builds ML data pipelines", "tinalopez", "tina_data", "Lyft"),
    ],
)

# ─── seed talks ───
cursor.executemany(
    "INSERT OR IGNORE INTO talks (talk_id, title, abstract, speaker_id, start_time, end_time, room, track, tags, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [
        ("t1", "Building RAG Systems at Scale", "Learn how to build production-ready RAG systems with chunking strategies, embedding models, and retrievaloptimization.", "1", "2026-06-29T09:00:00", "2026-06-29T10:00:00", "Stage A", "Talk", '["rag", "llm", "search"]', "intermediate"),
        ("t2", "Fine-Tuning LLMs for Production", "A practical guide to fine-tuning large language models, including LoRA, quantization, and evaluation.", "1", "2026-06-29T11:00:00", "2026-06-29T12:00:00", "Stage A", "Talk", '["llm", "fine-tuning", "training"]', "advanced"),
        ("t3", "MLOps Pipeline Design Patterns", "Common patterns and anti-patterns in MLOps, from experiment tracking to model monitoring.", "2", "2026-06-29T14:00:00", "2026-06-29T15:00:00", "Stage B", "Workshop", '["mlops", "devops", "monitoring"]', "beginner"),
        ("t4", "Building Safe and Responsible LLMs", "Techniques for aligning LLMs, reducing hallucinations, and implementing safety filters.", "4", "2026-06-29T16:00:00", "2026-06-29T17:00:00", "Stage C", "Talk", '["safety", "alignment", "llm"]', "intermediate"),
        ("t5", "Real-Time Feature Engineering with Feast", "How to build real-time feature stores for machine learning applications.", "12", "2026-06-29T09:30:00", "2026-06-29T10:30:00", "Stage B", "Talk", '["feast", "features", "real-time"]', "intermediate"),
        ("t6", "Multimodal LLMs: Beyond Text", "Exploring multimodal foundations, vision-language models, and applications.", "3", "2026-06-29T11:30:00", "2026-06-29T12:30:00", "Stage A", "Talk", '["multimodal", "vision", "llm"]', "advanced"),
        ("t7", "LLM Routing and Orchestration", "Patterns for routing requests to the right model, from prompt routing to agent frameworks.", "1", "2026-06-29T15:00:00", "2026-06-29T16:00:00", "Stage A", "Talk", '["routing", "orchestration", "agents"]', "intermediate"),
        ("t8", "Data Engineering for ML", "Building data pipelines that feed machine learning models, from batch to streaming.", "12", "2026-06-30T09:00:00", "2026-06-30T10:00:00", "Stage B", "Talk", '["data", "pipelines", "etl"]', "beginner"),
        ("t9", "Building ML Products", "From ML ideas to shipped products: how to navigate the product development lifecycle.", "13", "2026-06-30T11:00:00", "2026-06-30T12:00:00", "Stage C", "Talk", '["product", "strategy", "ml"]', "beginner"),
        ("t10", "Security in AI Systems", "Threat modeling for AI systems, prompt injection, and data privacy.", "4", "2026-06-30T14:00:00", "2026-06-30T15:00:00", "Stage C", "Talk", '["security", "privacy", "llm"]', "intermediate"),
        ("t11", "Recommendation Systems in Production", "Case studies from Netflix, Spotify, and Airbnb on building recommendation systems.", "7", "2026-06-30T16:00:00", "2026-06-30T17:00:00", "Stage A", "Talk", '["recommendation", "nlp", "search"]', "intermediate"),
        ("t12", "Fine-Tuning for Code Generation", "Specialized techniques for fine-tuning LLMs for programming tasks.", "10", "2026-06-30T09:30:00", "2026-06-30T10:30:00", "Stage B", "Talk", '["code", "llm", "fine-tuning"]', "advanced"),
        ("t13", "Scalable Model Serving with Triton", "How to serve ML models at scale using NVIDIA Triton Inference Server.", "6", "2026-06-30T11:30:00", "2026-06-30T12:30:00", "Stage B", "Talk", '["serving", "triton", "performance"]', "intermediate"),
        ("t14", "Building AI Agents", "Architectures for autonomous agents, tool use, and planning.", "19", "2026-06-30T15:00:00", "2026-06-30T16:00:00", "Stage A", "Talk", '["agents", "routing", "orchestration"]', "advanced"),
        ("t15", "Prompt Engineering Best Practices", "Patterns and antipatterns for prompting LLMs effectively.", "9", "2026-07-01T09:00:00", "2026-07-01T10:00:00", "Stage C", "Workshop", '["prompting", "llm", "engineering"]', "beginner"),
        ("t16", "Vector Databases Comparison", "Pinecone, Weaviate, Milvus, and Chroma: pros, cons, and use cases.", "5", "2026-07-01T11:00:00", "2026-07-01T12:00:00", "Stage A", "Talk", '["vector", "database", "search"]', "intermediate"),
        ("t17", "Quantization and Compression", "Model compression techniques: quantization, pruning, and distillation.", "8", "2026-07-01T14:00:00", "2026-07-01T15:00:00", "Stage B", "Talk", '["quantization", "compression", "performance"]', "advanced"),
        ("t18", "Building AI Startups", "Lessons from founding and scaling an AI startup.", "16", "2026-07-01T16:00:00", "2026-07-01T17:00:00", "Stage C", "Talk", '["startup", "business", "strategy"]', "beginner"),
        ("t19", "LLM Evaluation Frameworks", "How to evaluate LLM outputs: metrics, benchmarks, and human evaluation.", "14", "2026-07-01T09:30:00", "2026-07-01T10:30:00", "Stage B", "Talk", '["evaluation", "metrics", "llm"]', "intermediate"),
        ("t20", "Generative AI in Finance", "Use cases and challenges of generative AI in financial services.", "11", "2026-07-01T11:30:00", "2026-07-01T12:30:00", "Stage A", "Talk", '["finance", "genai", "use-case"]', "intermediate"),
        ("t21", "AutoML: From Theory to Practice", "Automated ML: hyperparameter tuning, feature selection, and neural architecture search.", "16", "2026-07-01T15:00:00", "2026-07-01T16:00:00", "Stage B", "Talk", '["automl", "hyperopt", "feature"]', "advanced"),
        ("t22", "Privacy-Preserving ML", "Federated learning, differential privacy, and secure multi-party computation.", "15", "2026-07-01T17:00:00", "2026-07-01T18:00:00", "Stage C", "Talk", '["privacy", "federated", "secure"]', "advanced"),
        ("t23", "Building ML APIs", "REST and GraphQL patterns for exposing ML models as services.", "5", "2026-07-02T09:00:00", "2026-07-02T10:00:00", "Stage A", "Talk", '["api", "rest", "graphql"]', "beginner"),
        ("t24", "Debugging ML Models", "Systematic approaches to debugging model predictions and performance issues.", "20", "2026-07-02T11:00:00", "2026-07-02T12:00:00", "Stage B", "Workshop", '["debugging", "analysis", "monitoring"]', "intermediate"),
        ("t25", "LLM Fine-Tuning on a Budget", "Cost-effective techniques for fine-tuning without expensive infrastructure.", "17", "2026-07-02T14:00:00", "2026-07-02T15:00:00", "Stage B", "Talk", '["fine-tuning", "cost", "optimization"]', "intermediate"),
        ("t26", "AI in Cybersecurity", "Using ML for threat detection, anomaly detection, and incident response.", "18", "2026-07-02T16:00:00", "2026-07-02T17:00:00", "Stage C", "Talk", '["security", "anomaly", "ml"]', "intermediate"),
        ("t27", "Model Registry Best Practices", "How to manage ML model versions, lineage, and deployment gates.", "6", "2026-07-02T09:30:00", "2026-07-02T10:30:00", "Stage B", "Talk", '["registry", "mlops", "versioning"]', "beginner"),
        ("t28", "Building AI Assistants", "Building conversational AI assistants with RAG and agent frameworks.", "9", "2026-07-02T11:30:00", "2026-07-02T12:30:00", "Stage A", "Talk", '["assistant", "rag", "agents"]', "intermediate"),
        ("t29", "Edge ML for Mobile", "Deploying machine learning models on mobile and edge devices.", "10", "2026-07-02T15:00:00", "2026-07-02T16:00:00", "Stage B", "Talk", '["edge", "mobile", "deployment"]', "advanced"),
        ("t30", "Future of AI Engineering", "Panel discussion on the evolving role of AI engineers.", "1", "2026-07-02T17:00:00", "2026-07-02T18:30:00", "Stage A", "Panel", '["career", "community", "future"]', "beginner"),
    ],
)

# ─── seed booths ───
cursor.executemany(
    "INSERT OR IGNORE INTO booths (booth_id, name, category, grid_x, grid_y, description, website) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [
        ("b1", "AWS AI", "Infrastructure", "2", "3", "AWS Machine Learning services including SageMaker, Bedrock, and Lambda", "https://aws.amazon.com"),
        ("b2", "Google Cloud AI", "Infrastructure", "2", "7", "Vertex AI, Gemini models, and cloud ML infrastructure", "https://cloud.google.com/ai"),
        ("b3", "Microsoft Azure ML", "Infrastructure", "2", "11", "Azure Machine Learning, Copilot, and AI models", "https://azure.microsoft.com"),
        ("b4", "NVIDIA", "Infrastructure", "5", "3", "GPU acceleration for AI training and inference, Triton", "https://www.nvidia.com"),
        ("b5", "Hugging Face", "Data", "5", "7", "Open source ML models, datasets, and the Transformers library", "https://huggingface.co"),
        ("b6", "Snowflake", "Data", "5", "11", "Cloud data platform with AI/ML capabilities", "https://www.snowflake.com"),
        ("b7", "Databricks", "Data", "8", "3", "Lakehouse platform for data engineering and ML", "https://www.databricks.com"),
        ("b8", "MongoDB", "Data", "8", "7", "Vector search and AI-powered data solutions", "https://www.mongodb.com"),
        ("b9", "Weaviate", "Data", "8", "11", "Open source vector database for AI applications", "https://weaviate.io"),
        ("b10", "Chroma", "Data", "11", "3", "Open source vector database for LLM applications", "https://www.trychroma.com"),
        ("b11", "Pinecone", "Data", "11", "7", "Managed vector database for AI workloads", "https://www.pinecone.io"),
        ("b12", "Milvus", "Data", "11", "11", "Open source vector database at scale", "https://milvus.io"),
        ("b13", "Mlflow", "ML Ops", "14", "3", "Open source ML lifecycle platform", "https://www.mlflow.org"),
        ("b14", "Weights & Biases", "ML Ops", "14", "7", "Experiment tracking, model monitoring, and collaboration", "https://wandb.ai"),
        ("b15", "Arize", "ML Ops", "14", "11", "ML observability and monitoring platform", "https://arize.com"),
        ("b16", "DataRobot", "ML Ops", "17", "3", "Automated ML and MLOps platform", "https://www.datarobot.com"),
        ("b17", "Databricks", "ML Ops", "17", "7", "Enterprise MLOps and Lakehouse platform", "https://databricks.com"),
        ("b18", "Hugging Face", "Generative AI", "17", "11", "LLMs, RAG, and generative AI tools", "https://huggingface.co"),
        ("b19", "Anthropic", "Generative AI", "20", "3", "Safe and reliable AI systems, Claude model", "https://www.anthropic.com"),
        ("b20", "OpenAI", "Generative AI", "20", "7", "Large language models and AI research", "https://openai.com"),
        ("b21", "Cohere", "Generative AI", "20", "11", "Foundation models and generative AI API", "https://cohere.ai"),
    ],
)

# ─── seed bookmarks (demo data) ───
cursor.executemany(
    "INSERT OR IGNORE INTO user_bookmarks (talk_id, type, entity_id) VALUES (?, ?, ?)",
    [
        (1, "talk", "t1"),
        (3, "talk", "t3"),
        (1, "speaker", "1"),
        (2, "booth", "b1"),
    ],
)

conn.commit()
conn.close()

print(f"seeded {DB_PATH}")

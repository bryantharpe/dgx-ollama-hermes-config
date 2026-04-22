#!/usr/bin/env python3
"""Idempotent database bootstrap. Runs at container startup."""

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

# ─── speakers ────────────────────────────────────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO speakers (id, name, bio, company, github, twitter) VALUES (?, ?, ?, ?, ?, ?)",
    [
        (1, "Sarah Chen", "Principal ML engineer specializing in LLM orchestration", "AI Nexus", "sarahchen", "sarahchen_ai"),
        (2, "Marcus Johnson", "Founder of LocalLLM Lab, researcher in model quantization", "LocalLLM Lab", "marcusj", "marcusj_research"),
        (3, "Elena Rodriguez", "Senior ML engineer at TechCorp, focuses on MLOps pipelines", "TechCorp", "elena_r", "elena_mlops"),
        (4, "David Kim", "PhD candidate researching RAG architectures for enterprise search", "Stanford AI", "davidkim", "dkim_nlp"),
        (5, "Priya Patel", "CTO at DataFlow AI, expert in distributed training", "DataFlow AI", "priyapatel", "priyadataflow"),
        (6, "Alex Thompson", "Staff engineer at ModelScale, works on inference optimization", "ModelScale", "alexthompson", "alex_inference"),
        (7, "Maria Garcia", "Research scientist at OpenModels, focuses on fine-tuning techniques", "OpenModels", "mariag", "mariag_research"),
        (8, "James Wilson", "Senior data engineer building ML data pipelines", "DataTech", "jwilson", "jwilson_data"),
        (9, "Linda Martinez", "ML platform engineer at CloudAI", "CloudAI", "lindam", "linda_mlplatform"),
        (10, "Robert Taylor", "AI architect designing scalable LLM systems", "ScaleAI", "rtaylor", "rtaylor_ai"),
        (11, "Nancy Lee", "Product manager for AI developer tools at DevTools Inc", "DevTools Inc", "nancylee", "nancy_ai"),
        (12, "Michael Brown", "ML engineer specializing in computer vision", "VisionAI", "mbrown", "mbrown_cv"),
        (13, "Jessica Davis", "Data scientist at FinanceAI, works on risk modeling", "FinanceAI", "jdavis", "jdavis_risk"),
        (14, "Christopher Martinez", "Research engineer atPromptLab, works on prompting techniques", "PromptLab", "cmartinez", "cmartinez_prompt"),
        (15, "Amanda White", "DevOps engineer at CloudNative, specializes in ML infrastructure", "CloudNative", "awhite", "awhite_devops"),
    ],
)

# ─── talks (36 talks across 4 days) ───────────────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO talks (id, title, speaker_id, day, start_time, end_time, room, description, tags, track) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [
        # Day 1
        (1, "Introduction to Local LLMs", 2, "Day 1", "09:00", "10:00", "Stage A", "A comprehensive introduction to running LLMs locally, including quantization techniques and hardware requirements.", "local-llm,quantization,hardware", "Foundations"),
        (2, "RAG Architectures Explained", 4, "Day 1", "10:30", "11:30", "Stage A", "Deep dive into Retrieval-Augmented Generation architectures for enterprise knowledge systems.", "rag,enterprise,knowledge-graph", "RAG"),
        (3, "Prompt Engineering Best Practices", 14, "Day 1", "11:30", "12:30", "Stage B", "Learn proven patterns for effective prompting across different LLM families.", "prompting,engineering", "Applications"),
        (4, "Building MLOps Pipelines", 3, "Day 1", "13:00", "14:00", "Stage A", "Designing robust MLOps pipelines for model deployment and monitoring.", "mlops,deployment,monitoring", "MLOps"),
        (5, "Model Quantization Strategies", 2, "Day 1", "14:00", "15:00", "Stage B", "Comparing GPTQ, GGUF, and other quantization approaches for efficient inference.", "quantization,inference,efficiency", "Foundations"),
        (6, "Fine-Tuning LLMs on YOUR Data", 7, "Day 1", "15:30", "16:30", "Stage A", "Hands-on guide to fine-tuning large language models with your proprietary data.", "fine-tuning,customization", "Applications"),
        (7, "Distributed Training at Scale", 5, "Day 1", "16:30", "17:30", "Stage B", "Scaling training across multiple GPUs and nodes using modern frameworks.", "distributed,training,scale", "MLOps"),
        (8, "LLM Orchestration Patterns", 1, "Day 1", "17:30", "18:30", "Stage A", "Design patterns for orchestrating multiple LLMs in production workflows.", "orchestration,architecture", "Applications"),
        # Day 2
        (9, "Vector Databases compared", 4, "Day 2", "09:00", "10:00", "Stage A", "Analyzingpinecone, and Qdrant for RAG implementations.", "vector-db,rag,pinecone", "RAG"),
        (10, "Inference Optimization Techniques", 6, "Day 2", "10:30", "11:30", "Stage B", "Speeding up LLM inference with caching, batching, and model pruning.", "inference,optimization,speed", "Foundations"),
        (11, "Edge AI with Small Models", 12, "Day 2", "11:30", "12:30", "Stage A", "Deploying efficient AI models on edge devices and mobile platforms.", "edge,small-models,mobile", "Applications"),
        (12, "Secure AI with Differential Privacy", 15, "Day 2", "13:00", "14:00", "Stage B", "Protecting sensitive data during model training and inference.", "privacy,security,differential-privacy", "Security"),
        (13, "Multi-Modal RAG Systems", 1, "Day 2", "14:00", "15:00", "Stage A", "Extending RAG to handle text, images, and structured data.", "rag,multi-modal,vision", "RAG"),
        (14, "AI Agent Architectures", 10, "Day 2", "15:30", "16:30", "Stage B", "Building autonomous AI agents with memory and planning capabilities.", "agents,orchestration,planning", "Applications"),
        (15, "Continuous Integration for ML", 8, "Day 2", "16:30", "17:30", "Stage A", "Automated testing and validation of ML pipelines in CI/CD workflows.", "mlops,ci-cd,testing", "MLOps"),
        (16, "LLM Fine-Tuning on a Budget", 7, "Day 2", "17:30", "18:30", "Stage B", "Cost-effective approaches to fine-tuning LLMs with limited computational resources.", "fine-tuning,cost-efficiency", "Applications"),
        # Day 3
        (17, "Building AI Search Engines", 4, "Day 3", "09:00", "10:00", "Stage A", "Creating semantic search experiences with RAG and modern embeddings.", "search,rag,embeddings", "RAG"),
        (18, "LLM Security Best Practices", 9, "Day 3", "10:30", "11:30", "Stage B", "Protecting LLM applications from prompt injection and data leaks.", "security,prompt-injection", "Security"),
        (19, "Scaling Vector Store Performance", 4, "Day 3", "11:30", "12:30", "Stage A", "Optimizing vector database queries for sub-second RAG responses.", "vector-db,performance,optimization", "RAG"),
        (20, "Model Serving Architectures", 6, "Day 3", "13:00", "14:00", "Stage B", "Design patterns for serving LLMs in production, from batch to streaming.", "serving,production,inference", "MLOps"),
        (21, "RAG Evaluation Frameworks", 1, "Day 3", "14:00", "15:00", "Stage A", "Measuring and improving RAG system quality with automated evaluation.", "rag,evaluation,metrics", "RAG"),
        (22, "Fine-Tuning with LoRA", 7, "Day 3", "15:30", "16:30", "Stage B", "Efficient fine-tuning using Low-Rank Adaptation techniques.", "fine-tuning,lora,adaptation", "Applications"),
        (23, "Distributed RAG Systems", 10, "Day 3", "16:30", "17:30", "Stage A", "Building RAG systems that span multiple data centers and regions.", "rag,distributed,scaling", "RAG"),
        (24, "AI-Powered Developer Tools", 11, "Day 3", "17:30", "18:30", "Stage B", "How AI is transforming IDEs, code completion, and debugging.", "ai-tools,devtools,ide", "Applications"),
        # Day 4
        (25, "Quantized LLM Deployment", 2, "Day 4", "09:00", "10:00", "Stage A", "Production deployment strategies for GGUF and GPTQ quantized models.", "quantization,deployment,gguf", "Foundations"),
        (26, "RAG with Graph Databases", 4, "Day 4", "10:30", "11:30", "Stage B", "Combining knowledge graphs with RAG for intelligent information retrieval.", "rag,knowledge-graph,graphs", "RAG"),
        (27, "LLM Fine-Tuning Hardware", 15, "Day 4", "11:30", "12:30", "Stage A", "Choosing the right hardware for efficient model training and fine-tuning.", "hardware,training,hardware-selection", "Foundations"),
        (28, "Building AI Assistants", 10, "Day 4", "13:00", "14:00", "Stage B", "Creating intelligent assistants with context awareness and memory.", "assistants,agents,conversation", "Applications"),
        (29, "MLOps for RAG Systems", 3, "Day 4", "14:00", "15:00", "Stage A", "Monitoring, alerting, and versioning for RAG production systems.", "mlops,rag,monitoring", "MLOps"),
        (30, "Ethical Considerations in AI", 13, "Day 4", "15:30", "16:30", "Stage B", "Bias detection, fairness, and responsible AI deployment practices.", "ethics,bias,fairness", "Foundations"),
        (31, "Real-Time RAG Applications", 1, "Day 4", "16:30", "17:30", "Stage A", "Building low-latency RAG systems for interactive applications.", "rag,real-time,latency", "RAG"),
        (32, "Open Source LLMs Roundtable", 2, "Day 4", "17:30", "18:30", "Stage B", "Community discussion on the state and future of open_source LLMs.", "open-source,community,llms", "Foundations"),
        (33, "Fine-Tuning for Code Generation", 11, "Day 4", "09:00", "10:00", "Stage C", "Specialized fine-tuning strategies for coding assistant models.", "code-generation,fine-tuning,programming", "Applications"),
        (34, "RAG for Enterprise Search", 4, "Day 4", "10:30", "11:30", "Stage C", "Implementing RAG in large enterprise search systems.", "enterprise,search,rag", "RAG"),
        (35, "Agent-Based Simulation", 10, "Day 4", "11:30", "12:30", "Stage C", "Using AI agents for complex system simulation and modeling.", "agents,simulation,complex-systems", "Applications"),
        (36, "Future of AI Developer Tools", 11, "Day 4", "13:00", "14:00", "Stage C", "Vision for next-generation AI-powered development environments.", "ai-tools,devtools,future", "Applications"),
    ],
)

# ─── expo_booths (24 booths across 2 halls) ──────────────────────────────────
cursor.executemany(
    "INSERT OR IGNORE INTO expo_booths (id, company_name, description, tags, grid_x, grid_y, hall, booth_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (1, "AI Nexus", "Enterprise AI solutions and custom model development", "enterprise,consulting,custom-models", 10.0, 10.0, "Hall A", "A-101"),
        (2, "LocalLLM Lab", "Tools for running LLMs on local hardware", "local-llm,quantization,deployment", 15.0, 10.0, "Hall A", "A-102"),
        (3, "TechCorp AI", "Machine learning platforms for large organizations", "mlops,platform,enterprise", 20.0, 10.0, "Hall A", "A-103"),
        (4, "DataFlow AI", "Scalable AI infrastructure and training pipeline", "distributed,training,scale", 25.0, 10.0, "Hall A", "A-104"),
        (5, "ModelScale", "High-performance LLM inference serving", "inference,optimization,serving", 30.0, 10.0, "Hall A", "A-105"),
        (6, "OpenModels", "Open-source LLMs and fine-tuning tools", "open-source,foundational-models,fine-tuning", 35.0, 10.0, "Hall A", "A-106"),
        (7, "VisionAI", "Computer vision solutions for manufacturing and healthcare", "cv,industrial,healthcare", 10.0, 15.0, "Hall A", "A-201"),
        (8, "FinanceAI", "Risk modeling and algorithmic trading solutions", "finance,risk,trading", 15.0, 15.0, "Hall A", "A-202"),
        (9, "CloudAI", "Cloud-native ML platform and managed services", "cloud,managed-service,kubernetes", 20.0, 15.0, "Hall A", "A-203"),
        (10, "ScaleAI", "AI infrastructure and scaling solutions", "infrastructure,scale,distributed", 25.0, 15.0, "Hall A", "A-204"),
        (11, "DevTools Inc", "AI-powered developer tools and IDE plugins", "devtools,ide,developer-productivity", 30.0, 15.0, "Hall A", "A-205"),
        (12, "PromptLab", "Prompt engineering tools and LLM APIs", "prompting,apis,tools", 35.0, 15.0, "Hall A", "A-206"),
        (13, "AI Security", "LLM security and prompt injection protection", "security,privacy,prompt-injection", 40.0, 10.0, "Hall A", "A-301"),
        (14, "VectorDB Solutions", "Managed vector database services", "vector-db,pinecone,qdrant", 45.0, 10.0, "Hall A", "A-302"),
        (15, "Edge AI Co", "AI on edge devices and embedded systems", "edge,embedded,microcontrollers", 50.0, 10.0, "Hall A", "A-303"),
        (16, "AI Ethics Institute", "AI fairness, bias detection, and responsible AI", "ethics,bias,responsible-ai", 55.0, 10.0, "Hall A", "A-304"),
        (17, "RAG Technologies", "Retrieval-Augmented Generation solutions", "rag,enterprise-search,knowledge-graph", 10.0, 20.0, "Hall A", "A-401"),
        (18, "ML Platform Systems", "End-to-end ML platform for data teams", "mlops,platform,data-team", 15.0, 20.0, "Hall A", "A-402"),
        (19, "AI Analytics Corp", "AI-powered analytics and business intelligence", "analytics,bi,decision-support", 20.0, 20.0, "Hall A", "A-403"),
        (20, "Semantic Search Inc", "Semantic search and document understanding", "search,semantic,nlp", 25.0, 20.0, "Hall A", "A-404"),
        (21, "AI Training Services", "Custom AI model training and fine-tuning", "training,fine-tuning,consulting", 30.0, 20.0, "Hall A", "A-405"),
        (22, "AI Consulting Group", "AI strategy and implementation consulting", "consulting,strategy,implementation", 35.0, 20.0, "Hall A", "A-406"),
        (23, "AI Hardware Lab", "Specialized AI hardware and accelerators", "hardware,accelerators,gpu", 40.0, 20.0, "Hall B", "B-101"),
        (24, "AI Automation", "AI-powered workflow automation solutions", "automation,workflow,enterprise", 45.0, 20.0, "Hall B", "B-102"),
    ],
)

conn.commit()
conn.close()

print(f"seeded {DB_PATH}")

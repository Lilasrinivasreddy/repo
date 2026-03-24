┌──────────────────────────────────────────────┐
│ 👤 USER / ENGINEER (VS CODE)                │
│ - Copilot Chat                              │
│ - JSON / Confluence Input                   │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 📥 INPUT / CONTEXT LAYER                     │
│----------------------------------------------│
│ ✔ Confluence (manual / MCP fetch)            │
│ ✔ Source-to-target mapping                   │
│ ✔ JSON templates                            │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 🧠 AI ORCHESTRATION LAYER (COPILOT AGENTS)  │
│----------------------------------------------│
│ ⭐ Root Orchestrator Agent                   │
│   → Understand request                      │
│   → Validate input                          │
│   → Decide flow                             │
│                                             │
│ ⭐ Sub Agents                               │
│   → Table Agent (SQL)                       │
│   → SA Agent (IAM)                          │
│   → Bucket Agent (GCS)                      │
│   → Terraform Agent (IaC)                   │
│   → Git Agent (PR content)                  │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 📘 RULES / CONFIG LAYER                     │
│----------------------------------------------│
│ ✔ Naming conventions                        │
│ ✔ Table standards                           │
│ ✔ IAM policies                              │
│ ✔ Terraform templates                       │
│ ✔ PR templates                              │
│ ❗ NOT inside agent                          │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 🛠 MCP EXECUTION LAYER (OPTIONAL)           │
│----------------------------------------------│
│ ✔ GitHub → create branch / PR               │
│ ✔ Confluence → fetch data                  │
│ ✔ Terraform → plan/apply                   │
│ ✔ BigQuery → run validation                │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 🌐 EXTERNAL SYSTEMS                         │
│----------------------------------------------│
│ ✔ GitHub Repo                              │
│ ✔ GCP (BQ / IAM / GCS)                     │
│ ✔ Terraform                                │
│ ✔ Confluence                               │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│ 👤 HUMAN REVIEW & GOVERNANCE               │
│----------------------------------------------│
│ ✔ Review SQL / Terraform                   │
│ ✔ Approve PR                              │
│ ✔ Merge                                   │
└──────────────────────────────────────────────┘
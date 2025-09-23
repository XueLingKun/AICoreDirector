# AICoreDirector — Enterprise AI Governance & Orchestration Platform

English | 中文: [README_zh-CN.md](README_zh-CN.md)

[![CI](https://github.com/AICoreDirector/AICoreDirector/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

AICoreDirector is an enterprise AI governance platform that unifies all LLM calls, AI components, and traditional ML services behind a single interface. It provides intelligent routing and scheduling, fallback, and integrated management—serving as the enterprise AI capability bus and central hub for production.

### Core Value Proposition
- Enterprise AI governance: centralized management of all AI capabilities and models
- LLM orchestration platform: intelligent routing and load balancing across multiple models
- AI service mesh: unified API gateway for AI/ML services with governance
- Plugin ecosystem: extensible architecture for custom AI capabilities

---

## Features

- Unified multi-model management: register, switch, persist, and extend LLMs and classic ML models
- Intelligent routing & scheduling: choose the best model by tags, business level, health, QPS, and cost
- Pluggable architecture & hot-reload: auto registration and hot-swap for business/model plugins
- Rich APIs: invoke AI services, manage models, query monitoring data with consistent contracts
- Health checks & elastic on/off: periodic checks and automatic failover for high availability
- QPS & hit-rate monitoring: real-time metrics for traffic governance and capacity planning
- Cost & token usage: per-call token and cost accounting with multi-dimensional aggregation
- Service registry & heartbeat: external services can register, report health, and be governed

---

## Architecture

```
Frontend (Vue.js)  <->  API (FastAPI)  <->  Core (Python)
                           |                 |
                           v                 v
                   Service Registry      Plugin System
```

Key modules:
- API Layer: RESTful endpoints, validation, routing, exception handling
- Business Layer: model selection, session, prompt handling
- LLM Pool: unified model registry and metadata with dynamic expansion
- Smart Routing: cost/latency/health-aware selection and failover
- Health & QPS Monitoring: real-time metrics and dashboards
- Plugin System: hot-pluggable functions and external services
- Prompt Center: centralized prompt templates and best practices

---

## Project Structure

```
AICoreDirector/
├── api/                # FastAPI endpoints
├── core/               # Core engine: routing, health, stats, prompts
├── business/           # Business plugins
├── adapters/           # LLM adapters and context
├── frontend/           # Vue.js frontend
├── config_prompts/     # Prompt templates
├── docs/               # Documentation & assets
├── scripts/            # Utilities and scripts
├── tests/              # Test stubs
└── llm_models.yaml     # Model pool config
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+

### Backend Setup
```bash
pip install -r requirements.txt

# Development
uvicorn api.main:app --reload

# Production (recommended)
uvicorn api.main:app --host 0.0.0.0 --port 8000 \
  --workers 4 --log-config log_config.json
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Configure Models
Edit `llm_models.yaml` to add providers (name, url, key, tags, qps, cost...).

---

## Key APIs

- `POST /llm_invoke` — LLM inference (supports `stream=true`)
- `POST /manage_LLM` — add/update/delete LLM/ML models (syncs to `llm_models.yaml`)
- `POST /list_LLM` — list all LLMs with metadata
- `GET  /service-discovery/list` — registered services and plugin abilities
- `GET  /plugin/list` — list registered plugins
- `POST /plugin/invoke?plugin_name=...` — unified plugin entry (batch supported)
- `GET  /get_model_health` — model health/status
- `GET  /get_model_qps` — per-model QPS
- `GET  /get_model_hit_count` — selection hit counts
- `GET  /get_model_cost` — aggregate model cost

OpenAPI docs available at `/docs` and `/openapi.json` when the server is running.

---

## Monitoring & Logging
- Structured JSON logs via `log_config.json`
- Logs include API requests, routing decisions, errors, latency, costs
- Production tips: rotate logs, set INFO level, integrate with ELK/Prometheus/Grafana

---

## Development
- Clean plugin guidelines with `@plugin_api` decorator
- Hot-reload plugin discovery and prioritized routing
- Centralized PromptManager for template loading and reuse
- Batch and streaming processing utilities

---

## Contributing
We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

Steps:
1. Fork the repository
2. Create a feature branch
3. Make changes with tests/docs
4. Submit a pull request

---

## License
MIT License — see [LICENSE](LICENSE).

---

## Discoverability (Topics)

This project is tagged with the following topics to improve discoverability:

```
ai, ml, machine-learning, llm, large-language-model,
ai-platform, ai-governance, ai-orchestration, ai-integration,
llm-gateway, microservices, service-mesh,
plugin-system, plugins, fastapi, python
```

Repository About:
- Description: AICoreDirector is an enterprise AI governance platform that unifies all LLM calls, AI components, and traditional ML services behind a single interface. It provides intelligent routing and scheduling, fallback, and integrated management—serving as the enterprise AI capability bus and central hub for production.
- Website: https://aicoredirector.github.io

---

## Links
- Organization: https://github.com/AICoreDirector
- Main Repository: https://github.com/AICoreDirector/AICoreDirector
- Usage Guide: [USAGE.md](USAGE.md)

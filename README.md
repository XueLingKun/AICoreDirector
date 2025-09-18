# AICoreDirector - Enterprise AI Governance & Orchestration Platform

[中文 README](README_zh-CN.md) | English

[![CI](https://github.com/AICoreDirector/AICoreDirector/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

**AICoreDirector** is an enterprise-grade **AI governance platform** that provides unified **LLM management**, intelligent routing, and multi-modal **AI capability integration**. It serves as a centralized **AI hub** for enterprise services, enabling efficient resource allocation, intelligent service discovery, and comprehensive **AI governance**.

### 🚀 **Core Value Proposition**
- **Enterprise AI Governance**: Centralized management of all AI capabilities and models
- **LLM Orchestration Platform**: Intelligent routing and load balancing across multiple models
- **AI Service Mesh**: Unified API gateway for all AI/ML services
- **Plugin Ecosystem**: Extensible architecture for custom AI capabilities

## Features

### 🚀 **Core Capabilities**
- **Multi-LLM Management**: Unified management of multiple LLM models with intelligent routing
- **AI Service Discovery**: Dynamic service registration and health monitoring for all AI/ML services
- **Plugin System**: Extensible plugin architecture for custom AI capabilities and business logic
- **Prompt Management**: Centralized prompt configuration with version control and best practices
- **Real-time Monitoring**: Live dashboard for LLM health, QPS, cost tracking, and AI governance metrics

### 🔧 **Technical Features**
- **Intelligent Routing**: AI-powered model selection based on cost, performance, and business requirements
- **AI Health Monitoring**: Automatic health checks and failover mechanisms for all AI services
- **Cost Optimization**: Smart cost management and resource allocation across multiple AI models
- **AI API Gateway**: Unified API interface with authentication, rate limiting, and AI service orchestration
- **Multi-language Support**: Internationalization support (Chinese/English) for global enterprise deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Core Engine   │
│   (Vue.js)      │◄──►│   (FastAPI)     │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Service Registry│    │ Plugin System   │
                       │ & Discovery     │    │ & Extensions    │
                       └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/AICoreDirector.git
   cd AICoreDirector
   ```

2. **Backend setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure LLM models
   cp llm_models.yaml.example llm_models.yaml
   # Edit llm_models.yaml with your API keys and endpoints
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Start the backend**
   ```bash
   # From project root
   python main.py
   ```

### Configuration

1. **LLM Models**: Edit `llm_models.yaml` to add your LLM providers
2. **Environment Variables**: Set API keys in `.env` file
3. **Service Registry**: Configure service endpoints in `service_registry.json`

## Usage

### API Endpoints

- **LLM Management**: `/api/llm/*` - Add, update, delete LLM models
- **Service Discovery**: `/service-discovery/*` - Service registration and discovery
- **Plugin System**: `/plugin/*` - Custom AI capability plugins
- **Prompt Management**: `/api/prompts/*` - Prompt file operations

### Frontend Features

- **Dashboard**: Real-time monitoring of LLM health and performance
- **LLM Config**: Model configuration and testing interface
- **Service Discovery**: Service registry management
- **Prompt Manager**: Prompt file editing with version control
- **History**: API call history and analytics

## Development

### Project Structure
```
AIHub/
├── api/                 # FastAPI backend
├── core/               # Core business logic
├── frontend/           # Vue.js frontend
├── business/           # Business plugins
├── config_prompts/     # Prompt configurations
├── docs/               # Documentation
└── scripts/            # Utility scripts
```

### Adding New Features

1. **Backend**: Add new endpoints in `api/main.py` or create new modules
2. **Frontend**: Create new Vue components in `frontend/src/views/`
3. **Plugins**: Implement new capabilities in `business/` directory
4. **Internationalization**: Add translations in `frontend/src/locales/`

### Testing

```bash
# Backend tests
python -m pytest tests/

# Frontend tests
cd frontend
npm run test
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- **Python**: Follow PEP 8, use type hints
- **JavaScript/Vue**: Use ESLint rules, follow Vue.js style guide
- **Documentation**: Write clear docstrings and README updates

## Deployment

### Production Setup

1. **Environment**: Set production environment variables
2. **Database**: Configure persistent storage for service registry
3. **Security**: Enable authentication and HTTPS
4. **Monitoring**: Set up logging and monitoring tools

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/AICoreDirector/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/AICoreDirector/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/AICoreDirector/wiki)

## Acknowledgments

- Built with FastAPI, Vue.js, and Element Plus
- Inspired by modern AI service architectures
- Community contributions and feedback

---

## 🏷️ **Project Topics**

This project is tagged with the following topics for better discoverability:

```
ai-platform, llm-gateway, ai-governance, microservices, 
fastapi, python, ai-orchestration, plugin-system, 
service-mesh, enterprise-ai, ai-integration, ml-platform,
ai-hub, ai-central, ai-management, ai-operations
```

---

**Note**: This is the English version of the README. For Chinese documentation, see [README_zh-CN.md](README_zh-CN.md).

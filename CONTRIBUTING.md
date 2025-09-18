# Contributing to AICoreDirector

Thank you for your interest in contributing to AICoreDirector! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Use the GitHub issue tracker
- Include detailed steps to reproduce
- Provide system information (OS, Python/Node versions)
- Include error logs and stack traces

### Suggesting Enhancements

- Use the GitHub issue tracker with the "enhancement" label
- Describe the use case and expected behavior
- Consider backward compatibility
- Discuss implementation approach

### Code Contributions

- Fork the repository
- Create a feature branch
- Make your changes
- Add tests
- Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Git
- Your preferred IDE/editor

### Local Development

1. **Clone and setup**
   ```bash
   git clone https://github.com/your-username/AICoreDirector.git
   cd AICoreDirector
   
   # Backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   
   # Frontend
   cd frontend
   npm install
   ```

2. **Configuration**
   ```bash
   # Copy and edit configuration files
   cp llm_models.yaml.example llm_models.yaml
   cp .env.example .env
   ```

3. **Start development servers**
   ```bash
   # Terminal 1: Backend
   python main.py
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

## Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8
- **Type Hints**: Use type hints for function parameters and return values
- **Docstrings**: Use Google-style docstrings
- **Imports**: Group imports (standard library, third-party, local)
- **Testing**: Use pytest, aim for >80% coverage

```python
from typing import List, Optional
from fastapi import FastAPI, HTTPException

def process_llm_request(
    prompt: str, 
    model_name: Optional[str] = None
) -> dict:
    """
    Process an LLM request.
    
    Args:
        prompt: The input prompt text
        model_name: Optional specific model to use
        
    Returns:
        Dictionary containing the response and metadata
        
    Raises:
        HTTPException: If the request fails
    """
    # Implementation here
    pass
```

### JavaScript/Vue (Frontend)

- **Style**: Use ESLint and Prettier
- **Vue**: Follow Vue.js style guide
- **Components**: Use composition API with `<script setup>`
- **Internationalization**: Use `$t()` for all user-facing text
- **Testing**: Use Vitest for unit tests

```vue
<template>
  <div class="llm-config">
    <h1>{{ $t('llmconfig.title') }}</h1>
    <!-- Component content -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const config = ref({})

onMounted(() => {
  // Component logic
})
</script>
```

### Internationalization

- **Keys**: Use descriptive, hierarchical keys (e.g., `nav.dashboard`, `errors.network`)
- **Context**: Provide context for translators
- **Fallbacks**: Always provide fallback text
- **Plurals**: Handle pluralization properly

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "llmconfig": "LLM Config"
  },
  "errors": {
    "network": "Network error occurred",
    "validation": "Invalid input data"
  }
}
```

## Pull Request Process

### Before Submitting

1. **Test your changes**
   ```bash
   # Backend tests
   python -m pytest tests/
   
   # Frontend tests
   cd frontend
   npm run test
   npm run build
   ```

2. **Check code quality**
   ```bash
   # Python linting
   flake8 api/ core/ business/
   
   # Frontend linting
   cd frontend
   npm run lint
   ```

3. **Update documentation**
   - Update README if needed
   - Add docstrings for new functions
   - Update API documentation

### Pull Request Guidelines

- **Title**: Clear, descriptive title
- **Description**: Explain what and why, not how
- **Related Issues**: Link to relevant issues
- **Screenshots**: Include for UI changes
- **Testing**: Describe how to test your changes

### Review Process

- All PRs require at least one review
- Address review comments promptly
- Maintainers may request changes
- Squash commits before merging

## Testing

### Backend Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest --cov=api --cov=core
```

### Frontend Testing

```bash
# Unit tests
npm run test:unit

# E2E tests
npm run test:e2e

# Test coverage
npm run test:coverage
```

## Documentation

### Code Documentation

- **Functions**: Document parameters, return values, exceptions
- **Classes**: Document public methods and attributes
- **Modules**: Document purpose and usage
- **API Endpoints**: Document request/response formats

### User Documentation

- **README**: Installation and quick start
- **API Docs**: Endpoint documentation
- **User Guide**: Feature usage and examples
- **Contributing**: This document

## Release Process

### Versioning

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version in `pyproject.toml` and `package.json`
- Create release notes for significant changes

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] Release notes written
- [ ] Tagged and released on GitHub

## Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions
- **Wiki**: Check the project wiki for additional documentation
- **Community**: Join our community channels

## License

By contributing to AICoreDirector, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to AICoreDirector! 🚀

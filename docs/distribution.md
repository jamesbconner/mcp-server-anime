# Package Distribution Guide

This document explains how to build, test, and distribute the mcp-server-anime package.

## Prerequisites

- Python 3.12+
- Poetry (latest version)
- PyPI account (for publishing)
- Git (for version control)

## Package Structure

The package is structured for optimal distribution:

```
mcp-server-anime/
├── src/
│   └── mcp_server_anime/          # Main package code
├── tests/                         # Test suite
├── docs/                          # Documentation
├── pyproject.toml                 # Package configuration
├── README.md                      # Package description
├── LICENSE                        # MIT license
├── CHANGELOG.md                   # Version history
└── .github/                       # CI/CD workflows
```

## Building the Package

### 1. Version Management

Update version in `pyproject.toml`:

```toml
[tool.poetry]
version = "0.1.1"  # Increment as needed
```

Update version in `src/mcp_server_anime/server.py`:

```python
parser.add_argument(
    "--version",
    action="version",
    version="mcp-server-anime 0.1.1"  # Match pyproject.toml
)
```

### 2. Update Changelog

Add new version entry to `CHANGELOG.md`:

```markdown
## [0.1.1] - 2024-12-XX

### Added
- New feature descriptions

### Fixed
- Bug fix descriptions

### Changed
- Breaking change descriptions
```

### 3. Build Package

```bash
# Clean previous builds
rm -rf dist/

# Build package
poetry build

# Verify build contents
tar -tzf dist/mcp-server-anime-*.tar.gz
unzip -l dist/mcp_server_anime-*.whl
```

## Testing Distribution

### 1. Local Testing

Test the built package locally:

```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from wheel
pip install dist/mcp_server_anime-*.whl

# Test installation
mcp-server-anime --version
mcp-server-anime --help

# Test with uvx
uvx run --from dist/mcp_server_anime-*.whl mcp-server-anime --version
```

### 2. Test PyPI (Recommended)

Upload to Test PyPI first:

```bash
# Configure test PyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/

# Upload to test PyPI (requires API token)
poetry publish -r testpypi

# Test installation from test PyPI
pip install --index-url https://test.pypi.org/simple/ mcp-server-anime

# Test with uvx from test PyPI
uvx --index-url https://test.pypi.org/simple/ mcp-server-anime --version
```

## Publishing to PyPI

### 1. Setup Authentication

Create API token at https://pypi.org/manage/account/token/

```bash
# Configure PyPI token
poetry config pypi-token.pypi your-api-token-here
```

### 2. Final Checks

Before publishing:

```bash
# Run full test suite
poetry run pytest

# Check code quality
poetry run ruff check .
poetry run mypy .
poetry run bandit -r src/

# Verify package metadata
poetry check

# Check for common issues
poetry run twine check dist/*
```

### 3. Publish

```bash
# Publish to PyPI
poetry publish

# Verify publication
pip install mcp-server-anime
uvx mcp-server-anime --version
```

## uvx Compatibility

### Entry Points

The package is configured for uvx compatibility:

```toml
[tool.poetry.scripts]
mcp-server-anime = "mcp_server_anime.server:main"
```

### Testing uvx Installation

```bash
# Test direct uvx installation
uvx mcp-server-anime --version

# Test uvx run
uvx run mcp-server-anime --help

# Test in Kiro MCP configuration
# Add to .kiro/settings/mcp.json:
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime"]
    }
  }
}
```

## Continuous Integration

### GitHub Actions

The package includes CI/CD workflows:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run tests
        run: poetry run pytest
```

### Automated Publishing

For automated releases:

```yaml
# .github/workflows/publish.yml
name: Publish
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pip install poetry
      - name: Build package
        run: poetry build
      - name: Publish to PyPI
        env:
          POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_API_TOKEN }}
        run: poetry publish
```

## Package Metadata

### PyPI Classifiers

The package uses appropriate classifiers:

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    "Topic :: Communications :: Chat",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Environment :: Console",
    "Operating System :: OS Independent",
]
```

### Keywords

Optimized for discoverability:

```toml
keywords = [
    "mcp",
    "anime",
    "anidb",
    "api",
    "server",
    "model-context-protocol",
    "kiro"
]
```

## Distribution Checklist

Before each release:

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `server.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run full test suite
- [ ] Check code quality (ruff, mypy, bandit)
- [ ] Build package (`poetry build`)
- [ ] Test local installation
- [ ] Test uvx compatibility
- [ ] Upload to Test PyPI
- [ ] Test installation from Test PyPI
- [ ] Create GitHub release
- [ ] Publish to PyPI
- [ ] Verify PyPI installation
- [ ] Test Kiro integration
- [ ] Update documentation

## Troubleshooting

### Common Issues

**Build fails:**
- Check `pyproject.toml` syntax
- Verify all dependencies are available
- Ensure Python version compatibility

**Upload fails:**
- Check API token configuration
- Verify package name availability
- Check for duplicate version numbers

**uvx installation fails:**
- Verify entry points configuration
- Check package dependencies
- Test with different Python versions

**Kiro integration issues:**
- Test MCP protocol compliance
- Verify tool registration
- Check server startup logs

### Debug Commands

```bash
# Check package contents
poetry show --tree

# Validate package
poetry check

# Check dependencies
poetry show --outdated

# Test entry points
python -c "import pkg_resources; print(list(pkg_resources.iter_entry_points('console_scripts')))"

# Check installation
pip show mcp-server-anime
```

## Security Considerations

### Package Security

- Use secure API tokens
- Scan for vulnerabilities with `bandit`
- Keep dependencies updated
- Use trusted CI/CD environments

### Distribution Security

- Sign releases with GPG (optional)
- Use secure upload methods
- Monitor for package impersonation
- Implement security scanning in CI

## Maintenance

### Regular Tasks

- Update dependencies monthly
- Monitor security advisories
- Review and respond to issues
- Update documentation as needed
- Test with new Python versions

### Long-term Maintenance

- Plan for breaking changes
- Maintain backward compatibility
- Archive old versions appropriately
- Consider package succession planning

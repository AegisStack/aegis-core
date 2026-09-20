# Release Guide for Aegis SDK

Complete guide for creating and publishing SDK releases.

## Table of Contents
1. [Pre-Release Checklist](#pre-release-checklist)
2. [Version Numbering](#version-numbering)
3. [Creating a Release](#creating-a-release)
4. [Publishing to PyPI](#publishing-to-pypi)
5. [GitHub Release](#github-release)
6. [Post-Release](#post-release)

---

## Pre-Release Checklist

Before creating a release:

- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Code coverage acceptable (`pytest --cov=aegis`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with changes
- [ ] Version bumped in `pyproject.toml`
- [ ] No uncommitted changes (`git status`)
- [ ] On main branch (`git branch --show-current`)

---

## Version Numbering

Aegis follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `1.2.3`)
  - **MAJOR**: Breaking API changes
  - **MINOR**: New features (backwards compatible)
  - **PATCH**: Bug fixes (backwards compatible)

### Examples

- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New feature (e.g., add new condition operator)
- `0.2.0` → `1.0.0`: Breaking change (e.g., change API signature)

### Pre-Release Versions

- **Alpha:** `0.1.0a1`, `0.1.0a2` - Early testing
- **Beta:** `0.1.0b1`, `0.1.0b2` - Feature complete, testing
- **Release Candidate:** `0.1.0rc1` - Final testing before release

---

## Creating a Release

### Step 1: Update Version

Edit `pyproject.toml`:

```toml
[project]
name = "aegis-sdk"
version = "0.2.0"  # Update this
```

### Step 2: Update CHANGELOG

Create/update `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to Aegis SDK will be documented in this file.

## [0.2.0] - 2026-04-07

### Added
- Support for `regex` condition operator
- Dashboard integration with WebSocket live feed
- Async batch ingestion for improved performance

### Changed
- Improved policy validation error messages
- Updated TimescaleDB schema for better indexing

### Fixed
- Fixed race condition in escalation manager
- Fixed memory leak in audit writer

### Breaking Changes
- None

## [0.1.0] - 2026-04-06

### Added
- Initial release
- Core policy engine with 8 condition operators
- Tool wrapping with signature preservation
- Audit logging with file sink
- Escalation management
- Complete test suite (44 tests)
```

### Step 3: Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.2.0"
```

### Step 4: Create Git Tag

```bash
# Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0

- Support for regex operator
- Dashboard integration
- Performance improvements

See CHANGELOG.md for full details."

# Verify tag
git show v0.2.0
```

### Step 5: Push to Remote

```bash
git push origin main
git push origin v0.2.0
```

---

## Publishing to PyPI

### Prerequisites

Install build tools:

```bash
pip install build twine
```

Create PyPI account at https://pypi.org/account/register/

### Step 1: Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### Step 2: Build Distribution

```bash
python -m build
```

This creates:
- `dist/aegis-sdk-0.2.0.tar.gz` (source distribution)
- `dist/aegis_sdk-0.2.0-py3-none-any.whl` (wheel)

### Step 3: Test with TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ aegis-sdk==0.2.0

# Test imports
python -c "from aegis import PolicyEngine; print('Success!')"
```

### Step 4: Upload to PyPI

```bash
python -m twine upload dist/*
```

You'll be prompted for credentials. Alternatively, use API token:

```bash
# Create ~/.pypirc
cat > ~/.pypirc <<EOF
[pypi]
username = __token__
password = pypi-AgE...your-token-here
EOF

# Make sure it's secure
chmod 600 ~/.pypirc

# Upload
python -m twine upload dist/*
```

### Step 5: Verify Installation

```bash
# Create fresh virtualenv
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install from PyPI
pip install aegis-sdk==0.2.0

# Test
python -c "from aegis import wrap; print('Success')"

# Cleanup
deactivate
rm -rf test_env
```

---

## GitHub Release

### Option 1: Web Interface

1. Go to https://github.com/yourorg/aegis-core/releases
2. Click "Draft a new release"
3. Choose tag: `v0.2.0`
4. Release title: `Aegis SDK v0.2.0`
5. Description: Copy from CHANGELOG.md
6. Attach files (optional):
   - `dist/aegis-sdk-0.2.0.tar.gz`
   - `dist/aegis_sdk-0.2.0-py3-none-any.whl`
7. Click "Publish release"

### Option 2: GitHub CLI

```bash
gh release create v0.2.0 \
  --title "Aegis SDK v0.2.0" \
  --notes-file CHANGELOG.md \
  dist/aegis-sdk-0.2.0.tar.gz \
  dist/aegis_sdk-0.2.0-py3-none-any.whl
```

---

## Post-Release

### Update Documentation

If you have a docs site:

```bash
cd docs
# Update version in config
# Rebuild docs
# Deploy
```

### Announce Release

Post announcement:
- GitHub Discussions
- Twitter/X
- Reddit (r/Python, r/MachineLearning)
- Discord/Slack communities
- Company blog

Example announcement:

```
Aegis SDK v0.2.0 is now available!

New features:
- Regex pattern matching in policies
- Real-time dashboard with WebSocket feed
- 3x faster audit ingestion

Upgrade: pip install --upgrade aegis-sdk

Docs: https://github.com/yourorg/aegis-core
Changelog: https://github.com/yourorg/aegis-core/blob/main/CHANGELOG.md
```

### Start Next Development Cycle

```bash
# Update version to next dev version
# Edit pyproject.toml: version = "0.3.0.dev0"

git add pyproject.toml
git commit -m "Start v0.3.0 development cycle"
git push origin main
```

---

## Automated Release Process (Optional)

### GitHub Actions Workflow

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          body_path: CHANGELOG.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Add PyPI token to GitHub secrets:
1. Go to repository Settings → Secrets → Actions
2. Add secret: `PYPI_API_TOKEN` = your PyPI token

Now releases are automatic:
```bash
git tag v0.2.0
git push origin v0.2.0
# GitHub Actions handles the rest!
```

---

## Troubleshooting

### Upload Failed: File Already Exists

PyPI doesn't allow re-uploading the same version. Solutions:

1. **Bump patch version:** `0.2.0` → `0.2.1`
2. **Use post-release:** `0.2.0.post1`
3. **Delete from TestPyPI** (only works on test server)

### Import Errors After Install

Check package structure:

```bash
# Unzip wheel
unzip -l dist/aegis_sdk-0.2.0-py3-none-any.whl

# Should see:
# aegis/__init__.py
# aegis/policy_engine.py
# etc.
```

If files are missing, check `pyproject.toml`:

```toml
[tool.setuptools]
packages = ["aegis"]
```

### Version Mismatch

Ensure version is consistent:
- `pyproject.toml`
- Git tag
- CHANGELOG.md

```bash
# Check version in installed package
python -c "import aegis; print(aegis.__version__)"
```

---

## Quick Reference

```bash
# Complete release workflow
# 1. Update version
vim pyproject.toml  # version = "0.2.0"

# 2. Update changelog
vim CHANGELOG.md

# 3. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main v0.2.0

# 4. Build and publish
rm -rf dist/
python -m build
python -m twine upload dist/*

# 5. Create GitHub release
gh release create v0.2.0 \
  --title "v0.2.0" \
  --notes-file CHANGELOG.md \
  dist/*

# 6. Verify
pip install --upgrade aegis-sdk
python -c "from aegis import PolicyEngine; print('OK')"
```

---

## Resources

- **Packaging Guide:** https://packaging.python.org/
- **Semantic Versioning:** https://semver.org/
- **PyPI Help:** https://pypi.org/help/
- **GitHub Releases:** https://docs.github.com/en/repositories/releasing-projects-on-github

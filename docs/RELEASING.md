# Releasing Aegis SDK

This guide releases the Python SDK (`aegis-core-sdk`) to PyPI. The dashboard is not
included in the published package.

## One-time setup

1. Create a PyPI account and enable two-factor authentication.
2. Confirm that `aegis-core-sdk` is an available PyPI project name.
3. In PyPI, open **Publishing** → **Add a new pending publisher** and select
   GitHub. Enter:
   - Owner: `AegisStack`
   - Repository: `aegis-core`
   - Workflow: `release.yml`
   - Environment: `pypi`
4. In GitHub, create a repository environment named `pypi` under **Settings**
   → **Environments**. Require reviewers there if production releases need an
   approval gate.

The repository uses PyPI Trusted Publishing. Do not create or store a PyPI API
token: publishing uses GitHub's short-lived OIDC identity instead.

## Prepare a release

Use Semantic Versioning: `MAJOR.MINOR.PATCH`. Increment MAJOR for breaking
changes, MINOR for compatible features, and PATCH for compatible fixes.

1. Update the version in both `pyproject.toml` and `aegis/__init__.py`.
2. Move the relevant entries from `[Unreleased]` to a dated version section in
   `CHANGELOG.md`.
3. Run the release checks locally:

   ```powershell
   .\venv\Scripts\python.exe -m pip install --upgrade build twine
   .\venv\Scripts\python.exe -m pytest tests -q
   Remove-Item -Recurse -Force dist, build, aegis_sdk.egg-info -ErrorAction SilentlyContinue
   .\venv\Scripts\python.exe -m build
   .\venv\Scripts\python.exe -m twine check dist/*
   ```

4. Optionally upload to TestPyPI and install it in a fresh environment:

   ```powershell
   .\venv\Scripts\python.exe -m twine upload --repository testpypi dist/*
   ```

   TestPyPI credentials are separate from production PyPI. A TestPyPI trusted
   publisher can be configured separately if this becomes a regular step.

## Publish to PyPI

1. Commit the version and changelog changes on `main`.
2. Create an annotated tag matching the package version exactly, for example:

   ```powershell
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin main v0.1.0
   ```

3. In GitHub, create and publish a release for that tag. Publishing the GitHub
   Release starts `.github/workflows/release.yml`.

The workflow verifies that the tag is `v` plus the `pyproject.toml` version,
runs the SDK tests, builds the source distribution and wheel, checks their
metadata, and then uploads them to PyPI. The OIDC permission exists only in the
final publishing job.

## Verify the published release

After the workflow succeeds, use a new environment outside the repository:

```powershell
python -m venv aegis-verify
.\aegis-verify\Scripts\python.exe -m pip install aegis-core-sdk==0.1.0
.\aegis-verify\Scripts\python.exe -c "from aegis import PolicyEngine; print('OK')"
```

Replace `0.1.0` with the released version. PyPI versions are immutable; if an
artifact is wrong, release a new version rather than trying to replace it.

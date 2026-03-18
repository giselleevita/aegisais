# Backend Dependency Management

`apps/api/pyproject.toml` is the only source of truth for direct backend dependencies.

The generated artifacts are:

- `requirements.lock`: fully resolved runtime dependency graph with hashes
- `requirements-dev.lock`: fully resolved dev environment with hashes and `-r requirements.lock` at the top

## Rules

- Do not edit `requirements.lock` manually.
- Do not edit `requirements-dev.lock` manually.
- Do not install backend dependencies with plain `pip install -r ...` unless `--require-hashes` is used.
- Do not add a second dependency source such as `requirements.in`, Poetry, or uv.

## Why this strategy

- It keeps the existing `pip` + `pyproject.toml` model.
- Hashes make installs artifact-verified, not just version-pinned.
- Docker installs only the runtime lock, while dev syncs from the dev lock that explicitly includes runtime.
- The same compiler script is used by developers, CI, and lockfile validation.

## Lockfile compilation

The canonical compiler is:

```bash
cd apps/api
./scripts/compile_lockfiles.sh
```

Under the hood, the runtime graph is compiled with:

```bash
pip-compile \
  --generate-hashes \
  --allow-unsafe \
  --strip-extras \
  --output-file=requirements.lock \
  pyproject.toml
```

The dev graph is compiled from the `dev` extra in `pyproject.toml`, constrained by `requirements.lock`, and emitted as `requirements-dev.lock` with:

- `-r requirements.lock`
- dev-only packages and their hashes

This prevents runtime and dev from drifting apart.

## Installation workflow

Runtime install:

```bash
python3 -m pip install --require-hashes -r apps/api/requirements.lock
```

Development install:

```bash
python3 -m pip install pip-tools==7.5.3
cd apps/api
pip-sync requirements-dev.lock
python3 -m pip install --no-deps -e .
```

`pip-sync` owns the environment. Re-run the editable install after a sync if you need the local package linked.

## Validation

To verify that committed lockfiles still match `pyproject.toml`:

```bash
apps/api/scripts/check_lockfiles.sh
```

The checker recompiles lockfiles in a temporary directory and fails on any diff.

## Security audit

Run the locked dependency audit with:

```bash
cd apps/api
pip-audit -r requirements.lock
```

## Docker behavior

The production image copies `requirements.lock` before application code and installs it with `--require-hashes`. Dev dependencies are never installed in the production image.

## Upgrade policy

- Review and refresh dependencies weekly.
- Use `make update-deps` from `apps/api` for controlled upgrades.
- Every upgrade must pass lockfile validation, `pip-audit`, tests, and the Docker build before merge.

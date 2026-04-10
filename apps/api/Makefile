update-deps:
	./scripts/compile_lockfiles.sh --upgrade

check-deps:
	./scripts/check_lockfiles.sh

audit-deps:
	pip-audit -r requirements.lock

smoke-llm:
	./.venv/bin/python ./scripts/smoke_llm.py

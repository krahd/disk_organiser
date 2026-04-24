.PHONY: venv install backend frontend dev

venv:
	python3 -m venv venv

install: venv
	. venv/bin/activate && pip install -r backend/requirements.txt || true
	# install node deps (root package.json)
	npm ci --no-audit || true

backend:
	. venv/bin/activate && python -m backend.app

frontend:
	npm run start

dev:
	@echo "Starting backend in background and frontend in foreground..."
	./scripts/dev.sh

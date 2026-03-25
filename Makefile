VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"

test:
	$(VENV)/bin/pytest -q --tb=line

test-fast:
	$(VENV)/bin/pytest -q --tb=line --lf

test-parallel:
	$(VENV)/bin/pytest -q --tb=line -n auto

coverage:
	$(VENV)/bin/pytest --cov=cryptoscholar --cov-report=term-missing

lint-security:
	$(VENV)/bin/bandit -r cryptoscholar/

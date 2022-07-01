PYTHON=python3.9
PIP=$(PYTHON) -m pip

init:
	$(PIP) install -r requirements.txt

install: init
	$(PIP) install -e .

test:
	$(PYTHON) -m pytest -v

.PHONY: init install

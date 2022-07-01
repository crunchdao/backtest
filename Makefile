PYTHON=python
PIP=$(PYTHON) -m pip

init:
	$(PIP) install -r requirements.txt

install: init
	$(PIP) install -e .

test:
	$(PYTHON) -m pytest -v

example:
	PYTHONPATH=. find example/ -name "*.py" -exec $(PYTHON) {} \;

.PHONY: init install test example

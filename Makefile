init:
	pip install -r requirements.txt

install: init
	pip install -e .

test:
	python -m unittest discover -p 'test_*.py'

.PHONY: init install

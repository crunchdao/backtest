init:
	pip install -r requirements.txt

install: init
	pip install -e .

.PHONY: init install

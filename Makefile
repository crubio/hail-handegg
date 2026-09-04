PYTHON = uv run python

.PHONY: run prefetch train

run:
	$(PYTHON) main.py

prefetch:
	$(PYTHON) scripts/prefetch.py

train:
	$(PYTHON) scripts/train_ranker.py

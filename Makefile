PROJECT=src
FLAKE8=flake8
PYDOCSTYLE=pydocstyle

all: help

help:
	@echo "clean -------------- - Clean all artifacts."
	@echo "  clean-pyc          - Remove Python cache files."
	@echo "distcheck ---------- - Check distribution for problems."
	@echo "  flake              - Run flake8 on the source code."
	@echo "  docscheck          - Run pydocstyle on Python files."

clean: clean-pyc

clean-pyc:
	-find . -type f -a \( -name "*.pyc" -o -name "*$$py.class" \) | xargs rm
	-find . -type d -name "__pycache__" | xargs rm -r

distcheck: flake docscheck

flake:
	$(FLAKE8) "$(PROJECT)"

docscheck:
	$(PYDOCSTYLE) "$(PROJECT)"

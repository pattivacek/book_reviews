.PHONY: all toc clean_pdf clean force lint lint-fix format

TEX = pdflatex -halt-on-error -file-line-error

# Use python3 if available, or whatever python is if not.
# http://stackoverflow.com/questions/28480240/makefile-use-exe1-if-exists-else-exe2
PYTHON := $(shell python3 --version >/dev/null 2>&1 && echo python3 || echo python)

DOC_NAME := book_reviews

all: $(DOC_NAME).pdf

toc: clean_pdf all

statistics.tex: book_reviews.tex calculate_stats.py
	$(PYTHON) calculate_stats.py

clean_pdf:
	rm -f $(DOC_NAME).pdf

clean: clean_pdf
	rm -f $(DOC_NAME).aux $(DOC_NAME).log $(DOC_NAME).out $(DOC_NAME).toc booklist.csv statistics.tex *~

%.pdf: %.tex statistics.tex
	$(TEX) $<

lint:
	uv run ruff check calculate_stats.py

lint-fix:
	uv run ruff check --fix calculate_stats.py

format:
	uv run ruff format calculate_stats.py

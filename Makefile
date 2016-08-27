.PHONY: all toc stats clean_pdf clean force

TEX = pdflatex -halt-on-error -file-line-error

# Use python3 if available, or whatever python is if not.
# http://stackoverflow.com/questions/28480240/makefile-use-exe1-if-exists-else-exe2
PYTHON := $(shell python3 --version >/dev/null 2>&1 && echo python3 || echo python)

DOC_NAME := book_reviews

all: $(DOC_NAME).pdf

toc: clean_pdf all

#stats: statistics.tex
stats: calculate_stats.py
	$(PYTHON) $<

clean_pdf:
	rm -f $(DOC_NAME).pdf

clean: clean_pdf
	rm -f $(DOC_NAME).aux $(DOC_NAME).log $(DOC_NAME).out $(DOC_NAME).toc booklist.csv statistics.tex *~

%.pdf: %.tex stats
	$(TEX) $<

#statistics.tex: calculate_stats.py
#	$(PYTHON) $<

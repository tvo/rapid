# Author: Tobi Vollebregt
#
# Makefile for development purposes.
#

.PHONY: all pylint

all: README.txt README.html

# PyPI wants ReStructured text
README.txt: README.markdown
	pandoc -f markdown -t rst $< > $@

# I want HTML (to preview the formatting :))
README.html: README.markdown
	pandoc -f markdown -t html $< > $@

pylint:
	pylint --indent-string='\t' bin/rapid

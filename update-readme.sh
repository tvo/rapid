#!/bin/sh

# PyPI wants ReStructured text
pandoc -f markdown -t rst README.markdown > README.txt

# I want HTML (to preview the formatting :))
pandoc -f markdown -t html README.markdown > README.html

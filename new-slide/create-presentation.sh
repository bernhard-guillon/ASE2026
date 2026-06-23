#!/bin/bash
pandoc presentation.md -t beamer --listings --include-in-header=header.tex --template=beamer-sans.tex -o presentation.pdf

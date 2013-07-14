#!/bin/sh
for f in `find . -name '*.py' | egrep -v '^\./\.venv/'`; do
	pep8 --config=./tools/pep8.conf $f
done

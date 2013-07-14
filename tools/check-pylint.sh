#!/bin/sh

for f in `find . -name '*.py' | egrep -v '^\./\.venv/'`; do
	pylint --rcfile=./tools/pylint.rc $f
done

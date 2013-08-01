#!/bin/sh -x

set -e

pandoc ./docs/rest-api.markdown -t html5 -H ./docs/html/markdown.header -o ./docs/html/rest-api.html

#/bin/sh

set -e

if [ -n "$VIRTUAL_ENV" ]; then
	echo 'A virtualenv is currently active'
	echo 'You must run deactivate'
	exit 1
fi

rm -rf .venv
virtualenv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt

echo
echo 'virtualenv setup in .venv/ directory, with all requirements installed.'
echo 'To activate run:'
echo
echo 'source .venv/bin/activate'

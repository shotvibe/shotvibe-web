#!/bin/sh -x

set -e

virtualenv --system-site-packages .venv
. .venv/bin/activate
pip install -r ./requirements.txt
pip install -r ./tools/jenkins-requirements.txt

ln -sf ./tools/jenkins_local_settings.py ./local_settings.py

# Compile documentation in `docs` directory

./tools/make-docs.sh

mkdir -p reports

# Fatal Reports that will break the build
./tools/check-fatal-problems.pep8.sh > reports/fatal-pep8.report || true

# Standard Reports
./tools/check-pylint.sh > reports/pylint.report || true
./tools/check-pep8.sh > reports/pep8.report || true

python ./manage.py jenkins

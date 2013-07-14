#!/bin/sh -x

set -e

virtualenv --system-site-packages .venv
. .venv/bin/activate
pip install -r ./requirements.txt
pip install -r ./tools/jenkins-requirements.txt

ln -sf ./tools/jenkins_local_settings.py ./local_settings.py

mkdir -p reports

./tools/check-fatal-problems.pep8.sh > reports/fatal-pep8.report || true
./tools/check-pylint.sh > reports/pylint.report || true

python ./manage.py jenkins

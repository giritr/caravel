#!/usr/bin/env bash
echo $DB
rm /tmp/caravel_unittests.db
rm /tmp/celerydb.sqlite 
rm /tmp/celery_results.sqlite
rm -f .coverage
export CARAVEL_CONFIG=tests.caravel_test_config
set -e
caravel/bin/caravel db upgrade
caravel/bin/caravel version -v
python setup.py nosetests


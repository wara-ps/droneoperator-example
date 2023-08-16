#!/bin/sh

AGENT_MANAGER_TEST_CLASS="agent_manager_test.py"
echo -e "Starting tests from test class(es): $AGENT_MANAGER_TEST_CLASS \n"

python -m unittest tests/$AGENT_MANAGER_TEST_CLASS

#!/bin/bash

echo 'This script will use "docker build" to build the Drone Operator with the "latest" tag and push it to the waraps registry.'

read -p "Are you sure? [Y/n]" -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]   
then
    echo "Script Starting"
    docker build -t drone_operator_1:latest .
    docker tag drone_operator_1:latest registry.waraps.org/drone_operator_1:latest
    docker push registry.waraps.org/drone_operator_1:latest
fi

echo "Script done 👌 BYE"
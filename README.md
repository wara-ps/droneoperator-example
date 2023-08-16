#WARA-PS Drone Operator

## Introduction
This repo contatins code for the deployment of a virtual "Drone Operator". A drone operator looks like an agent on the map, but functions as a coordinator and decision maker. 
This is because the drone operator has access to a number of drones and can receive commands and task-requests from users, that may find it to complicated or are uninterested in finding
which drone is most suitable to perform the requested task. 

For example, if you want an area to be searched but does not want to spend valuable time looking for a suitable agent you can send the task to a drone operator. 
The drone operator will then sort through the agents it governs and decide which is most suitable to perform the task, currently based on proximity, and send it onwards to that 
agent, which will then execute the task. In the future, more parameters that the drone operator can base its decision on, such as endurance of the drone, speed ect., can be added.

##Getting started
###Install:
To run the code for the drone operator you need certain libraries which you can install through the command:
```pip install -r requirements.txt```

###Code edits:
To change the drone operator so that it governs your agents, you need to edit the ```agents.json``` file in the data folder.

Note that you will also have to fill in username and password for the mqtt broker, in ```.env```, before you can run the code.
Besides mqtt broker configurations, the agent name and position is also set in the ```.env``` file.

###Pipenv (virtual environment)
One way to build and run your drone operator is with the pipenv virtual environment
`pip install pipenv`  
`pipenv install`  
`pipenv run python ./main.py` 

###Docker
Another way to build and run your drone operator is to use docker. Thus a ```docker-compose.yml``` file has been added in the repo for easy deployment.

The command used are `docker-compose up. To shut it down press control + C.

##build_and_push.sh
Is a bash script that build a docker image with the `latest` tag and push it the WARAPS registry. The registry is password protected.

##Run Tests
Run tests.
 
From PyCharm:
1. Install Pytest if not installed
2. Run tests from PyCharm

From shell script in windows:
1. Install Pytest if not installed
2. Open terminal with shell script support, (e.g. Git bash)
3. From repo root folder, runt sh run_tests.py
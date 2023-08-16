from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum
import json, os
from queue import PriorityQueue

class TaskStatus(Enum):
    NONE = None
    RUNNING = 0
    PAUSED = 1
    FINISHED = 2
    DELAYED = 3

class Task():
    def __init__(self) -> None:
        #USSP Variables
        #request_height

        self.original_task: dict = None
        self.agent = None
        self.waraps_task: dict = None
        self.task_uuid: str = None
        self.priority: int = 1


        #################
        self.json = None
        self._ground_height: int = None
        self.waypoints: list = None
        self.status: TaskStatus = TaskStatus.NONE
        
        #request_plan
        self.plan_id: str = None
        self.task_made: datetime = None
        self.task_completed: datetime = None
        self.delay: int = None

        self._ussp_plan: str = None
        


    @property
    def ground_height(self):
        return self._ground_height

    @ground_height.setter
    def ground_height(self, data: dict):
        self._ground_height = data["height"]

    def set_plan_from_request(self, plan: dict):
        self.plan_id = plan["plan ID"]
        self.task_made = datetime.utcnow()
        self.delay = plan["delay"]

    @property
    def ussp_plan(self):
        return self._ussp_plan

    @ussp_plan.setter
    def ussp_plan(self, ussp_plan: dict):
        self._ussp_plan = ussp_plan["plan"]

    def plan_to_task(self, mqtt_manager, task_details: dict):
        try:
            waraps_task: dict = {}
            if task_details["task"]["name"] == "move-to":
                #NOTE!! This function ('move-to') does not work well with the USSP service due to
                #the planner sends a whole flight plan, but we only want/need one position.

                #Takes the last position in the flight plan and send it to the agent
                lat = self.ussp_plan[3]["position"][0]
                lon = self.ussp_plan[3]["position"][1]
                alt = self.ussp_plan[3]["position"][2]
                waraps_task = {
                    "com-uuid": mqtt_manager.operator_id,
                    "command": "start-task",
                    "execution-unit": self.agent.meta["name"],
                    "sender": mqtt_manager.operator_name,
                    "task": {
                        "name": "move-to",
                        "params": {
                            "speed": "standard",
                            "ussp-plan": self.plan_id,
                            "waypoint": {
                                "altitude": alt,
                                "latitude": lat,
                                "longitude": lon,
                                "rostype": "GeoPoint"
                                }
                            }
                    },
                    "task-uuid": task_details["task-uuid"]
                }

            elif task_details["task"]["name"] == "move-path":
                waraps_task = {
                    "com-uuid": mqtt_manager.operator_id,
                    "command": "start-task",
                    "execution-unit": self.agent.meta["name"],
                    "sender": mqtt_manager.operator_name,
                    "task": {
                        "name": "move-path",
                        "params": {
                            "speed": "standard",
                            "ussp-plan": self.plan_id,
                            "waypoints": []
                        }
                    },
                    "task-uuid": task_details["task-uuid"]
                }

                for fp in self.ussp_plan:
                    lat = fp["position"][0]
                    lon = fp["position"][1]
                    alt = fp["position"][2]
                    point: dict = {           
                        "altitude": alt,
                        "latitude": lat,
                        "longitude": lon,
                        "rostype": "GeoPoint"
                    }
                    waraps_task["task"]["params"]["waypoints"].append(point)

            elif task_details["task"]["name"] == "search-area":
                waraps_task = {
                    "com-uuid": mqtt_manager.operator_id,
                    "command": "start-task",
                    "execution-unit": self.agent.meta["name"],
                    "sender": mqtt_manager.operator_name,
                    "task": {
                        "name": "search-area",
                        "params": {
                            "speed": "standard",
                            "target-type": "person",
                            "target-size": 4.0,
                            "ussp-plan": self.plan_id,
                            "area": []
                        }
                    },
                    "task-uuid": task_details["task-uuid"]
                }

                for fp in self.ussp_plan:
                    lat = fp["position"][0]
                    lon = fp["position"][1]
                    alt = fp["position"][2]
                    point: dict = {           
                        "altitude": alt,
                        "latitude": lat,
                        "longitude": lon,
                        "rostype": "GeoPoint"
                    }
                    waraps_task["task"]["params"]["area"].append(point)

        except TypeError:
            waraps_task["task"]["params"]["waypoints"] = []
        finally:
            self.waraps_task = waraps_task
            print("Plan -> Task !DONE!")
            return waraps_task

    def make_json(self) -> dict:
        item: dict = {}
        item["ground_height"] = self.ground_height
        item["status"] = self.status
        item["plan_id"] = self.plan_id
        item["task_made"] = str(self.task_made)
        item["task_completed"] = str(self.task_completed)
        item["delay"] = self.delay
        item["ussp_plan"] = self.ussp_plan
        item["agent"] = self.agent.meta["name"]
        item["waraps_task"] = self.waraps_task
        return item

    def save_task_to_log(self):
        try:
            time_str = str(datetime.utcnow())
            file_name = time_str.replace(":", "-")
            file_name = file_name + ".json"
            file = self.make_json()
            with open(f"./logs/{file_name}", "w") as f:
                f.write(json.dumps(file))
        except FileNotFoundError:
            file_path = "./logs/"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(f"./logs/{file_name}", "w") as f:
                f.write(json.dumps(file))

@dataclass(order=True)
class TaskQueueItem:
    priority: int
    item: Any=field(compare=False)

class TaskQueue():
    def __init__(self, _maxsize: int = 10) -> None:
        self.queue: PriorityQueue[Task] = PriorityQueue(maxsize=_maxsize)

    def put_task_to_queue(self, item: TaskQueueItem):
        """Puts a TaskQueueItem into the Queue"""
        self.queue.put(item)

    def get_task_from_queue(self) -> TaskQueueItem:
        """Return the first TaskQueueItem from the Queue"""
        return self.queue.get()
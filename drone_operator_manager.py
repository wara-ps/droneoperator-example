from dataclasses import dataclass
import json


@dataclass
class DroneOperator():
    def __init__(self, data: dict) -> None:
        self.name: str = data["name"]
        self.base_topic: str = data["base_topic"]
        self.command_topic: str = data["command_topic"]
        self.levels: list = []
        self.tasks_available: list = []

class DroneOperatorManager:
    """Handle Drone Operators that are children to this Drone Operator"""
    def __init__(self) -> None:
        try:    
            self.children_list: list = []
            self.children: list = []

            with open('./data/drone_operators.json') as f:
                data = json.load(f)
                self.children_list = data["drone_operators"]

        except FileNotFoundError:
            print("Did not find data['drone_operators']")
    
    def create_new_drone_operator(self, data: dict) -> DroneOperator:
        new_child: DroneOperator = DroneOperator(data)
        self.children.append(new_child)
        return new_child
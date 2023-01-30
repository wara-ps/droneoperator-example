
import json
from datetime import datetime, timedelta
from paho.mqtt.client import Client as PahoClient
from data.config import USSPConfig
import uuid
from threading import Event
from data.config import OperatorConfig

class USSP():
    
    @classmethod
    def create_connection(self, client: PahoClient, topic:str, name: str):
        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "start-communication",
                "meta": {},
                "params": {
                    "name": name
                }
            },
            "task-uuid": str(uuid.uuid4())
        }
        client.publish(topic, json.dumps(payload))


    @classmethod
    def request_height(self, client: PahoClient, topic: str, event: Event):

        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "request-height",
                "meta": {},
                "params": {
                    "request": "query ground height"
                }
            },
            "task-uuid": str(uuid.uuid4())
        }

        client.publish(topic, json.dumps(payload))
        print(f"Sent 'query ground height' request. Awaiting response.....")
        event.wait()
        event.clear()
    

    @classmethod
    def request_plan(self, client: PahoClient, topic: str, event: Event, waypoints: list, payload_data: dict, speed: float = 100.0 ) -> json:

        nodes: list = []
        for wp in waypoints:
            node = {
            "type": "2D path",
            "position": [ wp[0], wp[1] ]
            }
            nodes.append(node)

        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "request-plan",
                "meta": {
                },
                "params": {
                    "request": "request plan",
                    "operator ID": payload_data["operator ID"],
                    "UAS ID": payload_data["UAS ID"],
                    "EPSG": payload_data["EPSG"],
                    "plan": nodes,
                    "when": str(datetime.utcnow() + timedelta(seconds=90)), #90 secounds in the future
                    "preferred speed": speed,
                    "preferred rate of ascend": 10,
                    "preferred rate of descend": 10
                }
            },
            "task-uuid": str(uuid.uuid4())
        }

        client.publish(topic, json.dumps(payload))
        print("Sent 'request plan' request. Awaiting response.....")
        event.wait()
        event.clear()
    

    @classmethod
    def get_plan(self, client: PahoClient, topic: str, event: Event, plan_id: str):

        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "get-plan",
                "meta": {
                },
                "params": {
                    "request": "get plan",
                    "plan ID": plan_id
                }
            },
            "task-uuid": str(uuid.uuid4())
        }

        client.publish(topic, json.dumps(payload))
        print("Sent 'Get plan' request. Awaiting response.....")
        event.wait()
        event.clear()
    

    @classmethod
    def accept_plan(self, client: PahoClient, topic: str, event: Event, plan_id: str) -> None:
        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "accept-plan",
                "meta": {
                },
                "params": {
                    "request": "accept plan",
                    "plan ID": plan_id
                }
            },
            "task-uuid": str(uuid.uuid4())
        }

        client.publish(topic, json.dumps(payload))
        print("Sent 'Accept Plan' request. Awaiting response.....")
        event.wait()
        event.clear()
        
    @classmethod
    def activate_plan(self, client: PahoClient, topic: str, event: Event, plan_id: str) -> None:

        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "activate-plan",
                "meta": {
                },
                "params": {
                    "request": "activate plan",
                    "plan ID": plan_id
                    #"withdraw plan": 50.0,
                }
            },
            "task-uuid": str(uuid.uuid4())
        }

        client.publish(topic, json.dumps(payload))
        print("Sent 'Activate Plan' request. Awaiting response.....")
        event.wait()
        event.clear()

    @classmethod
    def end_plan(self, client: PahoClient, topic: str, event: Event, plan_id: str) -> None:
        payload = {
            "com-uuid": OperatorConfig.OPERATOR_ID,
            "command": "start-task",
            "execution-unit": "USSP",
            "sender": OperatorConfig.OPERATOR_NAME,
            "task": {
                "name": "end-plan",
                "meta": {
                },
                "params": {
                    "request": "end plan",
                    "plan ID": plan_id
                }
            },
            "task-uuid": str(uuid.uuid4()) 
        }

        client.publish(topic, json.dumps(payload))

        print("Sent 'End Plan' request. Awaiting response.....")
        #client.loop_write()
        #event.wait()
        event.clear()

        
    @classmethod
    def cancel_plan(self, plan: json) -> None:
        return NotImplemented
        payload = {
            "request": "cancel plan",
            "plan ID": plan["plan ID"]
        }
        #the new payload
        # {
        #     "com-uuid": "5af69500-8a40-45df-8829-754e8cab5567",
        #     "command": "start-task",
        #     "execution-unit": "USSP",
        #     "sender": OperatorConfig.OPERATOR_NAME,
        #     "task": {
        #         "name": "cancel-plan",
        #         "meta": {
        #         },
        #         "params": {
        #             "request": "cancel plan",
        #             "plan ID": "<plan_id>"
        #         }
        #     },
        #     "task-uuid": "e185dd39-895a-4e6a-bd5a-d71b2872afe7"
        # }

        print("Sent 'Cancel Plan' request. Awaiting response.....")
        self.service_socket.send_string(json.dumps(payload))
        recv_msg = self.service_socket.recv_string()
        json_msg = json.loads(recv_msg)
        print(f"'Cancel Plan' response from server: \n {json_msg}") 



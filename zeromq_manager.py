import zmq
import json, traceback
from datetime import datetime, timedelta
from data.config import ZmqConfig



class ZeromqManager():

    def __init__(self) -> None:
        self.context = None
        self.service_socket = None
        self.publish_socket = None

    def initialize(self):
        context = zmq.Context()
        
        service_socket: zmq.Socket = context.socket(zmq.REQ) # REQ -> REP
        
        service_socket.setsockopt(zmq.TCP_KEEPALIVE,1) # KEEP THE SOCKET CONNECTION ALIVE
        service_socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE,300)
        service_socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL,300)

        service_socket.setsockopt(zmq.RCVTIMEO, 10000) #TIMEOUT WHEN SENDING A MESSAGE (Wait time)
        service_socket.setsockopt(zmq.LINGER, 0) #NEEDED FOR TIMEOUT

        #publish_socket = context.socket(zmq.PUB) #PUB -> SUB
        # publish_server: str = ZmqConfig.PUBLISH_SERVER
        # publish_port: int = ZmqConfig.PUBLISH_PORT

        # publish_socket.setsockopt(zmq.RCVTIMEO, 1000) #TIMEOUT
        # publish_socket.setsockopt(zmq.LINGER, 0) #NEEDED FOR TIMEOUT

        # publish_url: str = ZmqConfig.PUBLISH_URL
        # publish_socket.connect(publish_url)
        # print(f"Connected to USSP: {publish_url}")

        self.context = context
        self.service_socket = service_socket
        #self.publish_socket = publish_socket

    #sock = self.service_socket
    
    def run(self):
        service_url: str = ZmqConfig.SERVICE_URL
        self.service_socket.connect(service_url)
        print(f"Connected to USSP Service: {service_url}")

    def disconnect(self):
        self.service_socket.disconnect(ZmqConfig.SERVICE_URL)

    def request_height(self) -> json:
            try:
                payload = {
                    "request": "query ground height"
                }   

                self.service_socket.send_string(json.dumps(payload))
                print(f"Sent 'query ground height' request. Awaiting response.....")
                recv_msg = self.service_socket.recv_string()
                recv_json = json.loads(recv_msg)

                print(f"'query ground height' response from server: \n {recv_json}")
                return recv_json

            except zmq.ZMQError as e:
                raise zmq.ZMQError(e)
            except Exception:
                print(traceback.format_exc())

    def request_plan(self, waypoints: list, payload_data: dict, speed: float = 100.0 ) -> json:
        try:
            nodes: list = []
            for wp in waypoints:
                node = {
                "type": "2D path",
                "position": [ wp[0], wp[1] ]
                }
                nodes.append(node)

            #TODO does not wait for "when". when the replay comes back.
            payload = {
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

            print("Sent 'request plan' request. Awaiting response.....")
            self.service_socket.send_string(json.dumps(payload))
            recv_msg = self.service_socket.recv_string()
            recv_json = json.loads(recv_msg)
            print(f"'request plan' response from server: \n {recv_json}")

            return recv_json
        except zmq.ZMQError as e:
            raise zmq.ZMQError(e)
        except Exception:
            print(traceback.format_exc())

    def get_plan(self, plan: json) -> json:
        try:
            plan_id:int = plan["plan ID"]
            payload = {
                "request": "get plan",
                "plan ID": plan_id
            }

            print("Sent 'Get plan' request. Awaiting response.....")
            self.service_socket.send_string(json.dumps(payload))
            recv_msg = self.service_socket.recv_string()
            json_msg = json.loads(recv_msg)
            print(f"'Get plan' response from server: \n {json_msg}") 
            return json_msg
        except zmq.ZMQError as e:
            raise zmq.ZMQError(e)


    def accept_plan(self, plan: json) -> None:
        payload = {
            "request": "accept plan",
            "plan ID": plan["plan ID"]
        }

        print("Sent 'Accept Plan' request. Awaiting response.....")
        self.service_socket.send_string(json.dumps(payload))
        recv_msg = self.service_socket.recv_string()
        json_msg = json.loads(recv_msg)
        print(f"'Accept Plan' response from server: \n {json_msg}") 
        
    def activate_plan(self, plan: json) -> None:
        payload = {
            "request": "activate plan",
            "plan ID": plan["plan ID"]
            #"withdraw plan": 50.0,
        }

        print("Sent 'Activate Plan' request. Awaiting response.....")
        self.service_socket.send_string(json.dumps(payload))
        recv_msg = self.service_socket.recv_string()
        json_msg = json.loads(recv_msg)
        print(f"'Activate Plan' response from server: \n {json_msg}") 

    def end_plan(self, plan: str) -> None:
        
        payload = {
            "request": "end plan",
            "plan ID": plan
        }

        print("Sent 'End Plan' request. Awaiting response.....")
        self.service_socket.send_string(json.dumps(payload))
        recv_msg = self.service_socket.recv_string()
        json_msg = json.loads(recv_msg)
        print(f"'End Plan' response from server: \n {json_msg}") 

    def cancel_plan(self, plan: json) -> None:
        payload = {
            "request": "cancel plan",
            "plan ID": plan["plan ID"]
        }

        print("Sent 'Cancel Plan' request. Awaiting response.....")
        self.service_socket.send_string(json.dumps(payload))
        recv_msg = self.service_socket.recv_string()
        json_msg = json.loads(recv_msg)
        print(f"'Cancel Plan' response from server: \n {json_msg}") 



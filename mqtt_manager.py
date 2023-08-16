from enum import Enum
import uuid
from data.config import MqttConfig, OperatorConfig, USSPConfig
from ussp import USSP
from threading import Event
import zmq
from zeromq_manager import ZeromqManager
from rounding_helpers import rounded_lat_lon, rounded_timestamp
from paho.mqtt.client import Client as PahoClient
import json, ssl, traceback, time
from agent_manager import Agent, AgentManager
from task import Task, TaskQueueItem, TaskStatus, TaskQueue
from drone_operator_manager import DroneOperator, DroneOperatorManager
from team_manager import Team, TeamManager, TeamType, TeamCommandMessage

class TaskNotSupported(Exception):
    """Exception raised for errors when a task is not supported"""
    def __init__(self, message="Task not Supported") -> None:
        self.message = message
        super().__init__(self.message)

class InvalidMQTTMessage(Exception):
    """Exception raised for errors when a MQTT message is not correct"""
    def __init__(self, message="Incorrect MQTT Message") -> None:
        self.message = message
        super().__init__(self.message)

class TaskName(str, Enum):
    MOVE_PATH   = "move-path"
    MOVE_TO     = "move-to"
    SEARCH_AREA = "search-area"

class AgentCommand(str, Enum):
    PING        = "ping"
    SIGNAL_TASK = "signal-task"
    START_TASK  = "start-task"

class TaskSignal(str, Enum):
    ABORT = "$abort"
    ENOUGH = "$enough"
    PAUSE = "$pause"
    CONTINUE = "$continue"


class MqttManager:
    def __init__(self, agent_manager, zeromq_manager, drone_operator_manager, team_manager, task_queue) -> None:
        self.base_topic: str = MqttConfig.BASE_TOPIC
        self.operator_id: str = OperatorConfig.OPERATOR_ID
        self.uas_id: str = OperatorConfig.UAS_ID
        self.operator_name: str = OperatorConfig.OPERATOR_NAME
        self.rate: float = OperatorConfig.RATE
        self.espg: int = OperatorConfig.EPSG
        self.position: tuple = OperatorConfig.POSITION
        self.levels: list = []
        self.tasks_available: list = []
        
        self.agent_manager: AgentManager = agent_manager
        self.zmq_manager: ZeromqManager = zeromq_manager
        self.drone_operator_manager: DroneOperatorManager = drone_operator_manager
        self.team_manager: TeamManager = team_manager
        self.task_queue: TaskQueue = task_queue
        self.broker: str = None
        self.port: int = None
        self.client: PahoClient = None

        self.ussp_exec_topic: str = None
        self.unique_ussp_topic: str = None
        self.ussp_event: Event = Event()
        self.current_working_task: Task = None

    def initialize(self) -> None:

        self.broker: str = MqttConfig.BROKER
        self.port: int = MqttConfig.PORT
        is_tsl_connection: bool = MqttConfig.IS_TSL_CONNECTION
        user: str = MqttConfig.USER
        password: str = MqttConfig.PASSWORD

        #MQTT TOPICS
        command_topic: str = f"{self.base_topic}/exec/command"
        team_command_topic: str = f"{self.base_topic}/team/command"

        tst_topic: str = f"{self.base_topic}/tst/command"

        ussp_exec_topic = USSPConfig.USSP_EXEC_TOPIC  
        self.ussp_exec_topic = f"{ussp_exec_topic}/response"

        #LIST of all topics, add new here :)
        topics: list = [command_topic, team_command_topic, tst_topic, self.ussp_exec_topic]
        client: PahoClient = PahoClient(self.operator_name)

        def on_connect(client, userdata, flags, rc) -> None:
            if rc == 0:
                print(f"Connected to MQTT Broker: {self.broker}:{self.port}")
                #Drone Operators own topics
                for topic in topics:
                    self.client.subscribe(topic)
                    print(f"Subscribing to {topic}")

                #Topics for the agents
                for agent in self.agent_manager.agents_list:
                    topic: str = f"waraps/unit/+/+/{agent}/heartbeat"
                    self.client.subscribe(topic)
                    print(f"Subscribing to {topic}")
                    self.client.message_callback_add(topic, self.search_and_create_agent)

                #topcis for other droneoperators (Teams of teams)
                for dop in self.drone_operator_manager.children_list:
                    topic: str = f"waraps/unit/+/+/{dop}/heartbeat"
                    self.client.subscribe(topic)
                    print(f"Subscribing to {topic}")
                    self.client.message_callback_add(topic, self.search_and_create_agent)    

                USSP.create_connection(self.client, f"{ussp_exec_topic}/command", self.operator_name)
            else :
                print(f"Error to connect : {rc}")


        def team_command_messages(client, userdata, msg):
            msg_json = json.loads(msg.payload.decode('utf-8'))
            print(msg_json)
            payload: dict = dict()

            try:
                command = msg_json["command"]
            except json.JSONDecodeError:
                print("No command in message")
                return

            if command == TeamCommandMessage.ADD_UNIT_TO_TEAM:
                team_name = msg_json["team"]
                unit = msg_json["unit"]

                #TODO try block som fångar None
                team = self.team_manager.get_team_by_name(team_name)
                team.add_agent(unit)

            elif command == TeamCommandMessage.REMOVE_ALL_TEAMS:
                self.team_manager.remove_all_teams()

            elif command == TeamCommandMessage.REMOVE_TEAM:
                team_name = msg_json["team"]
                self.team_manager.remove_team(team_name)

            elif command == TeamCommandMessage.REMOVE_UNIT_FROM_TEAM:
                team_name = msg_json["team"]
                unit = msg_json["unit"]

                team = self.team_manager.get_team_by_name(team_name)
                team.remove_agent(unit)

            elif command == TeamCommandMessage.SET_TEAM:
                team_name: str = msg_json["team"]
                type: TeamType = TeamType(msg_json["type"])
                unit_names: list = msg_json["units"] #TODO en list med namn, borde vara en med Agents object...?

                self.team_manager.create_new_team(team_name, type, unit_names)
                self.subscribe_to_list_of_agents(unit_names)


            else:
                #raise TaskNotSupported #TODO catch this, command istället för Task
                print("Command not supported")
                return


        def tst_command_messages(client, userdatam, msg):
            print("TST COMMAND")
            command = json.loads(msg.payload.decode('utf-8'))
            print(command)
            #print(command)
            #print(command["children"]) #list
            #print(json.dumps(command["children"][0]["children"], indent=4)) #dict

            tasks: list[dict] = command["children"][0]["children"]

            task = {
                "com-uuid": str(uuid.uuid4()),
                "command": "start-task",
                "execution-unit": self.operator_id,
                "sender": "c2",
                "task": {
                    "name": "move-to",
                    "params": {
                        "speed": "standard",
                        "waypoint": {
                            "latitude": 57.75822918691215,
                            "longitude": 16.699930136826847,
                            "altitude": 45,
                            "rostype": "GeoPoint"
                        }
                    }
                },
                "task-uuid": "5383a17d-5e62-40ab-ace3-dcb99cb6ec19"
            }

            for task in tasks:
                
                new_payload: dict = self.get_payload(task["name"])
                new_payload["task"]["params"]["waypoint"] = task["params"]["p"]
                new_payload["task-uuid"] = str(uuid.uuid4())
                print(new_payload)
                self.handle_task(json.dumps(msg=new_payload))



        #Bind callback functions
        client.on_connect = on_connect
        client.message_callback_add(command_topic, self.handle_command)
        client.message_callback_add(team_command_topic, team_command_messages)
        client.message_callback_add(tst_topic, tst_command_messages)

        client.message_callback_add(self.ussp_exec_topic, self.ussp_connection_callback)
        
        

        if is_tsl_connection:
            client.username_pw_set(user, password)
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

        self.client = client
    
    def run(self) -> None:
        """Starts the background loop and connect to the broker"""
        self.client.loop_start()
        self.client.connect(self.broker, self.port, 60)

    def forward_task_to_team_member(self, payload: json):
        selected_dop: DroneOperator = self.select_first_drone_operator()
        print(f"Could not find an Agent sent task to team member: {selected_dop.name}")
        topic: str = selected_dop.command_topic
        self.client.publish(topic, json.dumps(payload))

    def select_first_drone_operator(self):
        return self.drone_operator_manager.children[0]

    def send_signal_to_agent(self, signal_task: json, task: Task):
        payload = signal_task
        name = task.agent.meta['name']
        topic = f"{task.agent.meta['base_topic']}/exec/command"
        print(f"Sent Signal to Agent {name}")
        self.client.publish(topic, json.dumps(payload))
        print(f"Looking for agent to response...")

    def send_task_to_agent(self, task: Task):
        # TODO: switch back to ussp-based task by commenting back next line :)
        # payload = task.waraps_task
        payload = task.original_task
        name = task.agent.meta['name']
        topic = f"{task.agent.meta['base_topic']}/exec/command"
        print(f"Sent task to Agent {name}")
        self.client.publish(topic, json.dumps(payload))
        print(f"Looking for agent to response...")

    def subscribe_to_agent(self, meta_data: dict) -> None:
        agent_topic: str = f"{meta_data['base_topic']}/#"
        self.client.subscribe(agent_topic)
        self.client.message_callback_add(agent_topic, self.agent_sensor_data)
        print(f"Subscribing to {agent_topic}")

    def subscribe_to_drone_operator(self, meta_data: dict) -> None:
        agent_topic: str = f"{meta_data['base_topic']}/exec/#"
        self.client.subscribe(agent_topic)
        self.client.message_callback_add(agent_topic, self.agent_sensor_data)
        print(f"Subscribing to {agent_topic}")

    def agent_sensor_data(self, client, userdata, msg ) -> None:
        s = msg.topic.split("/")
        #name is always in 4th place if following the docs
        agent_name = s[4]
        agent_attri = s[-1]
        try:
            str_msg = msg.payload.decode('utf-8')
            agent = next(( a for a in self.agent_manager.all_agents if a.meta["name"] == agent_name )) #StopIteration
            json_msg = json.loads(str_msg) #ValueError
        except ValueError: 
            #if a "str_msg" is not a valid JSON object, like a cam_url etc.
            setattr(agent, agent_attri, str_msg)
        except StopIteration: #IS DRONE OPERATOR TODO: Is this used??
            json_msg = json.loads(str_msg) #ValueError
            if agent_attri == "heartbeat": 
                dop_list = [x for x in self.drone_operator_manager.children if x.name == agent_name]
                dop_list[0].levels = json_msg["levels"]
            elif agent_attri == "direct_execution_info":
                dop_list = [x for x in self.drone_operator_manager.children if x.name == agent_name]
                dop_list[0].tasks_available = json_msg["tasks-available"]
         
        else: #No error
            setattr(agent, agent_attri, json_msg)
        finally: #always runs
            # try:
            if agent_attri == "response":
                self.agent_manager.check_response(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, json_msg, agent_name)
                self.send_response(json_msg)
            elif agent_attri == "feedback":
                self.agent_manager.check_feedback(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, json_msg, agent_name)
                self.send_feedback(json_msg)

    def update_levels(self) -> None:
        """Updates 'LEVELS' that is used in heartbeat"""
        try:
            for agent in self.agent_manager.all_agents:
                for lvl in agent.heartbeat["levels"]:
                    if lvl not in self.levels:
                        self.levels.append(lvl)

            for dop in self.drone_operator_manager.children:
                for lvl in dop.levels:
                    if lvl not in self.levels:
                        self.levels.append(lvl)

        except AttributeError:
            return

    def update_tasks_available(self) -> None:
        """Updates 'tasks-available' that is used in direct_execution_info"""
        try:
            for agent in self.agent_manager.all_agents:
                for task in agent.direct_execution_info["tasks-available"]:
                    if task not in self.tasks_available:
                        self.tasks_available.append(task)

            for dop in self.drone_operator_manager.children:
                for task in dop.tasks_available:
                    if task not in self.tasks_available:
                        self.tasks_available.append(task)
        except AttributeError:
            return

    def send_direct_execution_info(self) -> None:
        payload = {
            "name":self.operator_name,
            "rate":self.rate,
            "type":"DirectExecutionInfo",
            "stamp":rounded_timestamp(),
            "tasks-available":self.tasks_available
        }

        self.client.publish(f"{self.base_topic}/direct_execution_info", json.dumps(payload))

    def send_heartbeat(self) -> None:
        payload = {
            "name":self.operator_name,
            "agent-type":"drone_operator",
            "agent-description":"drone_operator",
            "agent-model": "operator.controltower",
            "agent-uuid":self.operator_id,
            "levels":self.levels,
            "rate":self.rate,
            "stamp":rounded_timestamp(),
            "type":"HeartBeat"
            }

        self.client.publish(f"{self.base_topic}/heartbeat", json.dumps(payload))

    def send_position(self) -> None:
        lat, lon = self.position
        payload = { 
            "latitude":lat,
            "longitude":lon,
            "altitude":0,
            "type":"GeoPoint"
        }

        self.client.publish(f"{self.base_topic}/sensor/position", json.dumps(payload))

    def send_feedback(self, payload) -> None:
        self.client.publish(f"{self.base_topic}/exec/feedback", json.dumps(payload))

    def send_response(self, payload) -> None:
        self.client.publish(f"{self.base_topic}/exec/response", json.dumps(payload))

    def subscribe_to_list_of_agents(self, agent_list) -> None:
        for agent in agent_list:
            topic: str = f"waraps/unit/+/+/{agent}/#"
            self.client.subscribe(topic)
            print(f"Subscribe to {topic}")
            self.client.message_callback_add(agent, self.handle_command)
    
    def handle_command(self, client, userdata, msg):
        try:
            print(f"New task received!")
            try:
                json_str = msg.payload.decode("utf-8")
                json_msg = json.loads(json_str)
                print(json_msg)
            except json.JSONDecodeError:
                payload: dict = dict()
                payload["response"] = "failed"
                payload["fail-reason"] = "Could not Parse JSON"
                self.send_response(payload)
                return

            command = json_msg["command"]

            if command != AgentCommand.PING:
                payload = {
                    "agent-uuid": self.operator_id,
                    "com-uuid": str(uuid.uuid4()),
                    "fail-reason": "",
                    "response": "",
                    "response-to": json_msg["com-uuid"],
                    "task-uuid": json_msg["task-uuid"]
                }
                

            if command == AgentCommand.PING:
                payload = {
                    "agent-uuid": self.operator_id,
                    "com-uuid": str(uuid.uuid4()),
                    "response": "pong",
                    "response-to": json_msg["com-uuid"]
                }
                self.send_response(payload)

            elif command == AgentCommand.SIGNAL_TASK:
                signal = json_msg["signal"]
                task_uuid = json_msg["task-uuid"]
                try:
                    task_to_handle: Task = next( (_task for _task in self.agent_manager.running_tasks if task_uuid == _task.task_uuid) ) #StopIteration
                except StopIteration:
                    payload["response"] = "failed"
                    payload["fail-reason"] = "No agents is preforming this task"
                    self.send_response(payload)
                    return

                payload["response"] = "ok"
                payload["fail-reason"] = f"Signal Sent to Agent"

                if signal == TaskSignal.ABORT or signal == TaskSignal.ENOUGH:
                    task_to_handle.status = TaskStatus.FINISHED
                    self.send_signal_to_agent(json_msg, task_to_handle)
                elif signal == TaskSignal.PAUSE:
                    task_to_handle.status = TaskStatus.PAUSED
                    self.send_signal_to_agent(json_msg, task_to_handle)
                elif signal == TaskSignal.CONTINUE:
                    task_to_handle.status = TaskStatus.RUNNING
                    self.send_signal_to_agent(json_msg, task_to_handle)
                else:
                    payload["response"] = "failed"
                    payload["fail-reason"] = f"{signal} Not Supported"
                    self.send_response(payload)

            elif command == AgentCommand.START_TASK:

                task_name = json_msg["task"]["name"]
                task_list: list = [task["name"] for task in self.tasks_available]
                if task_name not in task_list:
                    payload["response"] = "failed"
                    payload["fail-reason"] = "Task not supported"
                    self.send_response(payload)
                    return

                task: Task = Task()

                if not self.task_queue.queue.full():
                    task.original_task = json_msg
                    queue_priority = 1 #lower is better
                    queue_item = TaskQueueItem(queue_priority, task)
                    self.task_queue.put_task_to_queue(queue_item)
                else:  
                    print("QUEUE FULL")
                    if self.drone_operator_manager.children:
                        dummy_agent: Agent = Agent({"name": "Drone From Team Member"}) #This name is used in the functions check_internal_feedback & check__internal_response in agent_manager.py
                        task.agent = dummy_agent
                        task.plan_to_task(self, json_msg)
                        self.agent_manager.running_tasks.append(task)
                        self.forward_task_to_team_member(json_msg)
                    else:
                        print("No agent was found to execute the task....")
                        print("Awaiting new task")
                        payload["response"] ="failed"
                        payload["fail-reason"] ="No agent was found to execute the task"
                        self.send_response(payload)


        except Exception:
            payload["response"] = "failed"
            payload["fail-reason"] = "Internal Error on the Drone Operator"
            self.send_response(payload)
            print(traceback.format_exc())

    def search_and_create_agent(self, client, userdata, msg) -> None:
        """Looks for the agent with the 'wildcard' topic and replaces it with a proper (no wildcard) topic and creatas a Agent object"""
        new_topic: str = msg.topic.replace("/heartbeat", "")
        agent_name = msg.topic.split("/")[4] #name is always in 4th place if following the docs
        json_msg = json.loads(msg.payload.decode("utf-8"))

        agent_type: str =json_msg["agent-type"]

        unsubcribe_topic: str = f"waraps/unit/+/+/{agent_name}/heartbeat"
        self.client.message_callback_remove(unsubcribe_topic)
        self.client.unsubscribe(unsubcribe_topic)
        print(f"{unsubcribe_topic} -> {new_topic}")
        if agent_type == "Drone_Operator":
            data: dict  = {}
            data["name"] = json_msg["name"]
            data["base_topic"] = new_topic
            data["command_topic"] = f"{data['base_topic']}/exec/command"
            data["agent_uuid"] = json_msg["agent-uuid"]
            self.subscribe_to_agent(data)
            dop = self.drone_operator_manager.create_new_drone_operator(data)
        else: #Is agent
            meta_data = {
                    "name": agent_name,
                    "base_topic": new_topic,
                    "agent-uuid": json_msg["agent-uuid"],
                    "busy": False
                }
            self.subscribe_to_agent(meta_data)
            self.agent_manager.create_new_agent(meta_data)

    def handle_task(self) -> None: #Started in an other thread from main.py
        while True:
            while not self.task_queue.queue.empty():
                if any(agent.meta["busy"] == False for agent in self.agent_manager.all_agents):
                    task_item: TaskQueueItem = self.task_queue.get_task_from_queue()
                    task: Task = task_item.item
                    self.current_working_task = task
                    prio: int = task_item.priority
                    task_name = task.original_task["task"]["name"]
                    params = task.original_task["task"]["params"]
                    selected_agent: Agent = self.agent_manager.select_closest_agent_that_is_non_busy(task_name, params)

                    if selected_agent is not None:
                        task.agent = selected_agent
                        task.task_uuid = task.original_task["task-uuid"]
                        waypoints: list[dict] = []
                        

                        if task_name == TaskName.MOVE_PATH:
                            for wp in params["waypoints"]:
                                lat = wp["latitude"]
                                lon = wp["longitude"]
                                waypoint = [lat, lon]
                                waypoints.append(waypoint)

                        elif task_name == TaskName.MOVE_TO:
                            lat = task.original_task["task"]["params"]["waypoint"]["latitude"]
                            lon = task.original_task["task"]["params"]["waypoint"]["longitude"]
                            alt = task.original_task["task"]["params"]["waypoint"]["altitude"]

                            waypoint = [lat, lon] 
                            waypoints.append(waypoint)

                        elif task_name == TaskName.SEARCH_AREA:
                            for wp in params["area"]:
                                lat = wp["latitude"]
                                lon = wp["longitude"]
                                waypoint = [lat, lon]
                                waypoints.append(waypoint)

                        else:
                            raise TaskNotSupported #TODO fångas inte :(
                        

                        #SPECIAL CASE FOR 'search-area' :(
                        if task_name != TaskName.SEARCH_AREA:

                            lat = selected_agent.position["latitude"]
                            lon = selected_agent.position["longitude"]
                            alt = selected_agent.position["altitude"]

                            
                            waypoint = [lat, lon]
                            waypoints.insert(0, waypoint)

                        payload_data: dict = {
                            "operator ID": self.operator_id,
                            "UAS ID": self.uas_id,
                            "EPSG": self.espg
                        }
                        try:
                            ##NEW##
                            USSP.request_height(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event)
                            USSP.request_plan(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, waypoints, payload_data)
                            USSP.get_plan(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, task.plan_id)
                            USSP.accept_plan(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, task.plan_id)
                            USSP.activate_plan(self.client, f"{self.unique_ussp_topic}/command", self.ussp_event, task.plan_id)
                            task.plan_to_task(self, task.original_task)
                            

                            ##old##
                            #the code for Zeromq
                            # task.ground_height = self.zmq_manager.request_height()
                            # request_plan_resp = self.zmq_manager.request_plan(waypoints, payload_data)
                            # task.set_plan_from_request(request_plan_resp)

                            # #print(f"Waiting for plan to active....")
                            # #time.sleep(request_plan_resp['delay'])

                            # task.ussp_plan = self.zmq_manager.get_plan(request_plan_resp)
                            # self.zmq_manager.accept_plan(request_plan_resp)
                            # self.zmq_manager.activate_plan(request_plan_resp)
                            # task.plan_to_task(self, task.original_task)
                            ##old END##

                        except zmq.ZMQError as e:
                            payload = {
                                "agent-uuid": self.operator_id,
                                "com-uuid": task.original_task["com-uuid"],
                                "fail-reason": "Could not communicate with USSP Service",
                                "response": "failed",
                                "response-to": task.original_task["com-uuid"],
                                "task-uuid": task.original_task["task-uuid"]
                            }

                            print("Could not communicate with USSP Service")
                            print(e)
                            selected_agent.meta["busy"] = False
                            self.send_response(payload)
                            return

                        self.send_task_to_agent(task)
                        self.agent_manager.running_tasks.append(task)
                        self.current_working_task = None


                    else: #NO AGENT TO DO THE TASK
                        time.sleep(2)
                        queue_item = TaskQueueItem(prio, task)
                        self.task_queue.put_task_to_queue(queue_item)
                else:
                    time.sleep(2)

            time.sleep(0.5)
   
    def get_payload(self, tst_name: str) -> dict:
        task_payloads = {
            "fly-to": { #move to
                "com-uuid": str(uuid.uuid4()),
                "command": "start-task",
                "execution-unit": self.operator_id,
                "sender": "c2",
                "task": {
                    "name": "move-to",
                    "params": {
                        "speed": "standard",
                        "waypoint": {
                            "latitude": 0.0,
                            "longitude": 0.0,
                            "altitude": 0,
                            "rostype": "GeoPoint"
                        }
                    }
                },
                "task-uuid": ""
            }
        }

        if tst_name in task_payloads:
            return task_payloads[tst_name]

    def ussp_connection_callback(self, client, userdata, msg):
        message: dict = json.loads(msg.payload.decode("utf-8"))
        dop_name: str = message.get("name")
        ussp_topic: str = message.get("ussp_topic")

        if not dop_name:
            print("No 'name' in response")
            return
        elif not ussp_topic:
            print("No 'ussp_topic' in response")
            return

        if dop_name == self.operator_name:
            self.unique_ussp_topic = ussp_topic

            self.client.unsubscribe(self.ussp_exec_topic)

            self.client.subscribe(f"{self.unique_ussp_topic}/response")

            self.client.message_callback_add(f"{self.unique_ussp_topic}/response", self.handle_ussp)
            print("Connection to USSP established")
    
    def handle_ussp(self, client, userdata, msg):
        try:
            message: dict = json.loads(msg.payload.decode("utf-8"))
        except json.decoder.JSONDecodeError as e:
            print(e)
            return
        reply = message.get("reply")

        print(reply)

        if reply == "query ground height":
            print(f"'query ground height' response from server: \n {message}")
            self.current_working_task.ground_height = message
            self.ussp_event.set()
        elif reply == "request plan":
            print(f"'request plan' response from server: \n {message}")
            self.current_working_task.set_plan_from_request(message)
            self.ussp_event.set()
        elif reply == "get plan":
            print(f"'Get plan' response from server: \n {message}")  
            self.current_working_task.ussp_plan = message
            self.ussp_event.set()
        elif reply == "accept plan":
            print(f"'Accept Plan' response from server: \n {message}") 
            self.ussp_event.set()
        elif reply == "activate plan":
            print(f"'Activate Plan' response from server: \n {message}") 
            self.ussp_event.set()
        elif reply == "end plan":
            print(f"'End Plan' response from server: \n {message}")
        elif reply == "cancel plan":
            pass
        elif reply == "Invalid Request":
            print("Invalid Request")
        else:
            print(f"'else' response from server: \n {message}")


##################################
##################################
##################################
##################################
##############                                                                                  
# _____ _____ _____ _____    _____ _____ _____ _____ _____ _____ _____ _____ _____ 
#|_   _|   __|  _  |     |  |   __|  |  |   | |     |_   _|     |     |   | |   __|
#  | | |   __|     | | | |  |   __|  |  | | | |   --| | | |-   -|  |  | | | |__   |
#  |_| |_____|__|__|_|_|_|  |__|  |_____|_|___|_____| |_| |_____|_____|_|___|_____|
#                                                                                  
######################################################################################################
######################################################################################################
######################################################################################################
######################################################################################################

    #skicka ofta
    def send_team_info(self, payload):
        pass
    
    #skickar ofta
    def send_team_manager_info(self, payload):
        #Team manager info which is information about a team manager and the status of the associated team task queue 16.3
        pass

    def send_team_response(self, payload):
        #teams which is info about all existing teams belonging to the specific team manager
        self.client.publish(f"{self.base_topic}/team/response", json.dumps(payload))



"""
#OLD
def listen_for_heartbeat(client, userdata, msg):
    try:
        msg_json = json.loads(msg.payload.decode('utf-8'))
        if msg_json["agent-type"] == "Drone_Operator": #Drone operator
            operator_allow: bool = False

            if any(dop == msg_json["name"] for dop in self.drone_operator_manager.children_list):
                operator_allow = True

            if operator_allow:
                if not any(dop.name == msg_json["name"] for dop in self.drone_operator_manager.children):
                    data: dict  = {}
                    data["name"] = msg_json["name"]
                    data["base_topic"] = msg.topic.replace("/heartbeat", "")
                    data["command_topic"] = data["base_topic"] + "/exec/command"
                    data["agent_uuid"] = msg_json["agent-uuid"]
                    self.subscribe_to_entity(client, data)
                    dop = self.drone_operator_manager.create_new_drone_operator(data)
                else:
                    return

        else: #Agent
            allow: bool = False

            if any(agent == msg_json["name"] for agent in self.agent_manager.agents_list):
                allow = True

            if allow:
                if any(lvl == "direct execution" for lvl in msg_json["levels"]): #If agent has "direct execution"
                    if not any(agent.meta['name'] == msg_json["name"] for agent in self.agent_manager.all_agents): #if the agent is not in the list of agents
                        
                        base_topic = msg.topic.replace("/heartbeat", "")

                        meta_data = {
                                "name": msg_json["name"],
                                "base_topic": base_topic,
                                "agent-uuid": msg_json["agent-uuid"],
                                "busy": False, 
                            }
                        self.subscribe_to_entity(client, meta_data)
                        agent = self.agent_manager.create_new_agent(meta_data)

    except KeyError:
        #if "levels" does not exist, probably only this drone operator itself
        return
    except JSONDecodeError:
        return
"""
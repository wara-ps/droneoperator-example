from dataclasses import dataclass
from datetime import datetime
import os
from task import Task, TaskStatus
import numpy as np
from zeromq_manager import ZeromqManager
from ussp import USSP
from paho.mqtt.client import Client as PahoClient
from threading import Event

@dataclass
class Agent():
    '''
    Saves everything an agent sends on MQTT
    some common attributes are: \n
    "heartbeat", "sensor_info", "position", "speed", "course", "heading", "direct_execution_info"
    '''
    def __init__(self, meta_data) -> None:
        self.meta: dict = meta_data


class AgentManager():
    def __init__(self, zmq_manager) -> None:
        try:
            self.zmq_manager: ZeromqManager = zmq_manager
            self.agents: list[Agent] = []
            self.running_tasks: list[Task] = []
            self.agents_list: list[str] = []

            try:
                str_of_agents = os.getenv("AGENTS")
            except Exception:
                str_of_agents = ""
            self.agents_list = str_of_agents.split(",")

        except FileNotFoundError:
            print("Did not find any allow/deny list")


    @property
    def all_agents(self) -> list:
        return self.agents

    def check_feedback(self, client: PahoClient, topic: str, event: Event, feedback: dict, agent_name) -> None:
        try:
            task: Task = next(( t for t in self.running_tasks if t.task_uuid == feedback["task-uuid"])) #StopIteration

            if feedback["status"] == "finished" or feedback["status"] == "failed" or feedback["status"] == "aborted" or feedback["status"] == "enough":
                task.agent.meta["busy"] = False
                task.status = TaskStatus.FINISHED
                task.task_completed = datetime.utcnow()
                #task.save_task_to_log()
                self.running_tasks.remove(task)

            if feedback["status"] == "finished":
                print(f"{task.agent.meta['name']} Completed the task")
                if task.agent.meta['name'] != "Drone From Team Member": USSP.end_plan(client, topic, event, task.plan_id)
            
            elif feedback["status"] == "failed":
                print(f"{task.agent.meta['name']} Failed the task")
                if task.agent.meta['name'] != "Drone From Team Member": USSP.end_plan(client, topic, event, task.plan_id)
            
            elif feedback["status"] == "aborted":
                print(f"{task.agent.meta['name']} Aborted the task")
                if task.agent.meta['name'] != "Drone From Team Member": USSP.end_plan(client, topic, event, task.plan_id)

            elif feedback["status"] == "enough":
                print(f"{task.agent.meta['name']} 'enoughed' the task")
                if task.agent.meta['name'] != "Drone From Team Member": USSP.end_plan(client, topic, event, task.plan_id)
        
        except StopIteration: #Not a task sent from this droneoperator
            agent = next(( a for a in self.all_agents if a.meta["name"] == agent_name ))
            if feedback["status"] == "finished" or feedback["status"] == "failed" or feedback["status"] == "aborted" or feedback["status"] == "enough":
                agent.meta["busy"] = False
            elif feedback["status"] == "running":
                agent.meta["busy"] = True

    def check_response(self, client: PahoClient, topic: str, event: Event, response: dict, agent_name):
        try:
            task: Task = next(( t for t in self.running_tasks if t.task_uuid == response["task-uuid"] )) #StopIteration

            if response["response"] == "running":
                print(f"{task.agent.meta['name']} Accepted the task")
                task.status = TaskStatus.RUNNING

            elif response["response"] == "finished":
                task.agent.meta["busy"] = False
                task.status = TaskStatus.FINISHED
                task.task_completed = datetime.utcnow()
                #task.save_task_to_log()
                self.running_tasks.remove(task)
                print(f"{task.agent.meta['name']} Completed the task")
                if task.agent.meta['name'] != "Drone From Team Member": USSP.end_plan(client, topic, event, task.plan_id)

            elif response["response"] == "ok":
                print(f"{task.agent.meta['name']} Preformed the Signal")
                if task.status is TaskStatus.FINISHED:
                    task.agent.meta["busy"] = False
                    USSP.end_plan(client, topic, event, task.plan_id)
                    self.running_tasks.remove(task)
            else:
                print(f"The agent did not accept the task: {response['fail-reason']}")
                USSP.end_plan(client, topic, event, task.plan_id)
                self.running_tasks.remove(task)
        
        except StopIteration: #Task not sent from this droneoperator
            agent = next(( a for a in self.all_agents if a.meta["name"] == agent_name ))
            if response["response"] == "finished" or response["response"] == "failed":
                agent.meta["busy"] = False
            elif response["response"] == "running":
                agent.meta["busy"] = True

    def filter_agents(self, cmd) -> list:
        """Returns a list of agents that support the task"""
        agents = [agent for agent in self.all_agents for task in agent.direct_execution_info["tasks-available"] if cmd == task["name"]]
        if not agents:
            print("No agents available")
        return agents

    def select_first_available_agent(self, agents: list) -> Agent:
        """Selects the first non-busy agent"""
        try:
            agent = next((agent for agent in agents if agent.meta["busy"] is False))    
        except StopIteration:
            print("No agent available")
            agent = None
        finally:
            return agent
            
    def select_closest_agent_that_is_non_busy(self, cmd, params) -> Agent:
        try:
            agents = self.filter_agents(cmd)  #Filter agents, only agents that can perform task
            agent = None
            non_busy_agents = self.__find_all_non_busy_agents(agents)
            if cmd == "move-to":
                first_position = params['waypoint']
            elif cmd == "move-path":
                first_position = params['waypoints'][0]  # First waypoint on path
            elif cmd == "search-area":
                first_position = params['area'][0]
            else:
                raise AttributeError('No waypoint or waypoints attribute in params')

            agent = self.__select_closest_agent(non_busy_agents, first_position)
            agent.meta["busy"] = True

        # except AttributeError:
        #     pass
        # except Exception:
        #     print(traceback.format_exc())
 
        finally:
            return agent

    @staticmethod
    def __find_all_non_busy_agents(agents: list) -> list:

        non_busy_agents = [agent for agent in agents if agent.meta["busy"] is False]

        if not non_busy_agents:
            print("No agent available")

        return non_busy_agents

    def __select_closest_agent(self, agents: list, position) -> Agent:
        '''
        Return the closest agent, returns None type if no agent available
        '''
        try:
            lat = position["latitude"]
            lon = position["longitude"]
            operator_waypoint = [lat, lon]

            non_sorted_dict = {}
            for index, agent in enumerate(agents):
                agent_lat = agent.position['latitude']
                agent_lon = agent.position['longitude']
                agent_waypoint = [agent_lat, agent_lon]
                non_sorted_dict[index] = self.calculate_haversine_distance(operator_waypoint, agent_waypoint)

            sorted_dict = dict(sorted(non_sorted_dict.items(), key=lambda item: item[1]))  # sort on value (distance)
            agent_number_to_return = list(sorted_dict.keys())[0]
            return agents[agent_number_to_return]
        except IndexError:
            return None

    @staticmethod
    def calculate_distance(operator_waypoint, agent_waypoint):
        dist = np.sqrt(
            (operator_waypoint[0] - agent_waypoint[0]) ** 2 + (operator_waypoint[1] - agent_waypoint[1]) ** 2)
        return dist

    @staticmethod
    def calculate_haversine_distance(operator_waypoint, agent_waypoint):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        Reference:
            https://stackoverflow.com/a/29546836/7657658
        """

        lat1, lon1 = operator_waypoint
        lat2, lon2 = agent_waypoint

        lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = np.sin(
            dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2

        c = 2 * np.arcsin(np.sqrt(a))
        km = 6371 * c
        return km

    def create_new_agent(self, meta_data) -> Agent:
        """Creates a new agent and append it to a list of agents! Returns the new agent"""
        new_agent = Agent(meta_data)
        self.agents.append(new_agent)
        return new_agent

    def update_agents(self, name):
        new_agents_list = [x for x in self.all_agents if name == x.meta["name"]]
        self.agents = new_agents_list







# ________  .____     ________   
# \_____  \ |    |    \______ \  
#  /   |   \|    |     |    |  \ 
# /    |    \    |___  |    `   \
# \_______  /_______ \/_______  /
#         \/        \/        \/ 

# def find_agent(self, cmd) -> Agent:
#     print(f"Fetching Agents for task -> {cmd}")
#     agents = self.filter_agents(cmd)
#     agent = self.select_first_available_agent(agents)
#     return agent

# def filter_agents(self, cmd) -> list[Agent]: #HÄR
#     """Returns a list of agents that support the task"""
#     agents = [agent for agent in self.all_agents for task in agent.direct_execution_info["tasks-available"] if cmd in task["name"]]
#     if not agents:
#         print("No agents available")
#     return agents

# def select_first_available_agent(self, agents: list) -> Agent:
#     """Selects the first non-busy agent"""
#     try:
#         agent = next((agent for agent in agents if agent.meta["busy"] is False))    
#     except StopIteration:
#         print("No agent available")
#         agent = None
#     finally:
#         return agent


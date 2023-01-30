import time
from agent_manager import AgentManager
from task import TaskQueue
from team_manager import TeamManager
from zeromq_manager import ZeromqManager
from mqtt_manager import MqttManager
from drone_operator_manager import DroneOperatorManager
from threading import Thread
from flask import Flask

def flask_app():
    app = Flask(__name__)
    @app.route('/')
    def hello_world():
        return 'OK'
    app.run()

def main():
    task_queue: TaskQueue = TaskQueue(10)
    zeromq = ZeromqManager()
    #zeromq.initialize()
    #zeromq.run()
    
    agent_manager = AgentManager(zeromq)
    drone_operator_manager = DroneOperatorManager()
    team_manager = TeamManager()

    mqtt = MqttManager(agent_manager, zeromq, drone_operator_manager, team_manager, task_queue)
    mqtt.initialize()
    mqtt.run() #PRODUCER THREAD
    
    handle_task_thread = Thread(target=mqtt.handle_task, daemon=True) 
    handle_task_thread.start() #CONSUMER THREAD

    #Main loop
    while True:
        mqtt.update_tasks_available()
        mqtt.update_levels()
        mqtt.send_heartbeat()
        mqtt.send_position()
        mqtt.send_direct_execution_info()
        time.sleep(mqtt.rate)

if __name__ == "__main__":
    #TODO får ingen feedback av teams av teams, kan vara för att det är olika verisoner?
    #TODO skicka response att en agent har lagts till i kön
    flask_app_thread = Thread(target=flask_app, daemon=True) 
    flask_app_thread.start()

    main()
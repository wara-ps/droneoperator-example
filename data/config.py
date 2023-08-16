from dataclasses import dataclass
import uuid
import os


@dataclass
class OperatorConfig:        
    "Variables used for configuring the Drone Operator"
    OPERATOR_NAME: str = os.getenv('OPERATOR_NAME')
    OPERATOR_ID: str = str(uuid.uuid4())
    UAS_ID: str = str(uuid.uuid4())
    EPSG: int = 5849
    RATE: float = 1.0 / 0.2 #5 seconds
    #Use 6 MAX 6 decimals for the POSITION
    #POSITION: tuple = (58.411617, 15.62124)
    POSITION: tuple = None

    POSITION = (float(os.getenv("START_LAT")), float(os.getenv("START_LON")))


'''
# Drone operator in Gothenburg
dataclass
class OperatorConfig:
    "Variables used for configuring the Drone Operator"
    OPERATOR_NAME: str = "drone_operator_gbg"
    OPERATOR_ID: str = str(uuid.uuid4())
    UAS_ID: str = str(uuid.uuid4())
    EPSG: int = 5849
    RATE: float = 1.0 / 0.2  # 5 seconds
    # Use 6 MAX 6 decimals for the POSITION
    POSITION: tuple = (57.708807, 11.942400)


# Drone operator in Kiruna
dataclass
class OperatorConfig:
    "Variables used for configuring the Drone Operator"
    OPERATOR_NAME: str = "drone_operator_kiruna"
    OPERATOR_ID: str = str(uuid.uuid4())
    UAS_ID: str = str(uuid.uuid4())
    EPSG: int = 5849
    RATE: float = 1.0 / 0.2  # 5 seconds
    # Use 6 MAX 6 decimals for the POSITION
    POSITION: tuple = (67.85266387351295, 20.2340282696178)
'''


@dataclass
class MqttConfig:
    "Variables used for configuring the MQTT client"
    BROKER: str = os.getenv('WARAPS_BROKER')
    PORT: int = int(os.getenv('WARAPS_PORT'))
    IS_TSL_CONNECTION: bool = bool(os.getenv('WARAPS_TLS_CONNECTION', 'False') == 'TRUE') #if "False", USER & PASSWORD will not be used
    USER: str = os.getenv('WARAPS_USERNAME')
    PASSWORD: str = os.getenv('WARAPS_PASSWORD')
    REAL_SIM: str = "real"
    DOMAIN: str = "ground"
    #REAL_SIM: str = "simulation"
    #DOMAIN: str = "air"
    BASE_TOPIC: str = f"waraps/unit/{DOMAIN}/{REAL_SIM}/{OperatorConfig.OPERATOR_NAME}"

@dataclass
class ZmqConfig:
    "Variables used for configuring the ZeroMQ client"
    #Used for the USSP service
    #SERVICE_SERVER: str = "ussp.waraps.org" 
    SERVICE_SERVER: str = os.getenv('SERVICE_SERVER')
    SERVICE_PORT: int = int(os.getenv('SERVICE_PORT'))
    SERVICE_URL: str = f"tcp://{SERVICE_SERVER}:{SERVICE_PORT}"


    #Used for PUB/SUB connection
    PUBLISH_SERVER: str = os.getenv('PUBLISH_SERVER')
    PUBLISH_PORT: int = int(os.getenv('PUBLISH_PORT'))
    PUBLISH_URL: str = f"tcp://{PUBLISH_SERVER}:{PUBLISH_PORT}"

@dataclass
class USSPConfig:
    USSP_EXEC_TOPIC: str = os.getenv("USSP_EXEC_TOPIC")
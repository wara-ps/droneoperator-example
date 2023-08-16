from enum import Enum
from agent_manager import Agent

class TeamType(Enum):
    SINGLE_AGENT_TASK = "single-agent-task"
    DIRECT_COMMAND = "direct-command"

class TeamCommandMessage(str, Enum):
    ADD_UNIT_TO_TEAM      = "add-unit-to-team"
    REMOVE_ALL_TEAMS      = "remove-all-teams"
    REMOVE_TEAM           = "remove-team"
    REMOVE_UNIT_FROM_TEAM = "remove-unit-from-team"
    SET_TEAM              = "set-team"

class Team():
    def __init__(self, name: str, type: TeamType, units: list = None) -> None:
        self.name: str = name
        self.type: TeamType = type
        self.units_names: list[str] = [] #list of agents to subscribe to
        if units:
            self.units_names = units
        self.units: list[Agent] = []

    def add_agent(self, agent: str) -> None:
        """Adds an agent to the team"""
        self.units_names.append(agent)

    def remove_agent(self, agent: str) -> None:
        """Removes an agent from the team"""
        try:
            self.units_names.remove(agent) #TODO det är en str, ska vara Agent
        except ValueError as e:
            print(e)
            #TODO skicka response
            #print(f"{agent.meta['name']} not in team")

class TeamManager():
    def __init__(self) -> None:
        self.teams: list[Team] = []

    def get_team_by_name(self, team_name: str):
        """Returns a 'Team' class object with the correct name otherwise None"""
        for team in self.teams:
            if team.name == team_name:
                return team
        return None

    def add_team(self, team: Team) -> None:
        """Adds a team to the team manager"""
        self.teams.append(team)

    def remove_team(self, team_name: str) -> None:
        """Removes a team from the team manager"""
        new_list = [x for x in self.teams if x.name != team_name]
        self.teams = new_list

    def remove_all_teams(self) -> None:
        """Remove all teams"""
        self.teams.clear()

    def create_new_team(self, name: str, _type: TeamType, units: list = None) -> Team:
        """Creates a new team and append it to a list of teams! Returns the new team"""
        new_team: Team = Team(name, _type, units)
        self.teams.append(new_team)
        return new_team

        



import unittest
from agent_manager import AgentManager


class AgentManagerTests(unittest.TestCase):
    """
    Drone operator position is configured in config file
    """

    msg = {
        "tasks-available": [{'name': 'move-to', 'signals': ['$abort', '$enough']},
                            {'name': 'move-path', 'signals': ['$abort', '$enough']}]
    }

    def test_select_closest_agent_that_is_non_busy_move_path(self):
        close_agent, far_away_agent, agent_manager = self.__setup_two_agents_and_agent_manager()

        params_move_path = {'speed': 'standard', 'waypoints': [
            {'latitude': 57.76645545817885, 'longitude': 16.72444981507556, 'altitude': 134.9, 'rostype': 'GeoPoint'},
            {'latitude': 57.7660044270175, 'longitude': 16.729328377442002, 'altitude': 134.9, 'rostype': 'GeoPoint'}]}

        # Assert that no agent are busy
        self.assertFalse(close_agent.meta["busy"])
        self.assertFalse(far_away_agent.meta["busy"])

        # Assert that move-path works
        agent_move_path = AgentManager.select_closest_agent_that_is_non_busy(agent_manager, "move-path",
                                                                             params_move_path)
        # Assert that selected agent is busy
        self.assertTrue(close_agent.meta["busy"])
        self.assertFalse(far_away_agent.meta["busy"])

        self.assertEqual(agent_move_path.meta["agent-uuid"], "ea7f6c3e-d757-11ec-9d64-0242ac120002")
        self.assertEqual(agent_move_path.meta["name"], "name1")

        self.assertEqual(agent_move_path.position["altitude"], 40.0)
        self.assertEqual(agent_move_path.position["latitude"], 57.8611363)
        self.assertEqual(agent_move_path.position["longitude"], 16.7805011)

    def test_select_closest_agent_that_is_non_busy_move_to(self):
        close_agent, far_away_agent, agent_manager = self.__setup_two_agents_and_agent_manager()

        params_move_to = {'speed': 'standard',
                          'waypoint': {'latitude': 57.70823988120551, 'longitude': 11.93838357925415, 'altitude': 134.9,
                                       'rostype': 'GeoPoint'}}

        # Assert that no agent are busy
        self.assertFalse(close_agent.meta["busy"])
        self.assertFalse(far_away_agent.meta["busy"])

        # Assert that move-to works
        agent_move_to = AgentManager.select_closest_agent_that_is_non_busy(agent_manager, "move-to",
                                                                           params_move_to)

        # Assert that selected agent is busy
        self.assertTrue(close_agent.meta["busy"])
        self.assertFalse(far_away_agent.meta["busy"])

        self.assertEqual(agent_move_to.meta["agent-uuid"], "ea7f6c3e-d757-11ec-9d64-0242ac120002")
        self.assertEqual(agent_move_to.meta["name"], "name1")

        self.assertEqual(agent_move_to.position["altitude"], 40.0)
        self.assertEqual(agent_move_to.position["latitude"], 57.8611363)
        self.assertEqual(agent_move_to.position["longitude"], 16.7805011)

    def __setup_two_agents_and_agent_manager(self):
        agent_manager = AgentManager()
        meta_data_1 = {
            "name": "name1",
            "topic": "topic1",
            "agent-uuid": "ea7f6c3e-d757-11ec-9d64-0242ac120002",
            "busy": False,
        }

        meta_data2 = {
            "name": "name2",
            "topic": "topic1",
            "agent-uuid": "5c2bb680-d780-11ec-9d64-0242ac120002",
            "busy": False,
        }

        close_agent_position = {
            "altitude": 40.0,
            "latitude": 57.8611363,
            "longitude": 16.7805011}

        far_away_agent_position = {
            "altitude": 40.0,
            "latitude": 58.7611363,
            "longitude": 17.6805011}

        close_agent = agent_manager.create_new_agent(meta_data_1)
        far_away_agent = agent_manager.create_new_agent(meta_data2)

        setattr(close_agent, "direct_execution_info", self.msg)
        setattr(close_agent, "position", close_agent_position)

        setattr(far_away_agent, "direct_execution_info", self.msg)
        setattr(far_away_agent, "position", far_away_agent_position)

        return close_agent, far_away_agent, agent_manager


if __name__ == '__main__':
    unittest.main()

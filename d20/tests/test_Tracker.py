import unittest
from unittest import mock

from d20.Manual.Trackers import (NPCTracker,
                                 PlayerTracker,
                                 CloneTracker,
                                 PlayerState)

from d20.Manual.Config import Configuration
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  registerPlayer,
                                  registerNPC)
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.Manual.Facts import loadFacts


loadFacts()


@registerPlayer(
    name="TrackerTestPlayer",
    description="Tracker Test Player",
    creator="",
    version="0.1",
    engine_version="0.1",
    interests=['mimetype'])
class TrackerTestPlayer(PlayerTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleFact(self, **kwargs):
        pass

    def handleHypothesis(self, **kwargs):
        pass


@registerNPC(
    name="TrackerTestNPC",
    description="Tracker Test NPC",
    creator="",
    version="0.1",
    engine_version="0.1"
)
class TrackerTestNPC(NPCTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleData(self, **kwargs):
        pass


class TestPlayerTracker(unittest.TestCase):
    def testTrackerCreation(self):
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        players = verifyPlayers([], Configuration())
        player = players[0]
        with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
            tracker = PlayerTracker(id=0,
                                    player=player,
                                    rpcServer=rpcServer,
                                    asyncData=asyncData)

            self.assertEqual(tracker.state, PlayerState.stopped)
            clone = tracker.createClone()
            self.assertIsInstance(clone, CloneTracker)
            saveData = tracker.save()
            PlayerTracker.load(
                saveData, player, rpcServer, asyncData)

    def testNPCTrackerCreation(self):
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        npcs = verifyNPCs([], Configuration())
        npc = npcs[0]
        with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
            tracker = NPCTracker(id=0,
                                 npc=npc,
                                 rpcServer=rpcServer,
                                 asyncData=asyncData)

            self.assertEqual(tracker.state, PlayerState.stopped)
            saveData = tracker.save()
            NPCTracker.load(saveData, npc, rpcServer, asyncData)

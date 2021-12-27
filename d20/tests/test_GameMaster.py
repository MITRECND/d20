import unittest
from unittest import mock
import argparse
import os
import tempfile
import pytest

from d20.Manual.Exceptions import PlayerCreationError
from d20.Manual.GameMaster import GameMaster
from d20.Manual.RPC import (
    Entity,
    EntityType,
    RPCStreamCommands,
    RPCCommands,
    RPCStartStreamRequest,
    RPCStopStreamRequest,
    RPCRequest)
from d20.Manual.Facts import loadFacts
from d20.Manual.Templates import registerNPC, NPCTemplate


loadFacts()

args_ex = argparse.Namespace(
    config=None,
    debug=True,
    dump_objects=None,
    extra_actions=[],
    extra_facts=[],
    extra_npcs=[],
    extra_players=[],
    extra_screens=[],
    file=None,
    backstory_facts=None,
    backstory_facts_path=None,
    info_player=None,
    list_npcs=False,
    list_players=False,
    list_screens=False,
    load_file=None,
    save_file=None,
    temporary='/tmp/d20-test',
    use_screen='json',
    verbose=False,
    version=False)


class testGameMaster(unittest.TestCase):
    def setUp(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        self.testfile = tf.name
        tf.close()

        self.args = args_ex
        self.args.file = self.testfile

    def tearDown(self):
        os.remove(self.testfile)
        del self.testfile

    def testGameMasterInsufficientArgs(self):
        with self.assertRaises(TypeError):
            GameMaster()

    def testGameMasterNoFile(self):
        with self.assertRaises(TypeError):
            del self.args.file
            GameMaster(options=self.args)

    def testGameMaster(self):
        gm = GameMaster(options=self.args)

        self.assertEqual(len(gm.objects), 1)
        self.assertGreater(len(gm.npcs), 0)
        self.assertGreater(len(gm.screens), 0)

        gm.cleanup()

    # def testLoad(self):
    #     gm = GameMaster(options=self.args)
    #     mock_npc = mock.MagicMock()
    #     mock_npc.name = "HashNPC"
    #     save_state = {
    #             "npcs": [mock_npc]
    #         }
    #     gm.save_state = save_state
    #     gm.registerNPCs(True)


class testGameMasterHandlers(unittest.TestCase):
    def setUp(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        self.testfile = tf.name
        tf.close()

        self.args = argparse.Namespace(
            config=None,
            debug=True,
            dump_objects=None,
            extra_actions=[],
            extra_facts=[],
            extra_npcs=[],
            extra_players=[],
            extra_screens=[],
            file=self.testfile,
            info_player=None,
            list_npcs=False,
            list_players=False,
            list_screens=False,
            load_file=None,
            save_file=None,
            temporary='/tmp/d20-test',
            use_screen='json',
            verbose=False,
            version=False)

        self.gm = GameMaster(options=self.args)
        #  Mock RPC so calls to it don't matter
        self.gm.rpc = mock.Mock()

    def tearDown(self):
        self.gm.cleanup()

    def testFactStreamHandlers(self):
        fact_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.factStream,
            args={'fact_types': fact_types, 'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleFactStreamStart(msg)

        for ft in fact_types:
            self.assertIn(ft, self.gm.factStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleFactStreamStop(msg)

        for ft in fact_types:
            self.assertEqual(list(), self.gm.factStreamList[ft])

    def testHypStreamHandlers(self):
        hyp_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.hypStream,
            args={'hyp_types': hyp_types, 'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleHypStreamStart(msg)

        for ft in hyp_types:
            self.assertIn(ft, self.gm.hypStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleHypStreamStop(msg)

        for ft in hyp_types:
            self.assertEqual(list(), self.gm.hypStreamList[ft])

    def testChildFactStreamHandlers(self):
        fact_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childFactStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'fact_types': fact_types,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildFactStreamStart(msg)

        for ft in fact_types:
            self.assertIn(ft, self.gm.factStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleFactStreamStop(msg)

        for ft in fact_types:
            self.assertEqual(list(), self.gm.factStreamList[ft])

    def testChildHypStreamHandlers(self):
        hyp_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childHypStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'types': hyp_types,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildHypStreamStart(msg)

        for ft in hyp_types:
            self.assertIn(ft, self.gm.hypStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleHypStreamStop(msg)

        for ft in hyp_types:
            self.assertEqual(list(), self.gm.hypStreamList[ft])

    def testChildObjectStreamHandlers(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childObjectStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildObjectStreamStart(msg)

        self.assertIn(msg, self.gm.objectStreamList)

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleChildObjectStreamStop(msg)

        self.assertEqual(list(), self.gm.objectStreamList)

    def testhandleAddObject1(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)

        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': u'\u221a25',  # <- utf-8
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)

    def testhandleAddObject2(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                # 'encoding': None
            }
        )

        self.gm.handleAddObject(msg)
        self.gm.rpc.sendErrorResponse.assert_called_once_with(
            msg, reason="'Namespace' object has no attribute 'encoding'")

    def testhandleAddObject3(self):
        e = Entity(EntityType.npc, 1, 1)
        msg1 = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        e = Entity(EntityType.npc, 2, 1)
        msg2 = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg1)
        self.gm.rpc.sendOKResponse.assert_called_with(
            msg1, result={'object_id': 1}
        )

        self.gm.handleAddObject(msg2)
        self.gm.rpc.sendOKResponse.assert_called_with(
            msg2, result={'object_id': 1}
        )

    @mock.patch('d20.Manual.BattleMap.FileObject.__init__')
    def testhandleAddObject4(self, FileObjectInit):
        error_string = "mock_type error"
        FileObjectInit.side_effect = TypeError(error_string)

        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)
        self.gm.rpc.sendErrorResponse.assert_called_with(
            msg,
            reason="Unable to track object: %s" % (error_string)
            )


def testGameMasterInitKwargs(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "test"
    gm = GameMaster(extra_players='test',
                    extra_npcs='test',
                    extra_backstories='test',
                    extra_screens='test',
                    options=args)
    assert gm.extra_players == 'test'
    assert gm.extra_npcs == 'test'
    assert gm.extra_backstories == 'test'
    assert gm.extra_screens == 'test'

    with pytest.raises(TypeError) as excinfo:
        gm = GameMaster(test='test')
    assert str(excinfo.value) == "test is an invalid keyword argument"

    del args.temporary
    with pytest.raises(RuntimeError) as excinfo:
        gm = GameMaster(options=args)
    assert str(excinfo.value) == "Expected temporary directory to be" \
        " specified in options"


def testBackStoryFactLoad1(monkeypatch):
    mockBSF = mock.Mock()
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mockBSF)

    args = args_ex
    args.backstory_facts = """
    facts:
        - name: BulkAnalyzeFact
          arguments:
            directory: /path/to/files
            recursive: False
            enable: True
        - name: VTDownloadFact
          arguments:
            vt_api_key: your_api_key
            filehash: hash_to_lookup_and_download_for_analysis
            enable: False
    """

    gm = GameMaster(options=args)
    mockBSF.assert_called()
    gm.cleanup()


def testBackStoryFactPathLoad2(monkeypatch):
    mockBSF = mock.Mock()
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mockBSF)

    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.write(b"""
        facts:
            - name: BulkAnalyzeFact
              arguments:
                directory: /path/to/files
                recursive: False
                enable: True
            - name: VTDownloadFact
              arguments:
                vt_api_key: your_api_key
                filehash: hash_to_lookup_and_download_for_analysis
                enable: False
    """)

    tf.close()
    args = args_ex
    args.backstory_facts_path = tf.name

    gm = GameMaster(options=args)
    mockBSF.assert_called()
    os.remove(tf.name)
    gm.cleanup()


def testFileOpenException(monkeypatch):
    exception_mock = mock.Mock(return_value=Exception)
    mock1 = mock.Mock()
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    args = args_ex
    args.file = tf.name

    with monkeypatch.context() as m:
        m.setattr('builtins.open', exception_mock)
        m.setattr('d20.Manual.GameMaster.LOGGER.exception', mock1)
        with pytest.raises(SystemExit):
            GameMaster(options=args)
        os.remove(tf.name)


def testRegisterNPCsError(monkeypatch, caplog):
    mock1 = mock.Mock()
    mock_exception = mock.Mock(side_effect=Exception)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerDirectoryHandler",
                        mock1)

    @registerNPC(
        name="TestNPC",
        description="Raises exception on init",
        creator="",
        version="0.1",
        engine_version="0.1"
    )
    class RegTestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            raise Exception

        def handleData(self, **kwargs):
            pass

    args = args_ex
    args.backstory_facts = "test"
    GameMaster(options=args)
    assert "Unable to create NPC TestNPC ... skipping" in caplog.text

    monkeypatch.setattr("d20.Manual.Trackers.NPCTracker.createNPC",
                        mock_exception)
    GameMaster(options=args)
    assert "Unexpected issue creating NPC" in caplog.text


def testRegisterRegisterBackStories(monkeypatch):
    mock1 = mock.Mock()
    mock_backstory = mock.Mock()
    mock_backstory.name = "test"
    mock_verifyBackstory = mock.Mock(return_value=[mock_backstory])
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerDirectoryHandler",
                        mock1)
    monkeypatch.setattr("d20.BackStories.verifyBackStories",
                        mock_verifyBackstory)

    args = args_ex
    args.backstory_facts = "test"
    save = {'backstories': [{'name': 'test'}]}
    gm = GameMaster(options=args, save_state=save)
    gm.registerBackStories(True)
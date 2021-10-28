import unittest
from unittest import mock
from argparse import Namespace

from d20.Manual.Console import (ConsoleInterface, NPCConsole, PlayerConsole)
from d20.Manual.Exceptions import (ConsoleError, WaitTimeoutError)
from d20.Manual.RPC import (RPCResponse,
                            RPCCommands,
                            RPCResponseStatus,
                            RPCStreamCommands)

from d20.Manual.Facts import (Fact, loadFacts)

loadFacts()

from d20.Manual.Facts import MD5HashFact  # type: ignore # noqa: 402


class TestConsoleInterface(unittest.TestCase):
    def setUp(self):
        self.dhandler = mock.Mock()
        type(self.dhandler).myDir = \
            mock.PropertyMock(return_value='test')
        self.rpcClient = mock.Mock()

        self.tracker = mock.Mock()
        type(self.tracker).memory = \
            mock.PropertyMock(return_value={'test': 'test'})
        type(self.tracker).name = \
            mock.PropertyMock(return_value="Console Test")
        self.asyncData = mock.Mock()

    def _createConsole(self):
        return ConsoleInterface(
            id=0,
            directoryHandler=self.dhandler,
            rpc_client=self.rpcClient,
            asyncData=self.asyncData,
            config=dict())

    @mock.patch("d20.Manual.Console.LOGGER")
    def testConsoleCreation(self, logger):
        logger.critical = mock.Mock()
        with self.assertRaises(KeyError):
            ConsoleInterface(id=0, tracker=self.tracker)
        logger.critical.assert_called_with(
            "Expected argument not passed to init", exc_info=True)

    def testAsync(self):
        console = self._createConsole()
        console.async_

    def testRPCCalls(self):
        console = self._createConsole()
        console._noop()
        self.rpcClient.sendAndIgnore.assert_called_with(
            command=RPCCommands.noop
        )

        console.print('foo')
        self.rpcClient.sendAndIgnore.assert_called_with(
            command=RPCCommands.print,
            args={'args': ('foo',), 'kwargs': dict()}
        )

        with self.assertRaises(ValueError):
            console._addObject(
                b'data', 'creator-test', 1, None, None, None, None)

        with self.assertRaises(ValueError):
            console._addObject(
                b'data', 'creator-test', None, 1, None, None, None)

        with self.assertRaises(ValueError):
            console._addObject(
                b'data', 'creator-test', None, None, 1, None, None)

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(0, RPCResponseStatus.ok))
        console._addObject(
            b'data', 'creator-test', None, None, None, dict(), None
        )

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console._addObject(
                b'data', 'creator-test', None, None, None, dict(), None
            )

    def testRequests(self):
        console = ConsoleInterface(
            id=0,
            directoryHandler=self.dhandler,
            rpc_client=self.rpcClient,
            asyncData=self.asyncData,
            config={'http_proxy': 'http://no.such.proxy',
                    'https_proxy': 'http://no.such.proxy'})

        console.configureRequestsRetry(**{})
        with self.assertRaises(TypeError):
            console.configureRequestsSession(list())
        with self.assertRaises(ValueError):
            console.configureRequestsSession({'foo': 'bar'})
        console.configureRequestsSession({'verify': True})
        console.requests


class TestNPCConsole(unittest.TestCase):
    def setUp(self):
        self.dhandler = mock.Mock()
        type(self.dhandler).myDir = \
            mock.PropertyMock(return_value='test')
        self.rpcClient = mock.Mock()

        self.tracker = mock.Mock()
        type(self.tracker).memory = \
            mock.PropertyMock(return_value={'test': 'test'})
        type(self.tracker).name = \
            mock.PropertyMock(return_value="NPC Test")
        self.asyncData = mock.Mock()

    def _createConsole(self):
        return NPCConsole(id=0,
                          directoryHandler=self.dhandler,
                          rpc_client=self.rpcClient,
                          asyncData=self.asyncData,
                          config=dict(),
                          tracker=self.tracker)

    def testConsoleCreation(self):
        self._createConsole()

    def testDhandlerCalls(self):
        console = self._createConsole()
        self.assertEqual(console.myDirectory, 'test')
        console.createTempDirectory()
        self.dhandler.tempdir.assert_called_with()

    def testMemory(self):
        console = self._createConsole()
        self.assertEqual(console.memory, {'test': 'test'})

    def testaddObject(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.ok,
                                               result={'object_id': 1}))
        data = b"foo"
        console = self._createConsole()
        self.assertEqual(console.addObject(data), 1)
        self.rpcClient.sendAndWait.assert_called_with(
            args={'creator': 'NPC Test',
                  'parentObjects': None,
                  'object_data': b'foo',
                  'parentFacts': None,
                  'parentHyps': None,
                  'metadata': None,
                  'encoding': None},
            command=RPCCommands.addObject)

    def testaddObjectError(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.error,
                                               reason="Test"))
        data = b"foo"
        console = self._createConsole()
        with self.assertRaises(ConsoleError):
            console.addObject(data)

    def testaddFact(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.ok,
                                               result={'fact_id': 1}))
        fact = Fact()
        console = self._createConsole()

        with self.assertRaises(ValueError):
            console.addFact(fact)
        fact.addParentObject(0)
        console.addFact(fact)
        self.rpcClient.sendAndWait.assert_called_with(
            args={'fact': fact},
            command=RPCCommands.addFact)

    def testaddFactError(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.error,
                                               reason="Test"))
        fact = Fact(parentObjects=[0])
        console = self._createConsole()
        with self.assertRaises(ConsoleError):
            console.addFact(fact)

    def testaddHyp(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.ok,
                                               result={'hyp_id': 1}))
        hyp = Fact()
        console = self._createConsole()

        with self.assertRaises(ValueError):
            console.addHyp(hyp)

        hyp.addParentObject(0)
        console.addHyp(hyp)
        self.rpcClient.sendAndWait.assert_called_with(
            args={'hyp': hyp},
            command=RPCCommands.addHyp)

    def testaddHypError(self):
        type(self.rpcClient).sendAndWait = \
            mock.Mock(return_value=RPCResponse(0,
                                               RPCResponseStatus.error,
                                               reason="Test"))
        hyp = Fact(parentObjects=[0])
        console = self._createConsole()
        with self.assertRaises(ConsoleError):
            console.addHyp(hyp)


class TestPlayerConsole(unittest.TestCase):
    def setUp(self):
        self.dhandler = mock.Mock()
        type(self.dhandler).myDir = \
            mock.PropertyMock(return_value='test')
        self.rpcClient = mock.Mock()

        self.tracker = mock.Mock()
        type(self.tracker).memory = \
            mock.PropertyMock(return_value={'test': 'test'})
        type(self.tracker).name = \
            mock.PropertyMock(return_value="Player Test")
        self.asyncData = mock.Mock()

    def _createConsole(self):
        return PlayerConsole(
            id=0,
            directoryHandler=self.dhandler,
            rpc_client=self.rpcClient,
            asyncData=self.asyncData,
            clone_id=0,
            config=dict(),
            tracker=self.tracker,
            tainted=False)

    def testConsoleCreation(self):
        self._createConsole()

    def testPlayerConsole(self):
        console = self._createConsole()
        self.assertEqual(console.id, (0, 0))
        console.memory
        self.tracker.cloneMemory = mock.MagicMock(return_value={0: dict()})
        console.data

    def testRPC(self):
        console = self._createConsole()
        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    object=None
                )))
        self.assertEqual(console.getObject(0), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getObject(0)

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    object_list=None
                )))
        self.assertEqual(console.getAllObjects(), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getAllObjects()

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    fact=None
                )))
        self.assertEqual(console.getFact(0), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getFact(0)

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    hyp=None
                )))
        self.assertEqual(console.getHyp(0), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getHyp(0)

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    fact_list=None
                )))
        self.assertEqual(console.getAllFacts('md5'), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getAllFacts('md5')

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(
                    hyp_list=None
                )))
        self.assertEqual(console.getAllHyps('md5'), None)

        with self.assertRaises(ConsoleError):
            self.rpcClient.sendAndWait = mock.Mock(
                return_value=RPCResponse(
                    0, RPCResponseStatus.error, reason="Foo"))
            console.getAllHyps('md5')

    def testWaits(self):
        console = self._createConsole()
        self.tracker.clones = mock.MagicMock()
        self.rpcClient.getStream = mock.Mock(return_value=['msg1'])
        msgs = list(console._waitOn(0))
        self.rpcClient.getStream.assert_called_with(0)
        self.rpcClient.stopStream.assert_called_with(0)
        self.assertEqual(['msg1'], msgs)

        self.rpcClient.getStream = mock.Mock(
            return_value=[Namespace(result=Namespace(fact=None))])
        msgs = list(console.waitOnFacts('md5'))
        self.rpcClient.startStream.assert_called_with(
            command=RPCStreamCommands.factStream,
            args={'fact_types': ['md5'],
                  'only_latest': False}
        )

        self.rpcClient.getStream = mock.Mock(
            return_value=[Namespace(result=Namespace(hyp=None))])
        msgs = list(console.waitOnHyps('md5'))
        self.rpcClient.startStream.assert_called_with(
            command=RPCStreamCommands.hypStream,
            args={'hyp_types': ['md5'],
                  'only_latest': False}
        )

        with self.assertRaises(ValueError):
            list(console.waitOnChildFacts(facts='md5'))

        with self.assertRaises(ValueError):
            list(
                console.waitOnChildFacts(
                    object_id=1, fact_id=1, facts=['md5']))

        with self.assertRaises(TypeError):
            list(console.waitOnChildFacts(object_id=1))

        self.rpcClient.getStream = mock.Mock(
            return_value=[Namespace(result=Namespace(fact=None))])
        list(console.waitOnChildFacts(object_id=1, facts='md5'))
        self.rpcClient.startStream.assert_called_with(
            command=RPCStreamCommands.childFactStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'fact_types': ['md5'],
                  'only_latest': False}
        )

        with self.assertRaises(ValueError):
            list(console.waitOnChildHyps(types='md5'))

        with self.assertRaises(ValueError):
            list(
                console.waitOnChildHyps(
                    object_id=1, fact_id=1, types=['md5']))

        with self.assertRaises(TypeError):
            list(console.waitOnChildHyps(object_id=1))

        self.rpcClient.getStream = mock.Mock(
            return_value=[Namespace(result=Namespace(hyp=None))])
        list(console.waitOnChildHyps(object_id=1, types='md5'))
        self.rpcClient.startStream.assert_called_with(
            command=RPCStreamCommands.childHypStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'types': ['md5'],
                  'only_latest': False}
        )

        with self.assertRaises(ValueError):
            list(console.waitOnChildObjects())

        with self.assertRaises(ValueError):
            list(console.waitOnChildObjects(object_id=1, fact_id=1))

        self.rpcClient.getStream = mock.Mock(
            return_value=[Namespace(result=Namespace(object=None))])
        list(console.waitOnChildObjects(object_id=1))
        self.rpcClient.startStream.assert_called_with(
            command=RPCStreamCommands.childObjectStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'only_latest': False}
        )

        self.rpcClient.sendMessage = mock.Mock(return_value=0)
        self.rpcClient.waitForResponse = mock.Mock(
            return_value=Namespace(result=Namespace(fact=None)))
        fact = console.waitTillFact('md5')
        self.rpcClient.sendMessage.assert_called_once_with(
            command=RPCCommands.waitTillFact,
            args={'fact_type': ['md5'],
                  'last_fact': None}
        )
        self.rpcClient.waitForResponse.assert_called_with(0, 0)
        self.assertEqual(fact, None)

        self.rpcClient.waitForResponse = mock.Mock(
            return_value=None)
        with self.assertRaises(WaitTimeoutError):
            fact = console.waitTillFact('md5')

    def testinherited(self):
        console = self._createConsole()
        tainted_console = PlayerConsole(
            id=0,
            directoryHandler=self.dhandler,
            rpc_client=self.rpcClient,
            asyncData=self.asyncData,
            clone_id=0,
            config=dict(),
            tracker=self.tracker,
            tainted=True)

        self.rpcClient.sendAndWait = mock.Mock(
            return_value=RPCResponse(
                0, RPCResponseStatus.ok, result=Namespace(object_id=0)))
        object_id = console.addObject(b'data')
        self.assertEqual(object_id, 0)

        f = MD5HashFact(value='test')
        f.addParentObject(0)
        with self.assertRaises(ValueError):
            tainted_console.addFact(f)
        console.addFact(f)
        console.addHyp(f)

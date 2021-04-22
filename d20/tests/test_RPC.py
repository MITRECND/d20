import unittest
from unittest import mock
from argparse import Namespace
from d20.Manual.RPC import (RPCServer,
                            RPCRequest,
                            RPCResponse,
                            RPCCommands,
                            RPCStream,
                            RPCStreamCommands,
                            RPCResponseStatus,
                            RPCStartStreamRequest,
                            RPCStopStreamRequest,
                            Entity,
                            EntityType)


class TestRPC(unittest.TestCase):
    def setUp(self):
        self.rpcServer = RPCServer()
        self.stopRPC = False

        def idleFn(start):
            if self.stopRPC:
                return True
            else:
                return False

        self.rpcServer.registerIdleFunction(idleFn)

    def testRPCClient(self):
        client = self.rpcServer.createClient(EntityType.npc, entity_id=0)
        self.rpcServer.start()
        self.rpcServer.destroyClient(client.id)
        self.assertNotIn(client, self.rpcServer.clients)
        self.stopRPC = True

    def testRegisterHandler(self):
        with self.assertRaises(TypeError):
            self.rpcServer.registerHandler(RPCCommands.print, 'test')

        with self.assertRaises(TypeError):
            self.rpcServer.registerHandler('test', mock.Mock())

        with self.assertRaises(ValueError):
            self.rpcServer.registerHandler(
                RPCCommands.startStream, mock.Mock())

        handler = mock.Mock()
        self.rpcServer.registerHandler(RPCCommands.print, handler)
        self.assertIn(RPCCommands.print, self.rpcServer.handlers)
        self.assertEqual(self.rpcServer.handlers[RPCCommands.print], handler)

    def testRegisterStartHandler(self):
        with self.assertRaises(TypeError):
            self.rpcServer.registerStartStreamHandler(
                RPCStreamCommands.factStream, 'test')

        with self.assertRaises(TypeError):
            self.rpcServer.registerStartStreamHandler(
                'test', mock.Mock())

        stsh = mock.Mock()
        self.rpcServer.registerStartStreamHandler(
            RPCStreamCommands.factStream, stsh)

        self.assertIn(RPCStreamCommands.factStream,
                      self.rpcServer.startStreamHandlers)
        self.assertEqual(
            self.rpcServer.startStreamHandlers[RPCStreamCommands.factStream],
            stsh)

    def testRegisterStopHandler(self):
        with self.assertRaises(TypeError):
            self.rpcServer.registerStopStreamHandler(
                RPCStreamCommands.factStream, 'test')

        with self.assertRaises(TypeError):
            self.rpcServer.registerStopStreamHandler(
                'test', mock.Mock())

        stsh = mock.Mock()
        self.rpcServer.registerStopStreamHandler(
            RPCStreamCommands.factStream, stsh)

        self.assertIn(RPCStreamCommands.factStream,
                      self.rpcServer.stopStreamHandlers)
        self.assertEqual(
            self.rpcServer.stopStreamHandlers[RPCStreamCommands.factStream],
            stsh)

    def testPrintHandle(self):
        def handlePrint(msg):
            self.assertEqual(msg.entity.id, 0)
            self.assertEqual(msg.args.args, 'Test')
            self.rpcServer.sendResponse(msg, RPCResponseStatus.ok)
            self.stopRPC = True
        self.rpcServer.registerHandler(RPCCommands.print, handlePrint)
        self.rpcServer.start()
        client = self.rpcServer.createClient(EntityType.npc, entity_id=0)

        response = client.sendAndWait(RPCCommands.print,
                                      args={'args': 'Test'})

        self.assertIsInstance(response, RPCResponse)
        self.assertEqual(response.status, RPCResponseStatus.ok)

    def testStream(self):
        def handleStartStream(msg):
            result = {'test': 'test'}
            self.assertEqual(msg.entity.id, 0)
            self.rpcServer.sendResponse(msg,
                                        RPCResponseStatus.ok,
                                        result=result)

        def handleStopStream(msg):
            self.stopRPC = True

        self.rpcServer.registerStreamHandler(
            RPCStreamCommands.factStream,
            handleStartStream,
            handleStopStream)

        self.rpcServer.start()
        client = self.rpcServer.createClient(EntityType.npc, entity_id=0)

        stream_id = client.startStream(RPCStreamCommands.factStream)
        for msg in client.getStream(stream_id):
            self.assertEqual(msg.result.test, 'test')
            break
        client.stopStream(stream_id)


class TestRPCClasses(unittest.TestCase):
    def testEntity(self):
        e1 = Entity(EntityType.npc, 0, 0)
        e2 = Entity(EntityType.npc, 0, 0)
        e3 = Entity(EntityType.player, 0, 0, 0)
        self.assertEqual(e1, e2)
        self.assertNotEqual(e1, e3)
        self.assertTrue(e3.isPlayer)
        self.assertFalse(e1.isPlayer)
        self.assertEqual(str(e1), "npc-0")
        self.assertEqual(str(e3), "player-0-clone-0")

    def testRPCStream(self):
        with self.assertRaises(TypeError):
            RPCStream("Foo")

        with self.assertRaises(TypeError):
            RPCStream(RPCStreamCommands.factStream, args=list())

        RPCStream(RPCStreamCommands.factStream, args=dict())
        RPCStream(RPCStreamCommands.factStream, args=Namespace())

    def testRPCRequest(self):
        e1 = Entity(EntityType.npc, 0, 0)
        with self.assertRaises(TypeError):  # Fail due to entity type
            RPCRequest(type('foo', (), {}), RPCCommands.print)

        with self.assertRaises(TypeError):  # Fail due to command type
            RPCRequest(e1, 'foo')

        r1 = RPCRequest(e1, RPCCommands.print)
        r2 = RPCRequest(e1, RPCCommands.print)

        self.assertNotEqual(r1.id, r2.id)

    def testRPCStartStream(self):
        e1 = Entity(EntityType.player, 0, 0, 0)
        args = Namespace(**{'foo': 'bar'})
        r = RPCStartStreamRequest(e1, RPCStreamCommands.factStream, args=args)

        self.assertIsInstance(r.stream, RPCStream)
        self.assertEqual(r.stream.command, RPCStreamCommands.factStream)
        self.assertEqual(r.command, RPCCommands.startStream)
        self.assertEqual(r.stream.args, args)

    def testRPCStopStream(self):
        e1 = Entity(EntityType.player, 0, 0, 0)
        r = RPCStopStreamRequest(e1, 0)

        self.assertEqual(r.command, RPCCommands.stopStream)
        self.assertEqual(r.args.stream_id, 0)

    def testRPCResponse(self):
        with self.assertRaises(TypeError):
            RPCResponse(0, 'foo')

        with self.assertRaises(TypeError):
            RPCResponse(0, RPCResponseStatus.ok, result=list())

        with self.assertRaises(ValueError):
            RPCResponse(0, RPCResponseStatus.error)

        RPCResponse(0, RPCResponseStatus.ok)
        RPCResponse(0, RPCResponseStatus.error, reason="Test")

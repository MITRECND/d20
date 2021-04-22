import time
import queue
import threading
from argparse import Namespace
from enum import Enum

from d20.Manual.Logger import logging
from d20.Manual.Exceptions import StreamTimeoutError


LOGGER = logging.getLogger(__name__)


class RPCResponseStatus(Enum):
    ok = 1
    error = 2


class RPCCommands(Enum):
    print = 0
    addObject = 1
    addFact = 2
    getObject = 3
    getAllObjects = 4
    getFact = 5
    getAllFacts = 6
    startStream = 7
    stopStream = 8
    waitTillFact = 9
    addHyp = 10
    getHyp = 11
    getAllHyps = 12
    promote = 13
    noop = 14


class RPCStreamCommands(Enum):
    factStream = 1
    childFactStream = 2
    childObjectStream = 3
    hypStream = 4
    childHypStream = 5


class EntityType(Enum):
    npc = 0
    player = 1
    backstory = 2


class Entity:
    def __init__(self, entity_type, rpc_id, id, clone_id=None):
        self.entity_type = entity_type
        self.rpcClient = rpc_id
        self.id = id
        self.clone = clone_id

    def __eq__(self, other):
        if self.entity_type != other.entity_type:
            return False

        if self.id != other.id:
            return False

        if self.clone != other.clone:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        if self.isNPC:
            return "npc-%d" % (self.id)
        elif self.isPlayer:
            return "player-%d-clone-%d" % (self.id, self.clone)
        elif self.isBackStory:
            return "backstory-%d" % (self.id)
        else:
            return "unknown-%d" % (self.id)

    @property
    def isPlayer(self):
        if self.entity_type == EntityType.player:
            return True
        return False

    @property
    def isNPC(self):
        if self.entity_type == EntityType.npc:
            return True
        return False

    @property
    def isBackStory(self):
        if self.entity_type == EntityType.backstory:
            return True
        return False


class RPCStream:
    def __init__(self, command, args=None):
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands value for command")

        self.command = command
        self.args = None
        if args is not None:
            if isinstance(args, dict):
                self.args = Namespace(**args)
            elif isinstance(args, Namespace):
                self.args = args
            else:
                raise TypeError("Expected a dict or Namespace type for args")


class RPCRequest:
    __msg_counter_ = 0

    def __init__(self, entity, command, args=None):
        if not isinstance(entity, Entity):
            raise TypeError("Expected an instance of 'Entity' for entity")
        self.entity = entity

        if not isinstance(command, RPCCommands):
            raise TypeError("Expected an RPCCommands value for command")
        self.command = command

        self.args = None
        if args is not None:
            if isinstance(args, dict):
                self.args = Namespace(**args)
            elif isinstance(args, Namespace):
                self.args = args
            else:
                raise TypeError("Expected a dict or Namespace type for args")

        self.id = RPCRequest.generateMsgId()

    @staticmethod
    def generateMsgId():
        RPCRequest.__msg_counter_ += 1
        return RPCRequest.__msg_counter_


class RPCStartStreamRequest(RPCRequest):
    def __init__(self, entity, command, args=None):
        super().__init__(entity, RPCCommands.startStream)
        self.stream = RPCStream(command, args=args)


class RPCStopStreamRequest(RPCRequest):
    def __init__(self, entity, stream_id):
        super().__init__(entity, RPCCommands.stopStream,
                         args={'stream_id': stream_id})


class RPCResponse:
    def __init__(self, id, status, result=None, reason=None):
        self.id = id

        if not isinstance(status, RPCResponseStatus):
            raise TypeError("status must be a RPCResponseStatus type")

        self.status = status
        if status == RPCResponseStatus.error:
            if reason is None:
                raise ValueError(("Reason must be populated when status is "
                                  "set to 'error'"))
            self.reason = reason

        self.result = None
        if result is not None:
            if isinstance(result, dict):
                self.result = Namespace(**result)
            elif isinstance(result, Namespace):
                self.result = result
            else:
                raise TypeError("Expected a dict for result")


class RPCClient:
    client_id = 0

    def __init__(self, server_queue, entity_type, entity_id, clone_id=None):
        self.server_queue = server_queue
        self.client_queue = queue.Queue()
        self.id = RPCClient.generateClientId()
        self.entity = Entity(entity_type, self.id, entity_id, clone_id)
        self.msglist = dict()
        self.streams = dict()
        self.timeouts = set()
        self.ignores = set()
        self._stop = False
        self._respThread = threading.Thread(
            target=self.respThread,
            name='rpcClient.%d' % self.id)
        self._respThread.daemon = True
        self._respThread.start()

    def stop(self):
        self._stop = True

    def join(self):
        self._respThread.join()

    def respThread(self):
        while not self._stop:
            try:
                resp = self.client_queue.get_nowait()
            except queue.Empty:
                time.sleep(.01)
                continue
            except Exception:
                raise

            LOGGER.debug("Received Response")

            if not isinstance(resp, RPCResponse):
                LOGGER.error("Received malformed response")
                continue

            msg_id = resp.id

            # If this request timed out, ignore it
            if msg_id in self.timeouts:
                self.timeouts.remove(msg_id)
                continue

            # If this request doesn't care about a response
            if msg_id in self.ignores:
                self.ignores.remove(msg_id)
                continue

            if msg_id in self.streams.keys():
                self.streams[msg_id].put(resp)
            else:
                self.msglist[msg_id] = resp

    def startStream(self, command, args=None):
        request = RPCStartStreamRequest(self.entity,
                                        command,
                                        args=args)

        self.streams[request.id] = queue.Queue()

        # Streams are handled separately from regular messages
        # so don't ignore the response
        self.server_queue.put(request)
        return request.id

    def stopStream(self, stream_id):
        if stream_id not in self.streams.keys():
            raise RuntimeError("Attempt to stop untracked stream")

        request = RPCStopStreamRequest(self.entity,
                                       stream_id)
        # Remove stream information
        del self.streams[stream_id]

        # Response for this message is unimportant
        self.ignores.add(request.id)
        self.server_queue.put(request)

    def getStream(self, stream_id, timeout=None):
        if stream_id not in self.streams.keys():
            raise RuntimeError("Attempt to get untracked stream")

        while 1:
            try:
                msg = self.streams[stream_id].get(timeout=timeout)
                yield msg
            except queue.Empty:
                raise StreamTimeoutError()
            except Exception:
                LOGGER.exception(("Unexpected exception waiting "
                                  "for stream data"))
                raise StopIteration()

    def sendMessage(self, command, args, ignore=False):
        request = RPCRequest(entity=self.entity, command=command, args=args)

        if ignore:
            self.ignores.add(request.id)
        self.server_queue.put(request)
        return request.id

    def waitForResponse(self, msg_id, timeout=0):
        start = time.time()
        while 1:
            if timeout > 0 and time.time() - start > timeout:
                self.timeouts.add(msg_id)
                return None
            if msg_id not in self.msglist:
                time.sleep(.01)
                continue

            resp = self.msglist[msg_id]
            del self.msglist[msg_id]

            if (not isinstance(resp, RPCResponse) or
                    resp.status != RPCResponseStatus.ok):
                pass  # TODO FIXME XXX

            return resp

    def sendAndIgnore(self, command, args=None):
        msg_id = self.sendMessage(command, args, ignore=True)
        return msg_id

    def sendAndWait(self, command, args=None, timeout=0):
        msg_id = self.sendMessage(command, args)
        return self.waitForResponse(msg_id, timeout)

    def handleResponse(self, response):
        self.client_queue.put(response)

    @staticmethod
    def generateClientId():
        RPCClient.client_id += 1
        return RPCClient.client_id


class RPCServer:
    def __init__(self):
        self.server_queue = queue.Queue()
        self.clients = dict()
        self.streams = dict()
        self._stop = False
        self.handlers = dict()
        self.startStreamHandlers = dict()
        self.stopStreamHandlers = dict()
        self.idleFn = None
        self.rpc_thread = threading.Thread(
            target=self.runGame,
            name='rpcServer')

    def registerHandler(self, command, fn):
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        if not isinstance(command, RPCCommands):
            raise TypeError("Expected an RPCCommands instance")
        if command in [RPCCommands.startStream,
                       RPCCommands.stopStream]:
            raise ValueError(("Stream state handled internally, please "
                              "register stream handlers instead"))

        LOGGER.debug("Registering Handler for %s procedure" % command)
        self.handlers[command] = fn

    def registerHandlers(self, handlers):
        for (command, fn) in handlers:
            self.registerHandler(command, fn)

    def registerStartStreamHandler(self, command, fn):
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands instance")
        LOGGER.debug("Registering Start Stream Handler for %s procedure"
                     % command)
        self.startStreamHandlers[command] = fn

    def registerStopStreamHandler(self, command, fn):
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands instance")
        LOGGER.debug("Registering Stop Stream Handler for %s procedure"
                     % command)
        self.stopStreamHandlers[command] = fn

    def registerStreamHandler(self, command, start_fn, stop_fn):
        self.registerStartStreamHandler(command, start_fn)
        self.registerStopStreamHandler(command, stop_fn)

    def registerStreamHandlers(self, handlers):
        for (command, start_fn, stop_fn) in handlers:
            self.registerStreamHandler(command, start_fn, stop_fn)

    def registerIdleFunction(self, fn):
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        LOGGER.debug("Registering Idle Function")
        self.idleFn = fn

    def start(self):
        self.rpc_thread.start()

    def isAlive(self):
        return self.rpc_thread.isAlive()

    def join(self):
        return self.rpc_thread.join()

    def runGame(self):
        start = time.time()
        while not self._stop:
            try:
                msg = self.server_queue.get_nowait()
                start = time.time()
                self._idleCount = 0
            except queue.Empty:
                # Check time idle
                try:
                    self._stop = self.idleFn(start)
                except Exception:
                    raise
                time.sleep(.001)
                continue

            if not isinstance(msg, RPCRequest):
                LOGGER.error("Expected RPCRequest type message")
                continue

            if msg.entity.isPlayer:
                tstring = 'player'
            elif msg.entity.isNPC:
                tstring = 'npc'
            elif msg.entity.isBackStory:
                tstring = 'backstory'
            else:
                tstring = 'unknown'

            if msg.command != RPCCommands.noop:
                LOGGER.debug("Received %s Message %d from %s id %d"
                             % (msg.command, msg.id, tstring, msg.entity.id))

            try:
                command = msg.command

                if command == RPCCommands.startStream:
                    self.startStream(msg)
                elif command == RPCCommands.stopStream:
                    self.stopStream(msg)
                else:
                    if command not in self.handlers:
                        raise RuntimeError(
                            "No handler specified for command %s"
                            % (command))
                    self.handlers[command](msg)
            except Exception:
                LOGGER.exception("Issue running command")

    def stop(self):
        self._stop = True

    def startStream(self, msg):
        command = msg.stream.command
        if command not in self.startStreamHandlers:
            raise RuntimeError("No start handler defined for stream function")

        self.startStreamHandlers[command](msg)
        self.streams[msg.id] = msg

    def stopStream(self, msg):
        stream_id = msg.args.stream_id
        if stream_id not in self.streams:
            pass  # TODO FIXME return error or something

        request = self.streams[stream_id]
        command = request.stream.command

        if command not in self.stopStreamHandlers:
            raise RuntimeError("No stop handler defined for stream function")

        self.stopStreamHandlers[command](msg)

        del self.streams[request.id]
        self.sendResponse(msg, RPCResponseStatus.ok)

    def createClient(self, entity_type, entity_id, clone_id=None):
        LOGGER.debug("Generating RPC Client")
        client = RPCClient(self.server_queue, entity_type, entity_id, clone_id)
        self.clients[client.id] = client
        return client

    def destroyClient(self, client_id):
        LOGGER.debug("Destroying RPC client %d" % (client_id))
        client = self.clients[client_id]
        client.stop()
        client.join()
        del self.clients[client_id]

    def sendResponse(self, msg, status, result=None, reason=None):
        if not isinstance(msg, RPCRequest):
            raise TypeError("Expected an RPCRequest")
        response = RPCResponse(msg.id, status, result, reason)
        client_id = msg.entity.rpcClient
        self.clients[client_id].handleResponse(response)

    def sendErrorResponse(self, msg, reason):
        self.sendResponse(msg, RPCResponseStatus.error, reason=reason)

    def sendOKResponse(self, msg, result=None):
        self.sendResponse(msg, RPCResponseStatus.ok, result=result)

import time
import queue
import threading
from argparse import Namespace
from enum import Enum
from typing import (Callable, Optional, Dict, Union, Set,
                    List, Tuple, Type, Generator)

from d20.Manual.Logger import logging, Logger
from d20.Manual.Exceptions import StreamTimeoutError, RPCTimeoutError


LOGGER: Logger = logging.getLogger(__name__)


class RPCResponseStatus(Enum):
    ok: int = 1
    error: int = 2


class RPCCommands(Enum):
    print: int = 0
    addObject: int = 1
    addFact: int = 2
    getObject: int = 3
    getAllObjects: int = 4
    getFact: int = 5
    getAllFacts: int = 6
    startStream: int = 7
    stopStream: int = 8
    waitTillFact: int = 9
    addHyp: int = 10
    getHyp: int = 11
    getAllHyps: int = 12
    promote: int = 13
    noop: int = 14


class RPCStreamCommands(Enum):
    factStream: int = 1
    childFactStream: int = 2
    childObjectStream: int = 3
    hypStream: int = 4
    childHypStream: int = 5


class EntityType(Enum):
    npc: int = 0
    player: int = 1
    backstory: int = 2


class Entity:
    def __init__(self, entity_type: EntityType, rpc_id: int, id: int,
                 clone_id: Optional[int] = None) -> None:
        self.entity_type: EntityType = entity_type
        self.rpcClient: int = rpc_id
        self.id: int = id
        self.clone: Optional[int] = clone_id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False

        if self.entity_type != other.entity_type:
            return False

        if self.id != other.id:
            return False

        if self.clone != other.clone:
            return False

        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        if self.isNPC:
            return "npc-%d" % (self.id)
        elif self.isPlayer and self.clone is not None:
            return "player-%d-clone-%d" % (self.id, self.clone)
        elif self.isBackStory:
            return "backstory-%d" % (self.id)
        else:
            return "unknown-%d" % (self.id)

    @property
    def isPlayer(self) -> bool:
        if self.entity_type == EntityType.player:
            return True
        return False

    @property
    def isNPC(self) -> bool:
        if self.entity_type == EntityType.npc:
            return True
        return False

    @property
    def isBackStory(self) -> bool:
        if self.entity_type == EntityType.backstory:
            return True
        return False


class RPCStream:
    def __init__(self, command: RPCStreamCommands,
                 args: Optional[Union[Dict, Namespace]] = None) -> None:
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands value for command")

        self.command: RPCStreamCommands = command
        self.args: Optional[Union[Dict, Namespace]] = None
        if args is not None:
            if isinstance(args, dict):
                self.args = Namespace(**args)
            elif isinstance(args, Namespace):
                self.args = args
            else:
                raise TypeError("Expected a dict or Namespace type for args")


class RPCRequest:
    __msg_counter_: int = 0

    def __init__(self, entity: Entity, command: RPCCommands,
                 args: Optional[Union[Dict, Namespace]] = None) -> None:
        if not isinstance(entity, Entity):
            raise TypeError("Expected an instance of 'Entity' for entity")
        self.entity: Entity = entity

        if not isinstance(command, RPCCommands):
            raise TypeError("Expected an RPCCommands value for command")
        self.command: RPCCommands = command

        self.args: Optional[Union[Dict, Namespace]] = None
        if args is not None:
            if isinstance(args, dict):
                self.args = Namespace(**args)
            elif isinstance(args, Namespace):
                self.args = args
            else:
                raise TypeError("Expected a dict or Namespace type for args")

        self.id: int = RPCRequest.generateMsgId()

    @staticmethod
    def generateMsgId() -> int:
        RPCRequest.__msg_counter_ += 1
        return RPCRequest.__msg_counter_


class RPCStartStreamRequest(RPCRequest):
    def __init__(self, entity: Entity, command: RPCStreamCommands,
                 args: Optional[Union[Dict, Namespace]] = None) -> None:
        super().__init__(entity, RPCCommands.startStream)
        self.stream = RPCStream(command, args=args)


class RPCStopStreamRequest(RPCRequest):
    def __init__(self, entity: Entity, stream_id: int) -> None:
        super().__init__(entity, RPCCommands.stopStream,
                         args={'stream_id': stream_id})


class RPCResponse:
    def __init__(self, id: int, status: RPCResponseStatus,
                 result: Optional[Union[Namespace, Dict]] = None,
                 reason: Optional[str] = None) -> None:
        self.id: int = id

        if not isinstance(status, RPCResponseStatus):
            raise TypeError("status must be a RPCResponseStatus type")

        self.status: RPCResponseStatus = status
        if status == RPCResponseStatus.error:
            if reason is None:
                raise ValueError(("Reason must be populated when status is "
                                  "set to 'error'"))
            self.reason = reason

        self.result: Namespace
        if result is not None:
            if isinstance(result, dict):
                self.result = Namespace(**result)
            elif isinstance(result, Namespace):
                self.result = result
            else:
                raise TypeError("Expected a dict for result")


class RPCClient:
    client_id: int = 0

    def __init__(self, server_queue: queue.Queue, entity_type: EntityType,
                 entity_id: int, clone_id: Optional[int] = None) -> None:
        self.server_queue: queue.Queue = server_queue
        self.client_queue: queue.Queue = queue.Queue()
        self.id: int = RPCClient.generateClientId()
        self.entity: Entity = Entity(entity_type, self.id, entity_id, clone_id)
        self.msglist: Dict[int, RPCResponse] = dict()
        self.streams: Dict[int, queue.Queue] = dict()
        self.timeouts: Set = set()
        self.ignores: Set = set()
        self._stop: bool = False
        self._respThread: threading.Thread = threading.Thread(
            target=self.respThread,
            name='rpcClient.%d' % self.id)
        self._respThread.daemon = True
        self._respThread.start()

    def stop(self) -> None:
        self._stop = True

    def join(self) -> None:
        self._respThread.join()

    def respThread(self) -> None:
        while not self._stop:
            try:
                resp: RPCResponse = self.client_queue.get_nowait()
            except queue.Empty:
                time.sleep(.01)
                continue
            except Exception:
                raise

            LOGGER.debug("Received Response")

            if not isinstance(resp, RPCResponse):
                LOGGER.error("Received malformed response")
                continue

            msg_id: int = resp.id

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

    def startStream(self, command: RPCStreamCommands,
                    args: Optional[Dict] = None) -> int:
        request: RPCStartStreamRequest = RPCStartStreamRequest(self.entity,
                                                               command,
                                                               args=args)

        self.streams[request.id] = queue.Queue()

        # Streams are handled separately from regular messages
        # so don't ignore the response
        self.server_queue.put(request)
        return request.id

    def stopStream(self, stream_id: int) -> None:
        if stream_id not in self.streams.keys():
            raise RuntimeError("Attempt to stop untracked stream")

        request: RPCStopStreamRequest = RPCStopStreamRequest(self.entity,
                                                             stream_id)
        # Remove stream information
        del self.streams[stream_id]

        # Response for this message is unimportant
        self.ignores.add(request.id)
        self.server_queue.put(request)

    def getStream(self, stream_id: int,
                  timeout: Optional[int] = None
                  ) -> Generator[RPCResponse, None, None]:
        if stream_id not in self.streams.keys():
            raise RuntimeError("Attempt to get untracked stream")

        while 1:
            try:
                msg: RPCResponse = self.streams[stream_id].get(timeout=timeout)
                yield msg
            except queue.Empty:
                raise StreamTimeoutError()
            except Exception:
                LOGGER.exception(("Unexpected exception waiting "
                                  "for stream data"))
                raise StopIteration()

    def sendMessage(self, command: RPCCommands,
                    args: Optional[Union[Dict, Namespace]],
                    ignore: bool = False) -> int:
        request: RPCRequest = RPCRequest(entity=self.entity, command=command,
                                         args=args)

        if ignore:
            self.ignores.add(request.id)
        self.server_queue.put(request)
        return request.id

    def waitForResponse(self, msg_id: int,
                        timeout: int = 0) -> RPCResponse:
        start = time.time()
        while 1:
            if timeout > 0 and time.time() - start > timeout:
                self.timeouts.add(msg_id)
                raise RPCTimeoutError()
            if msg_id not in self.msglist:
                time.sleep(.01)
                continue

            resp: RPCResponse = self.msglist[msg_id]
            del self.msglist[msg_id]

            if (not isinstance(resp, RPCResponse) or
                    resp.status != RPCResponseStatus.ok):
                pass  # TODO FIXME XXX

            return resp

    def sendAndIgnore(self, command: RPCCommands,
                      args: Optional[Union[Dict, Namespace]] = None) -> int:
        msg_id: int = self.sendMessage(command, args, ignore=True)
        return msg_id

    def sendAndWait(self, command: RPCCommands,
                    args: Optional[Union[Dict, Namespace]] = None,
                    timeout: int = 0) -> RPCResponse:
        msg_id: int = self.sendMessage(command, args)
        return self.waitForResponse(msg_id, timeout)

    def handleResponse(self, response: RPCResponse) -> None:
        self.client_queue.put(response)

    @staticmethod
    def generateClientId() -> int:
        RPCClient.client_id += 1
        return RPCClient.client_id


class RPCServer:
    def __init__(self):
        self.server_queue: queue.Queue = queue.Queue()
        self.clients: Dict[int, RPCClient] = dict()
        self.streams: Dict = dict()
        self._stop: bool = False
        self.handlers: Dict[RPCCommands, Callable] = dict()
        self.startStreamHandlers: Dict[RPCStreamCommands, Callable] = dict()
        self.stopStreamHandlers: Dict[RPCStreamCommands, Callable] = dict()
        self.idleFn: Callable = None
        self.rpc_thread: threading.Thread = threading.Thread(
            target=self.runGame,
            name='rpcServer')

    def registerHandler(self, command: RPCCommands, fn: Callable) -> None:
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

    def registerHandlers(self,
                         handlers: List[Tuple[RPCCommands, Callable]]) -> None:
        for (command, fn) in handlers:
            self.registerHandler(command, fn)

    def registerStartStreamHandler(self, command: RPCStreamCommands,
                                   fn: Callable) -> None:
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands instance")
        LOGGER.debug("Registering Start Stream Handler for %s procedure"
                     % command)
        self.startStreamHandlers[command] = fn

    def registerStopStreamHandler(self, command: RPCStreamCommands,
                                  fn: Callable) -> None:
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        if not isinstance(command, RPCStreamCommands):
            raise TypeError("Expected an RPCStreamCommands instance")
        LOGGER.debug("Registering Stop Stream Handler for %s procedure"
                     % command)
        self.stopStreamHandlers[command] = fn

    def registerStreamHandler(self, command: RPCStreamCommands,
                              start_fn: Callable, stop_fn: Callable) -> None:
        self.registerStartStreamHandler(command, start_fn)
        self.registerStopStreamHandler(command, stop_fn)

    def registerStreamHandlers(self,
                               handlers: List[Tuple[RPCStreamCommands,
                                                    Callable,
                                                    Callable]]) -> None:
        for (command, start_fn, stop_fn) in handlers:
            self.registerStreamHandler(command, start_fn, stop_fn)

    def registerIdleFunction(self, fn: Callable) -> None:
        if not callable(fn):
            raise TypeError("Provided function doesn't look callable")
        LOGGER.debug("Registering Idle Function")
        self.idleFn = fn

    def start(self) -> None:
        self.rpc_thread.start()

    def isAlive(self) -> bool:
        return self.rpc_thread.isAlive()

    def join(self) -> None:
        return self.rpc_thread.join()

    def runGame(self) -> None:
        start: float = time.time()
        while not self._stop:
            try:
                msg: Type[RPCRequest] = self.server_queue.get_nowait()
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
                command: RPCCommands = msg.command

                if isinstance(msg, RPCStartStreamRequest) and \
                        command == RPCCommands.startStream:
                    self.startStream(msg)
                elif isinstance(msg, RPCStopStreamRequest) and \
                        command == RPCCommands.stopStream:
                    self.stopStream(msg)
                else:
                    if command not in self.handlers:
                        raise RuntimeError(
                            "No handler specified for command %s"
                            % (command))
                    self.handlers[command](msg)
            except Exception:
                LOGGER.exception("Issue running command")

    def stop(self) -> None:
        self._stop = True

    def startStream(self, msg: RPCStartStreamRequest) -> None:
        command: RPCStreamCommands = msg.stream.command
        if command not in self.startStreamHandlers:
            raise RuntimeError("No start handler defined for stream function")

        self.startStreamHandlers[command](msg)
        self.streams[msg.id] = msg

    def stopStream(self, msg: RPCStopStreamRequest) -> None:
        if isinstance(msg.args, Namespace):
            stream_id = msg.args.stream_id
            if stream_id not in self.streams:
                pass  # TODO FIXME return error or something

            request = self.streams[stream_id]
            command = request.stream.command

            if command not in self.stopStreamHandlers:
                raise RuntimeError("No stop handler defined for stream \
                                    function")

            self.stopStreamHandlers[command](msg)

            del self.streams[request.id]
            self.sendResponse(msg, RPCResponseStatus.ok)

    def createClient(self, entity_type: EntityType, entity_id: int,
                     clone_id: Optional[int] = None) -> RPCClient:
        LOGGER.debug("Generating RPC Client")
        client: RPCClient = RPCClient(self.server_queue, entity_type,
                                      entity_id, clone_id)
        self.clients[client.id] = client
        return client

    def destroyClient(self, client_id: int) -> None:
        LOGGER.debug("Destroying RPC client %d" % (client_id))
        client = self.clients[client_id]
        client.stop()
        client.join()
        del self.clients[client_id]

    def sendResponse(self, msg: RPCRequest, status: RPCResponseStatus,
                     result: Optional[Union[Namespace, Dict]] = None,
                     reason: Optional[str] = None) -> None:
        if not isinstance(msg, RPCRequest):
            raise TypeError("Expected an RPCRequest")
        response: RPCResponse = RPCResponse(msg.id, status, result, reason)
        client_id = msg.entity.rpcClient
        self.clients[client_id].handleResponse(response)

    def sendErrorResponse(self, msg: RPCRequest, reason: str) -> None:
        self.sendResponse(msg, RPCResponseStatus.error, reason=reason)

    def sendOKResponse(self, msg: RPCRequest, result:
                       Optional[Union[Namespace, Dict]] = None) -> None:
        self.sendResponse(msg, RPCResponseStatus.ok, result=result)

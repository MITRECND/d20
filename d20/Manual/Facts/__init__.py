import os
import time
import inspect

from collections.abc import Iterable
from collections import OrderedDict

from inspect import (Parameter,
                     Signature)
from typing import Optional, Dict, Set
from .Fields import FactField

from d20.Manual.Logger import logging
from d20.Manual.Utils import loadExtras

LOGGER = logging.getLogger(__name__)
RegisteredFactGroups: Dict[str, Set] = dict()
RegisteredFacts: Set = set()
__all__ = ["registerFact",
           "Fact",
           "RegisteredFacts",
           "RegisteredFactGroups",
           "resolveFacts",
           "isFact",
           "isFactGroup",
           "loadFacts"]


def isFact(arg):
    """Function to determine whether a string is a registered fact
    """
    if arg in RegisteredFacts:
        return True

    return False


def isFactGroup(arg):
    """Function to determine whether a string is a registered fact group
    """
    if arg in RegisteredFactGroups.keys():
        return True

    return False


def resolveFacts(*args):
    """Function to expand and consilidate facts and fact groups

        This function takes a list of facts or fact groups as either an
        iterable or variadic arguments and returns a list of all facts,
        converting fact groups into individual facts it represents
    """
    if (len(args) == 1 and
            not isinstance(args[0], str) and
            isinstance(args[0], Iterable)):
        args = args[0]

    resolved = []
    for fact in args:
        if fact in RegisteredFactGroups.keys():
            resolved.extend(list(RegisteredFactGroups[fact]))
        elif fact in RegisteredFacts:
            resolved.append(fact)
        else:
            raise ValueError("Unrecognized fact or fact group")

    return resolved


def registerFact(*args, **kwargs):
    """A decorator for registering a Fact with a given type

    Args: fact_groups(str): The interest groups associated with this fact
    """

    if len(args) > 0 and inspect.isclass(args[0]):
        return registerFact()(args[0])

    def _registerFact(cls):
        global RegisteredFacts
        global RegisteredFactGroups
        global __all__
        global FactList

        if not isinstance(cls, _FactMeta_):
            raise TypeError("Detected class not descended from Fact")
        LOGGER.debug("Registering Fact %s"
                     % (cls.__qualname__))

        existing_class = globals().get(cls.__qualname__, None)
        if existing_class is not None:
            LOGGER.warning("%s already exists" % (cls.__qualname__))
            return existing_class

        if cls._type_ is None:
            raise ValueError("_type_ must not be None")

        if cls._type_ in RegisteredFacts:
            # TODO XXX FIXME should this just log a warning, instead?
            raise ValueError("%s is already registered" % (cls._type_))

        RegisteredFacts.add(cls._type_)

        # Setup fact groups if passed
        if args is not None:
            for fact_group in args:
                if not isinstance(fact_group, str):
                    raise TypeError("fact groups must be a 'str' type")
                if fact_group not in RegisteredFactGroups.keys():
                    RegisteredFactGroups[fact_group] = set()

                RegisteredFactGroups[fact_group].add(cls._type_)

        # Update global elements to reflect interests and defs
        __all__.append(cls.__qualname__)
        globals()[cls.__qualname__] = cls
        # Inject the fact groups into the fact
        setattr(cls, '_groups_', args)
        return cls
    return _registerFact


class _FactMeta_(type):
    """Meta class for the Fact class

        This meta class is used to dynamically modify classes based on
        the Fact class to inject fields as class members and update the
        class init/signature to allow direct intiailization of those members
    """
    @classmethod
    def __prepare__(cls, clsname, bases):
        return OrderedDict()

    def __new__(cls, clsname, bases, dct):
        fields = [key for (key, val) in dct.items()
                  if isinstance(val, FactField)]

        for name in fields:
            dct[name].__set_name__(cls, name)

        clsobj = super().__new__(cls, clsname, bases, dict(dct))

        # TODO FIXME find a cleaner way to get the methods of the Fact class
        # Worst case we could run this manually, and then copy the produced
        # list
        members = clsobj._baseFields_
        try:
            if clsname != "Fact":
                members.extend(
                    [field[0] for field in inspect.getmembers(Fact)])
        except Exception:
            pass

        req_kw_params = []
        opt_kw_params = []
        for name in fields:
            if (members is not None and
                    name in members):
                raise AttributeError(("%s used internally, please "
                                      "do not redefine") % (name))

            if dct[name].default is not Parameter.empty:
                default = dct[name].default
            elif dct[name].required:
                default = Parameter.empty
            else:
                default = FactField.empty

            param = Parameter(name,
                              Parameter.KEYWORD_ONLY,
                              default=default)

            if dct[name].required:
                req_kw_params.append(param)
            else:
                opt_kw_params.append(param)

            if dct[name].help is not None:
                if not isinstance(dct[name].help, str):
                    raise TypeError('help must be str type')
                setattr(dct[name], '__doc__', dct[name].help)

        _baseParameters_ = Parameter("kwargs", Parameter.VAR_KEYWORD)
        cls_params = req_kw_params + opt_kw_params + [_baseParameters_]
        sig = Signature(cls_params)
        setattr(clsobj, "__signature__", sig)
        setattr(clsobj, "_fields_", fields)

        return clsobj


class Fact(metaclass=_FactMeta_):
    """Base class for all Fact types

        This function must be the parent for any fact and provides
        basic bootstrapping of facts into the framework including
        injection of members via the meta class and providing basic
        functions. This class takes internal fact information as variables
        that look like _<name>_ and external variables as well

        Args:
          Populated by Framework:
            _id_: The unique id of the fact, populated by the framework
            _creator_: The creator of this fact
            _created_: The timestamp when this fact was created
            _parentObjects_: A list of id's of 'parent' objects
            _parentFacts_: A list of id's of 'parent' facts
            _parentHyps_: A list of id's of 'parent' hyp's
            _childObjects_: A list of id's of 'child' objects
            _childFacts_: A list of id's of 'child' facts
            _childHyps_: A list of id's of 'child' hyp's
          Populated by user:
            parentObjects: Same as _parentObjects_
            parentFacts: Same as _parentFacts_
            parentHyps: Same as _parentHyps_


    """
    _tainted_ = False
    _fields_ = None
    _type_: Optional[str] = None
    _groups_ = None
    # Base fields is the list of base/default keyword arguments
    # This list is meant to ensure someone creating a fact
    # doesn't try to reuse these names
    _baseFields_ = ["_id_",
                    "_creator_",
                    "_created_",
                    "_parentObjects_",
                    "_parentFacts_",
                    "_parentHyps_",
                    "parentObjects",
                    "parentFacts",
                    "parentHyps",
                    "_childObjects_",
                    "_childFacts_",
                    "_childHyps_"]

    def __init__(self, *args, **kwargs):
        for name in self._fields_:
            descriptor = getattr(self.__class__, name)
            descriptor.__set_instance__(self)
            setattr(self, '_%s__' % (name), descriptor)

        binding = self.__signature__.bind(*args, **kwargs)

        arguments = dict(binding.arguments)
        kwargs = arguments.pop('kwargs', dict())
        for (name, val) in binding.arguments.items():
            setattr(self, name, val)

        self._id_ = None
        self._parentObjects_ = set()
        self._parentFacts_ = set()
        self._parentHyps_ = set()
        self._childObjects_ = set()
        self._childFacts_ = set()
        self._childHyps_ = set()

        self._creator_ = None
        self._created_ = time.time()

        for (name, value) in kwargs.items():
            if name == '_id_':
                self._id_ = value
            elif name == '_tainted_':
                self._tainted_ = value
            elif name == '_creator_':
                self._creator_ = value
            elif name == '_created_':
                self._created_ = value
            elif name in ['_parentObjects_', 'parentObjects']:
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("parent objects must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentObjects_ = set(value)
            elif name in ['_parentFacts_', 'parentFacts']:
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("parent facts must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentFacts_ = set(value)
            elif name in ['_parentHyps_', 'parentHyps']:
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("parent hypotheses must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentHyps_ = set(value)
            elif name == '_childObjects_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("child objects must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childObjects_ = set(value)
            elif name == '_childFacts_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("child facts must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childFacts_ = set(value)
            elif name == '_childHyps_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int)
                                   for i in list(value)):
                            raise TypeError(("child hypotheses must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childHyps_ = set(value)
            else:
                raise TypeError("%s is an invalid keyword argument" % (name))

    def _setID(self, id):
        self._id_ = id

    @property
    def id(self):
        return self._id_

    @property
    def parentObjects(self):
        return list(self._parentObjects_)

    def addParentObject(self, parent):
        self._parentObjects_.add(parent)

    def remParentObject(self, parent):
        self._parentObjects_.discard(parent)

    @property
    def parentFacts(self):
        return list(self._parentFacts_)

    def addParentFact(self, parent):
        self._parentFacts_.add(parent)

    def remParentFact(self, parent):
        self._parentFacts_.discard(parent)

    @property
    def parentHyps(self):
        return list(self._parentHyps_)

    def addParentHyp(self, parent):
        self._parentHyps_.add(parent)

    def remParentHyp(self, parent):
        self._parentHyps_.discard(parent)

    @property
    def childObjects(self):
        return list(self._childObjects_)

    def addChildObject(self, child):
        self._childObjects_.add(child)

    def remChildObject(self, child):
        self._childObjects_.discard(child)

    @property
    def childFacts(self):
        return list(self._childFacts_)

    def addChildFact(self, child):
        self._childFacts_.add(child)

    def remChildFact(self, child):
        self._childFacts_.discard(child)

    @property
    def childHyps(self):
        return list(self._childHyps_)

    def addChildHyp(self, child):
        self._childHyps_.add(child)

    def remChildHyp(self, child):
        self._childHyps_.discard(child)

    @property
    def factType(self):
        return self._type_

    @property
    def _type(self):
        return self._type_

    @property
    def factGroups(self):
        return self._groups_

    @property
    def creator(self):
        return self._creator_

    @property
    def created(self):
        return self._created_

    @property
    def tainted(self):
        return self._tainted_

    def _taint(self):
        self._tainted_ = True

    def _untaint(self):
        self._tainted_ = False

    @property
    def _coreFacts(self):
        data = {'_id_': self._id_,
                '_creator_': self._creator_,
                '_created_': self._created_,
                '_tainted_': self._tainted_}

        return data

    @property
    def _internalFacts(self):
        data = {"_parentObjects_": self._parentObjects_,
                "_parentFacts_": self._parentFacts_,
                "_parentHyps_": self._parentHyps_,
                "_childObjects_": self._childObjects_,
                "_childFacts_": self._childFacts_,
                "_childHyps_": self._childHyps_}
        return data

    @property
    def _nonCoreFacts(self):
        data = dict()
        for field in self._fields_:
            try:
                data[field] = getattr(self, field)
            except AttributeError:
                pass

        return data

    def save(self):
        data = self._coreFacts
        data.update(self._nonCoreFacts)
        data.update(self._internalFacts)
        data["_class_"] = type(self).__name__

        return data

    @classmethod
    def load(cls, **kwargs):
        del kwargs["_class_"]
        return cls(**kwargs)


def getFactClass(name):
    """Helper method to return a fact class by name"""
    try:
        return globals().get(name, None)
    except Exception:
        raise


def loadFact(data):
    """Helper method to load a saved fact"""
    try:
        class_name = data['_class_']
    except Exception:
        raise ValueError("Unable to find expected field in save data")

    fact_class = getFactClass(class_name)
    return fact_class.load(**data)


def loadFacts(facts_path=None):
    paths = [os.path.dirname(os.path.abspath(__file__))]
    if facts_path is not None:
        paths.extend(facts_path)

    loaded = set()
    # Exclude Fields.py -- there's no harm/benefit in [re-]loading it
    loadExtras(paths, loaded, exclude_full=set(
        os.path.join(paths[0], 'Fields.py')))

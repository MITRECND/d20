.. _player-authoring:

Players
=======

What is a player
----------------

Before writing a '*player*' it's best to understand what a 'player' is in the context of D20.
A 'Player' in d20 is a class which provides the ability to react to 'facts' seen by the framework and using these fact either derive more facts or objects which can further the workflow of processing an object

Attack of the clones
--------------------

When a fact is seen that a player has registered interest in, a player instance will be created, called a clone and will be instructed to work on that fact.
What that means is that for every fact a new instance of a player will be launched.
To maintain any state or relationship between clones, the console (below) must be used.

Getting started
---------------

Every Player must inherit from the ``PlayerTemplate`` class and use the ``registerPlayer`` decorator to register the player with the framework.
Further, if the player is not included in the base distribution its path must be included in the config for it to be found.
Although multiple players can be defined in a file, it might be cleaner to keep players in their own files.

The following is an example of a simple player:

.. code-block:: python
    :linenos:

    from d20.Manual.Templates import (PlayerTemplate,
                                        registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="MyPlayer",
        description="An example player",
        creator="Me",
        # The version of the player
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1",
        help="This is just an example player",
        interests=['hash'],
    )
    class MyPlayer(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            """A function to handle facts"""

        def handleHyp(self, **kwargs):
            """A function to handle hyps"""

Interests
---------

Every player must register their ``interests`` to receive data they might find relevant. By default, if a player isn't interested in dealing with hyps, they can register interest only in facts by simply passing a ``list`` of types as the example code above does. If a player is also interested in hyps, they can pass a ``dict`` with the keys ``facts`` and ``hyps``. Any other keys in the ``dict`` will be ignored.

The following snippet is an exampe of what it would look like

.. code-block:: python
    :linenos:

    @registerPlayer(
        name="MyPlayer",
        description="An example player",
        creator="Me",
        version="0.1",
        engine_version="0.1",
        help="This is just an example player",
        interests={'facts': ['hash'],
                'hyps': ['hash']},
    )
    class MyPlayer(PlayerTemplate):
        """Class Definition"""


The console
-----------

Every player instance instance has access to a ``console`` in their class which provides a way of interacting with the framework.
The ``console`` includes many convenience functions and calls to get more information when necessary.

The following are the functions available to your player from the ``console``:

requests
~~~~~~~~

The console provides simple pre-configured access to a python ``requests``
session instance which can be used to make web requests. This instance works
like a regular ``requests`` instance:

..code-block:: python

    r = self.console.requests.get('http://google.com')
    print(r.status_code)

requests configuration
""""""""""""""""""""""

You can configure the underlying behavior of requests by using the following
two functions:

.. code-block:: python

    self.console.configureRequestsRetry()
    self.console.configureRequestsSession()

print
~~~~~

Using the built in ``print`` statement is generally a bad idea for any player.
If a player needs to print to the screen they can use the print function provided by the console which should act the same as the native python 3 print function.

.. code-block:: python

    self.console.print('Test')

Temporary directories
~~~~~~~~~~~~~~~~~~~~~

The console has the capability to create and provide temporary directories in case a player needs to store information on disk for any reason.

.. code-block:: python

    mydir = self.console.myDirectory
    tmpdir = self.console.createTempDirectory()

The ``myDirectory`` property returns a temporary player directory which should
not change during the life of a player instance. The ``createTempDirectory``
function will return a new unique temporary directory every time when called.

.. warning::
    The directories should be considered transient and should not include important information.
    The D20 save/load system does not take these directories into consideration, so import or presistent data should not be stored there.

Memory
~~~~~~

The console provides locations where information may be stored to be used across player instances (clones) or within an clone.

.. code-block:: python

    foo = self.console.memory
    foo = self.console.data

The ``memory`` property of the console is player-wide memory which all clones share, whereas the ``data`` property is specific to a clone.

Object Interaction
~~~~~~~~~~~~~~~~~~

A player can interact with objects in the framework using the console:

Getting Objects
"""""""""""""""

There are two functions to get objects. Use ``getObject`` to get a specific object by id.
Use ``getAllObjects`` to get a list of all objects

.. code-block:: python

    obj = self.console.getObject(0)
    ojbs = self.console.getAllObjects()

Adding Objects
""""""""""""""

If your player has a new object to add to the framework, this can be
accomplished using the ``addObject`` function

.. code-block:: python

    # assume object data is in variable 'data'
    obj_id = self.console.addObject(data)
    # The console returns the unique id of the object just added

Facts
~~~~~

A player can interact with facts in the framwork using the console:

Getting Facts
"""""""""""""

There are multiple ways to get facts from the framework.
To get a specific fact if the id is available, the ``getFact`` function may be used.
If all facts of a given type is required, this can be accomplished via the ``getAllFacts`` function.

.. code-block:: python

    f = getFact(0)
    fs = getAllFacts('md5')

Adding Facts
""""""""""""

If a player needs to add facts about an object, hyp (or another fact) it can do so using the ``addFact`` function:

.. code-block:: python

    fact = MimeTypeFact(mimetype='application/javascript',
                        object_id=0)
    self.console.addFact(fact)

Hyps
~~~~

A player can interact with the hyps in the framework using the console:

Getting Hyps
""""""""""""

There are multiple ways to get hyps from the framework. To get a specific
fact if the id is available, the ``getHyp`` function may be used. If all hyps
of a given type is required, this can be accomplished via the
``getAllHyps`` function.

.. code-block:: python

    f = getHyp(0)
    fs = getAllHyps('md5')

Adding Hyps
"""""""""""

If a player needs to add hyps about an object, fact, or another hyp it can do
so using the ``addHyp`` function:

.. code-block:: python

    fact = MimeTypeHyp(mimetype='application/javascript',
                        object_id=0)
    self.console.addHyp(fact)

waitOn
~~~~~~

A family of generator functions exist in the console to allow a player to
wait/block until an object, fact, or hyp has been added to the framework by
another player or npc based on certain conditions.

waitOnFacts
"""""""""""

The waitOnFacts function will block until facts of a certain type are provided.
By default this will return **all** facts of the given types and then start blocking.
It is safer to do this than to use the ``only_latest`` argument, as you might miss a fact having been added between calling waitOnFacts and its execution (aka a race condition).

.. code-block:: python

    for f in self.console.waitOnFacts('hash'):
        # do stuff with f
        break

waitOnHyps
""""""""""

The waitOnHyps function is the hyp version of the above ``waitOnFacts`` function.
The same conditions and caveats apply.

.. code-block:: python

    for h in self.console.waitOnHyps('hash'):
        # do stuff with h
        break

waitOnChildFacts
""""""""""""""""

The waitOnChildFacts function allows a player to wait on any facts of a given type that are children for a given object id, fact id, or hyp id. This enables a player to effectively watch the facts being added for a given object, fact, or hyp.

.. code-block:: python

    for f in self.console.waitOnChildFacts(object_id=0):
        # do stuff with f
        break

waitOnChildHyps
"""""""""""""""

The waitOnChildHyps function allows a player to wait on any hyps of a given
type that are children for a given object id, fact id, or hyp id. This enables
a player to effectively watch the hyps being added for a given object, fact,
or hyp.

.. code-block:: python

    for h in self.console.waitOnChildHyps(fact_id=0):
        # do stuff with h
        break

waitOnChildObjects
""""""""""""""""""

The waitOnChildObjects function allows a player to wait on any objects that are children for a given object id, fact id, or hyp id. This enables a player to effectively watch the objects being added for a given object, fact, or hyp.

.. code-block:: python

    for o in self.console.waitOnChildObjects(hyp_id=0):
        # do stuff with o
        break

waitTillFact
~~~~~~~~~~~~

The ``waitTillFact`` function will return a single fact of a given type or until timeout, if set

.. code-block:: python
    :linenos:

    try:
        f = self.console.waitTillFact('md5', timeout=5)
    except WaitTimeoutError as e:
        pass

This function can be used to reliably wait for the 'next' fact to be submitted of a given type by utilizing the ``last_fact`` argument

.. code-block:: python
    :linenos:

    fs = self.console.getAllFacts('hash')
    # assumng len(fs) > 0
    try:
        f = self.console.waitTillFact('hash', timeout=1, last_fact=fs[-1].id)
    except WaitTimeoutError as e:
        pass

Writing an Example Player
=========================

The following is an example of how to write a player based on a simple
scenario. Please read :ref:`Player Authoring<player-authoring>` before
proceeding.

Scenario
--------

In this example, we have obtained a piece of malware in the ``EPMalware`` family that has an encoded configuration file.
Someone has already written an ``NPC`` that can determine if a executable is in the malware family and which produces a ``fact`` of type ``ep_fact``.
Through analysis we know that this family of malware stores the config file in the file proceeded by the key sequence ``\xff\xba\xad\xff`` somewhere in the file. Right after the sequence is a structure that looks like the following:

.. code-block:: none

      1 byte      2 bytes (LE)
    -------------------------------------------
    | xor key | data length     |  xor'd data |


The example player we're going to write has the sole purpose of extracting and decoding/unencrypting the config block.
It should produce the config as a new ``fact`` for some other component to consume.

Prereqs
-------

Directory Structure
~~~~~~~~~~~~~~~~~~~

We'll need to do some setup before actually writing code.
Since you cannot add entities directly to ``d20`` as it is installed as a package, you'll need to create a directory that can host our new components.

.. code-block:: text

    .
    └── d20-extra
        ├── facts
        └── players

As shown above, we've created a base directory ``d20-extra`` for our components and then created a directory for ``facts`` and ``players``.

Configuration
~~~~~~~~~~~~~

In lieu of passing in the path to these directories every time you run ``d20``, it's considerably easier to write a config file to pass into ``d20`` instead.
Recall that config files are yaml files with different sections.

.. code-block:: yaml

    d20:
        extra-players:
            - <full path>/d20-extra/players
        extra-facts:
            - <full path>/d20-extra/facts

The above is what a simple example of what our config would look like for this example player.
Write something like the above in a file called ``myconfig.yml``.

Just the Facts
~~~~~~~~~~~~~~

As mentioned in the scenario our ``player`` needs to create a ``fact`` after it is able to extract the config, since we don't have a ``fact`` that is suitable, we'll need to create one.
Note that you should always check existing facts to see if they fit your use case before creating a new one.

To create a new fact we'll create a file in ``d20-extra/facts`` called
``EPConfig.py``.

.. code-block:: text

    .
    └── d20-extra
        ├── facts
        │   └── EPConfig.py
        └── players

Next we'll create our fact. For more information, please read :ref:`Fact Authoring<fact-authoring>`.

.. code-block:: python
    :linenos:

    from d20.Manual.Facts import (Fact,
                                registerFact)

    from d20.Manual.Facts.Fields import BytesField


    @registerFact('config')
    class EPConfigFact(Fact):
        _type_ = 'ep_config'
        config = BytesField(required=True)

At this point we should have everything we need to get started on writing the
player

Creating Your Player
--------------------

Skeleton
~~~~~~~~

As with all players, we'll start with a skeleton. The below can be used
to start any player you're writing:

.. code-block:: python
    :linenos:

    from d20.Manual.Templates import (PlayerTemplate,
                                    registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="",
        description="",
        creator="",
        # The version of the player
        # must conform to PEP440 version numbering
        version="",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="",
        help="",
        interests=[],
    )
    class Player(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            """A function to handle facts"""

        def handleHyp(self, **kwargs):
            """A function to handle hyps"""

Get Started
~~~~~~~~~~~

Now let's fill out the skeleton with relevant information for the player
we're writing:

.. code-block:: python
    :linenos:

    import struct
    from d20.Manual.Templates import (PlayerTemplate,
                                    registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="EPConfigDumper",
        description="A Player to dump config from EPMalware",
        creator="You!",
        # The version of the player
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1.1",
        help="No help available",
        interests=['ep_fact'],
    )
    class EPConfigDumper(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            """A function to handle facts"""

So, right off the bat, we've created a player that will only trigger if
some component, e.g., an ``NPC`` produces an ``ep_fact``. We've also removed
the handleHyp function since we will not be using it. Note that since
``handleFact`` is provided a fact to handle using keyword argument ``fact``,
you could have written the ``handleFact`` function slightly differently to not
need to reference the kwargs dictionary to obtain the ``fact``.

.. code-block:: python
    :linenos:

    def handleFact(self, fact, **kwargs):
        """Explicitly name fact keyword argument

           **kwargs is still required for other arguments and future
           compatibility
        """

Part 1
~~~~~~

Next let's add some code to handleFact to ensure that we've received what
we're expecting:

.. code-block:: python
    :lineno-start: 27

    def handleFact(self, **kwargs):
        try:
            myfact = kwargs['fact']
        except KeyError as e:
            raise RuntimeError("Expected a 'fact' element in arguments")

        if myfact.factType() != 'ep_fact':
            raise RuntimeError("Expected an 'ep_fact' type")

        try:
            obj_id = myfact.parentObjects[0]
        except KeyError as e:
            raise RuntimeError("Expected a parent object")

        obj = self.console.getObject(obj_id)


Let's break this down

.. code-block:: python
    :lineno-start: 28

        try:
            myfact = kwargs['fact']
        except KeyError as e:
            raise RuntimeError("Expected a 'fact' element in arguments")

        if myfact.factType() != 'ep_fact':
            raise RuntimeError("Expected an 'ep_fact' type")

This code grabs the ``fact`` that needs to be handled which is provided as the
``fact`` keyword argument and then checks to make sure that its type is ``ep_fact``

.. code-block:: python
    :lineno-start: 36

        try:
            obj_id = myfact.parentObjects[0]
        except KeyError as e:
            raise RuntimeError("Expected a parent object")


Our first task is to get the ``id`` of the object that was used to derive this ``fact``.
Generally, to use a ``fact`` you should be familiar with what it is and what data it represents.
In this example, we know that the ``ep_fact`` represents the indication that a parent object is in the ``EPMalware`` family and as such, the 0th parent object should be the actual malware.

.. code-block:: python
    :lineno-start: 41

        obj = self.console.getObject(obj_id)

Here is where we first interact with the framework via the ``console``.
After obtaining the ``id`` of the object via the ``fact``, we ask the ``console`` to provide the malware to us, so we can process it.
The end result is that ``obj`` will contain the raw data of the malware.
So far this is what our player looks like:

.. code-block:: python
    :linenos:

    import struct
    from d20.Manual.Templates import (PlayerTemplate,
                                    registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="EPConfigDumper",
        description="A Player to dump config from EPMalware",
        creator="You!",
        # The version of the player
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1.1",
        help="No help available",
        interests=['ep_fact'],
    )
    class EPConfigDumper(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            try:
                myfact = kwargs['fact']
            except KeyError as e:
                raise RuntimeError("Expected a 'fact' element in arguments")

            if myfact.factType() != 'ep_fact':
                raise RuntimeError("Expected an 'ep_fact' type")

            try:
                obj_id = myfact.parentObjects[0]
            except KeyError as e:
                raise RuntimeError("Expected a parent object")

            obj = self.console.getObject(obj_id)

Part 2
~~~~~~

So now that we've obtained the object in question, we need to use our
knowledge of the malware family and extract the config.

.. code-block:: python
    :lineno-start: 43

        loc = obj.find(b'\xff\xba\xad\xff')
        if loc == -1: # Not Found, maybe not proper malware
            return

        loc += 4 # skip past sequence
        xorkey = obj[loc]
        # Extract size
        size = struct.unpack("<H", obj[loc+1:loc+2])
        loc += 3 # skip to data
        # Extract encrypted/encoded data
        data = obj[loc: loc + size]

        outdata = b''
        for raw in data:
            outdata += bytes(chr(raw ^ xorkey))

Now let's break this down

.. code-block:: python
    :lineno-start: 43

        loc = obj.find(b'\xff\xba\xad\xff')
        if loc == -1: # Not Found, maybe not proper malware
            return

        loc += 4 # skip past sequence

Remember from the scenario, that we need to find the sequence ``\xff\xba\xad\xff`` in the file.
The easiest way to do this is to simply use the ``find`` command to look for the sequence.
After finding the sequence, skip the length of the sequence so what we're looking at is the releant data.

.. code-block:: python
    :lineno-start: 48

        xorkey = obj[loc]
        # Extract size
        size = struct.unpack("<H", obj[loc+1:loc+2])
        loc += 3 # skip to data
        # Extract encrypted/encoded data
        data = obj[loc: loc + size]

Now that we've found the beginning of our relevant data we need to extract the different elements that were outlined in the scenario.
The xor key is the first byte, so we save that.
Followed by the size field which is 2 bytes in size, little-endian, that we extract using ``struct.unpack``.
Finally, we use the size we just obtained to isolate the relevant data.

.. code-block:: python
    :lineno-start: 55

        outdata = b''
        for raw in data:
            outdata += bytes(chr(raw ^ xorkey))

Now with all of that information, we use the xor key and the data block, to
create an unencrypted/decoded data block.

At this point, this is what our player looks like:

.. code-block:: python
    :linenos:

    import struct
    from d20.Manual.Templates import (PlayerTemplate,
                                    registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="EPConfigDumper",
        description="A Player to dump config from EPMalware",
        creator="You!",
        # The version of the player
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1.1",
        help="No help available",
        interests=['ep_fact'],
    )
    class EPConfigDumper(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            try:
                myfact = kwargs['fact']
            except KeyError as e:
                raise RuntimeError("Expected a 'fact' element in arguments")

            if myfact.factType() != 'ep_fact':
                raise RuntimeError("Expected an 'ep_fact' type")

            try:
                obj_id = myfact.parentObjects[0]
            except KeyError as e:
                raise RuntimeError("Expected a parent object")

            obj = self.console.getObject(obj_id)
            loc = obj.find(b'\xff\xba\xad\xff')
            if loc == -1: # Not Found, maybe not proper malware
                return

            loc += 4 # skip past sequence
            xorkey = obj[loc]
            # Extract size
            size = struct.unpack("<H", obj[loc+1:loc+2])
            loc += 3 # skip to data
            data = obj[loc: loc + size]

            outdata = b''
            for raw in data:
                outdata += bytes(chr(raw ^ xorkey))

Part 3
~~~~~~

Now that we've extracted our information, we need to feed that information back into the framework for other components to use.
This is done in the form of a ``fact``. As we created the ``ep_config`` fact type earlier, we'll use that.

.. code-block:: python
    :lineno-start: 57

        epconfig_fact = EPConfigFact(config=outdata,
                                     parentObjects=[obj_id],
                                     parentFacts=[myfact.id])
        self.console.addFact(epconfig_fact)

Earlier in the code, recall that we import all ``facts`` in the system.
Because of the way ``d20`` automatically extends internal structures based on its configuration, this means that the ``EPConfigFact`` created earlier is directly accessible to our player.

So, we then create an instance of ``EPConfigFact`` passing it three keyword arguments, ``config``, ``parentObjects``, and ``parentFacts``.
The ``config`` argument was defined in the definition for the fact. The ``parentObjects`` field is inherited from the ``Fact`` object and defining some parent relationship is required before a ``fact`` can be submitted to the framework.
The final argument, ``parentFacts`` is also another inherited argument and defines the relationship of the original ``fact``, ``ep_fact``, to this newly created ``fact``.

To actually submit the ``fact`` to the framework, we leverage the console and
the ``addFact`` function.

At this point we're done with our simple example player. Here's what the
final product looks like:

.. code-block:: python
    :linenos:

    import struct
    from d20.Manual.Templates import (PlayerTemplate,
                                    registerPlayer)
    from d20.Manual.Facts import *


    @registerPlayer(
        name="EPConfigDumper",
        description="A Player to dump config from EPMalware",
        creator="You!",
        # The version of the player
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1.1",
        help="No help available",
        interests=['ep_fact'],
    )
    class EPConfigDumper(PlayerTemplate):
        def __init__(self, **kwargs):
            # PlayerTemplate registers the console as self.console
            # Remember to init the parent class!!
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            try:
                myfact = kwargs['fact']
            except KeyError as e:
                raise RuntimeError("Expected a 'fact' element in arguments")

            if myfact.factType() != 'ep_fact':
                raise RuntimeError("Expected an 'ep_fact' type")

            try:
                obj_id = myfact.parentObjects[0]
            except KeyError as e:
                raise RuntimeError("Expected a parent object")

            obj = self.console.getObject(obj_id)
            loc = obj.find(b'\xff\xba\xad\xff')
            if loc == -1: # Not Found, maybe not proper malware
                return

            loc += 4 # skip past sequence
            xorkey = obj[loc]
            # Extract size
            size = struct.unpack("<H", obj[loc+1:loc+2])
            loc += 3 # skip to data
            data = obj[loc: loc + size]

            outdata = b''
            for raw in data:
                outdata += bytes(chr(raw ^ xorkey))

            epconfig_fact = EPConfigFact(config=outdata,
                                        parentObjects=[obj_id],
                                        parentFacts=[myfact.id])
            self.console.addFact(epconfig_fact)

Running d20
-----------

Writing the player is all well and good but we'll need to run our code. To do
this we just need to pass our config to d20 along with the location of our
malware sample:

.. code-block:: bash

    d20 -c myconfig.yml /data/malware/sample
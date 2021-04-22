NPCs
====

What is an npc
--------------

An '*NPC*' in d20 is a class which provides the ability to react to 'objects'
seen by the framework and further uses these objects to either derive facts,
hyps or more objects which can further the workflow of breaking down a binary

Getting Started
---------------

Every NPC must inherit from the ``NPCTemplate`` class and be registered using the ``registerNPC`` decorator.
Further, if the npc is not included in the base distribution, the path to the NPC must be included in the config for it to be found.

The following is an example of a simple NPC:

.. code-block:: python
    :linenos:

    from d20.Manual.Templates import (NPCTemplate,
                                    registerNPC)


    @registerNPC(
        name="MyNPC",
        description="This is my NPC",
        creator="ME",
        version="0.1",
        engine_version="0.1"
    )
    class TestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            # Must init the parent!!
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            """A function to handle a new object"""

The console
-----------

Every npc instance instance has access to a ``console`` in their instance which provides a way of interacting with the framework.
The ``console`` includes many convenience functions and calls to get more information when necessary.

The following are the functions available to your npc from the ``console``:

requests
~~~~~~~~

The console provides simple pre-configured access to a python ``requests``
session instance which can be used to make web requests. This instance works
like a regular ``requests`` instance:

.. code-block:: python

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

Using the built in ``print`` statement is generally a bad idea for any npc.
If a npc needs to print to the screen they can use the print function provided by the console which should act the same as the native python 3 print function

.. code-block:: python

    self.console.print('Test')

Temporary directories
~~~~~~~~~~~~~~~~~~~~~

The console has the capability to create and provide temporary
directories in case a npc needs to store information on disk for any reason

.. code-block:: python

    mydir = self.console.myDirectory
    tmpdir = self.console.createTempDirectory()

The ``myDirectory`` property returns a temporary npc directory which should
not change during the life of a npc instance. The ``createTempDirectory``
function will return a new unique temporary directory every time when called.

.. warning::
    The directories should be considered transient and should not include important information.
    The D20 save/load system does not take these directories into consideration, so import or presistent data should not be stored there.

Memory
~~~~~~

The console provides a location where information may be stored to be used in the npc.
The ``memory`` property of the console is npc-wide memory.

.. code-block:: python

    foo = self.console.memory

Object Interaction
~~~~~~~~~~~~~~~~~~

An npc can interact with objects in the framework using the console:

Adding Objects
""""""""""""""

If your npc has a new object to add to the framework, this can be
accomplished using the ``addObject`` function

.. code-block:: python

    # assume object data is in variable 'data'
    obj_id = self.console.addObject(data)
    # The console returns the unique id of the objected just added

Fact Interaction
~~~~~~~~~~~~~~~~

An npc can interact with facts in the framwork using the console:

Adding Facts
""""""""""""

If an npc needs to add facts it can do so using the ``addFact`` function:

.. code-block:: python

    fact = MimeTypeFact(mimetype='application/javascript',
                        parentObjects=[0])
    self.console.addFact(fact)

Hyp Interaction
~~~~~~~~~~~~~~~

An npc can interact with hyps in the framework using the console:

Adding Hyps
"""""""""""

If an npc needs to add facts it can do so using the `addHyp` function:

.. code-block:: python

    hyp = MimeTypeFact(mimetype='application/javascript',
                       parentObjects=[0])
    self.console.addHyp(hyp)
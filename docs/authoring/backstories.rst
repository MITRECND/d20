BackStories
===================

What is a Backstory
-------------------

A '*BackStory*' in D20 is a mechanism to seed a D20 game without a starting binary.
Instead BackStory facts maybe provided allowing a backstory to then acquire binaries to start a game.
In this way you can kick off a D20 run without needing to provision files locally.

Getting Started
---------------

Every BackStory must inherit from the ``BackStoryTemplate`` class and use the ``registerBackStory`` decorator to register the BackStory with the framework.
Further, if the BackStory is not included in the base distribution its path must be included in the config for it to be found.

The following is an example of a simple BackStory:


.. code-block:: python
    :linenos:

    from d20.Manual.Templates import (BackStoryTemplate,
                                      registerBackStory)

    @registerBackStory(
        name="MyBackStory",
        description="An example backstory",
        creator="Me",
        # The version of the backstory
        # must conform to PEP440 version numbering
        version="0.1",
        # The minimum version of the game engine supported
        # The game engine version conforms to PEP440 so this
        # should be comparable, e.g., 0.1.0 and 0.1 are equivalent
        engine_version="0.1",
        help="This is just an example backstory",
        interests=['hash'],
    )
    class MyBackStory(BackStoryTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            """A function to handle facts"""

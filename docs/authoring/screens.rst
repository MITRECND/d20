Screens
=======

What is a screen
----------------

A 'screen' in D20 is a class that handles the result of a D20 run. It is executed after the GameMaster has decided no more processing is possible. A Screen may output to ``stdout`` or any location that is desired.

Getting Started
---------------

Similar to players and npcs, screens need to be classes that inherit from a parent class, in this case, ``ScreenTemplate`` and registered via the decorator ``registerScreen``.
Screens are instantiated after D20 has finished running and are given arguments cooresponding to the final state of the process in its init kwargs dictionary.
The following is an example of a screen:

.. code-block:: python
    :linenos:

    from d20.Manual.ScreenTemplate import (ScreenTemplate,
                                        registerScreen)
    from d20.Manual.Facts import Fact

    @registerScreen(
        name="test"
    )
    class TestScreen(ScreenTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Parent object inits
            # facts - dictionary of game facts
            # objects - list of objects
            # options - any options passed from config
            # hyps - dictionary of game hyps

        def present(self):
            gameData = {'objects': list(),
                        'facts': dict(),
                        'hyps': dict()}

            # Do work on data provided by init

            try:
                print(gameData)
            except Exception as e:
                LOGGER.exception("Error attempting to serialize game data")

Writing a screen, currently requires an in-depth understanding of the
data structures provided to it.

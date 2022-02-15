Actions
=======

What is an action
-----------------

An '*action*' in D20 is a class within a python package that provides some common functionality that a player or npc may leverage to complete their task.
Actions in D20, can be directly imported via the python import system under the `d20.Actions` package and must, themselves, be packages.
Actions not part of the default distribution must be included in the config to be accessible.

Getting Started
---------------

Every action must be a valid python package.
If unfamiliar with python packaging, please read python's documentation on `packaging <https://docs.python.org/3.9/tutorial/modules.html#packages>`_ for more information.
Note that, D20 actions only support one-level deep packages.
If your package has nested packages, they will need to be exposed by the highest level packages.

By convention, every action should be a class which exposes methods.
If the action you're creating does not require any state, consider using
the `staticmethod` decorator to allow direct usage of the function.
It also recommended that actions be fully documented with python docstrings.

The following directory structure is an example of the layout of a simple action:

.. code-block:: bash

    Actions/
    ├── MyAction
    │   └── __init__.py


Note that the containing directory does not need to be a python package.

Inside the ``__init__.py`` file it could look like:

.. code-block:: python
    :linenos:

    class MyAction:
        """My custom action class"""
        @staticmethod
        def add(num1, num2):
            """Function that adds two numbers and returns the result"""
            return num1 + num2

Using Actions
-------------

Actions can be directly imported and used like regular python code:

.. code-block:: python

    from d20.Actions.MyAction import MyAction

    val = MyAction.add(1, 1)

Please refer to the documentation for individual actions to determine their use.

Dependencies
------------

As external actions can implement python routines that may not be native,
they might make use of external libraries. As such they should generally
include a requirements file to ensure the proper libraries are installed as
needed.

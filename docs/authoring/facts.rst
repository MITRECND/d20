.. _fact-authoring:

Facts
=====

What is a fact
--------------

A '*fact*' in D20 is a data container class which represents some unit
of information discovered about either an object (a file, binary blob, etc) or
another fact.
A fact should be descriptive enough to provide information to a Player to make some decision. This class is given a 'type' which is then used to organize all the facts in the system.

Fact Groups
-----------

Facts can be grouped up for convenience into fact groups.
These groups are then exploded internally into their individual fact types. For example the ``hash`` type is actually a fact group which expands to the other fact types that are hashes ('md5', 'sha1', 'sha256', 'ssdeep').

Getting Started
---------------

Every fact must inherit from the ``Fact`` class and must use the ``registerFact`` decorator to register itself with the framework.
Facts not part of the core distribution need to have their paths passed into the config.

The following is an example of a simple fact:

.. code-block:: python
    :linenos:

    from d20.Manual.Facts import (Fact,
                                registerFact)

    from d20.Manual.Facts.Fields import StringField


    @registerFact('hash')
    class CRC32HashFact(Fact):
        _type_ = 'crc32'
        value = StringField()

The above code creates a new fact with the type ``crc32`` and as part of the
``hash`` fact group. It also contains a single field called ``value``.
Both the name of the class and value of ``_type_`` should be unique.
There are also a number of reserved names that act as an api.
If there is any overlap, D20 will throw an error during the reigstration process.

registerFact
~~~~~~~~~~~~

The ``registerFact`` decorator is used to register a fact with the framework.
By default, it does *not* require arguments:

.. code-block:: python

    @registerFact
    class CRC32HashFact(Fact):
        _type_ = 'crc32'
        value = StringField()

The only arguments accepted by the decorator are any fact groups that a fact
being defined needs to be placed in:

.. code-block:: python

    @registerFact('hash', 'crc')
    class CRC32HashFact(Fact):
        _type_ = 'crc32'
        value = StringField()

The above will create the ``crc32`` fact type and add it to the ``hash`` and ``crc`` fact groups.

Fact Class
----------

The ``Fact`` class along with the usage of the decorator provides a fair
bit of internal instrumentation that makes it easier to work with. This
includes taking any data fields defined and allowing them to be defined
at class initialization time by keyword. It further allows you to use Fact
Field types to better constrain how the data should be presented and used.

Immutability
~~~~~~~~~~~~

After adding a ``Fact`` to the framework (via ``console.addFact``), it should
be considered immutable.
Values should not be changed for any reason.
Internally, D20 will update relationships, but this should be left entirely to the framework.

Fact Class Properties
~~~~~~~~~~~~~~~~~~~~~

By default the ``Fact`` class defines the following properties which should not be redefined:

* id
* parentObjects
* addParentObject
* remParentObject
* parentFacts
* addParentFact
* remParentFact
* parentHyps
* addParentHyp
* remParentHyp
* childObjects
* addChildObject
* remChildObject
* childFacts
* addChildFact
* remChildFact
* childHyps
* addChildHyp
* remChildHyp
* factType
* factGroups
* creator
* created
* tainted
* save
* load

The ``Fact`` class also defines other 'private' variables and so it is not recommened to define any fields that look like ``_<name>_``.

Relationships
~~~~~~~~~~~~~

As might be indicated from the above properties there are many functions available for dealing with the relationships of facts to other objects.
All of these are accessible to Players and NPCs, but **must not** be used after adding the fact to the framework.
D20 handles relationships internally based on the information provided but will not automatically act on calls to these functions after a fact has been registered.

Accessor Methods
~~~~~~~~~~~~~~~~

The following methods provide read-only information:

**id**
    Returns the unique id of the fact in the framework

**parentObjects**
    Returns a list of object id's that are considered the 'parent' of this fact

**parentFacts**
    Returns a list of fact id's that are considered the 'parent' of this fact

**parentHyps**
    Returns a list of hyp id's that are considered the 'parent' of this fact

**childObjects**
    Returns a list of object id's that are considered 'children' of this fact

**childFacts**
    Returns a list of fact id's that are considered 'children' of this fact

**childHyps**
    Returns a list of hyp id's that are considered 'children' of this fact

**factType**
    Returns the str indicating the type of this fact (e.g., `crc32`)

**factGroups**
    Returns the list of str of the fact groups this fact was registered into

**creator**
    Returns the name of the element (Player or NPC) that created this fact

**created**
    Returns the unix timestamp when this fact was created

**tainted**
    Returns a boolean value indicating if this Fact is actually a Hypothesis - mainly used for internal housekeeping

The following functions provide the ability to add relationships to facts. They take the numerical id of the element you are trying to relate.
Note, these **must not** be used after adding a fact (or hyp) to the framework:

* addParentObject
* remParentObject
* addParentFact
* remParentFact
* addParentHyp
* remParentHyp
* addChildObject
* remChildObject
* addChildFact
* remChildFact
* addChildHyp
* remChildHyp

Fact Fields
-----------

Since Facts are data containers, they need data to contain.
To ensure d20 can operate in an automated fashion, data is constrained to classes derived from the `FactField` class.
The examples above uses the `StringField` class, which is derived from `FactField` and enforces the type to be a `str` type.

All fields take the following arguments:

* required (default=False) - Whether the field is required
* help (default=None) - A string to override the help/docstring of the field
* default (no default value) - The default value of this field if not set
* allowed_values (default=None) - A list of constraining values for this field

Here is a more complete example of a Fact class with a field with more options defined:

.. code-block:: python
    :linenos:

    @registerFact('hash')
    class CRC32HashFact(Fact):
        _type_ = 'crc'
        bits = IntegerField(required=True, allowed_values=[16,32])
        value = StringField(required=True, help='A CRC value')

To use the above type one could do the following:

.. code-block:: python

    foo = CRC32HashFact(bits=32, value="88638800")

The following fields are currently defined:

* StringField
* BooleanField
* BytesField
* IntegerField
* FloatField
* DictField
* ListField
* ListDictsField
* NumericalField
* StrOrBytesField

Custom Fields
-------------

If the existing fields do not meet your needs it is possible to create your
own by creating a class that inherits from FactField or its descendants
from collections.abc import Iterable
from inspect import Parameter


class _empty:
    """Marker object for FactField.empty"""


class FactField:
    """Base Fact field class

        This class serves as the base for fact field types that can be defined
        and set within Fact classes

        Args:
            name(str): The name of the variable in the instance. Populated by
                upstream code
            required(bool): Whether this field is required or
                not (default False)
            default(object): The default value for a variable
            allowed_values(Iterable): An iterable of allowed values that can
                be assigned
            help(str): A string to override the help/docstring of the field
    """
    empty = _empty

    def __init__(self, name=None, *args, required=False, help=None,
                 default=Parameter.empty, allowed_values=None, **kwargs):
        self.name = name
        self.required = required
        self.allowed_values = allowed_values
        self.instance = None
        self.default = default
        self.help = help

    def __set_name__(self, owner, name):
        self.name = name

    def __set_instance__(self, instance):
        self.instance = instance

    def getShell(self):
        try:
            return self.instance.__dict__[self.name]
        except KeyError:
            raise AttributeError("%s object has not defined attribute %s"
                                 % (self.instance.__class__.__name__,
                                    self.name)) from None

    def __str__(self):
        try:
            return str(self.instance.__dict__[self.name])
        except KeyError:
            raise AttributeError("%s object has not defined attribute %s"
                                 % (self.instance.__class__.__name__,
                                    self.name)) from None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            try:
                return instance.__dict__[self.name]
            except KeyError:
                if self.default is not Parameter.empty:
                    return self.default
                raise AttributeError("%s object has not defined attribute %s"
                                     % (instance.__class__.__name__,
                                        self.name)) from None

    def __set__(self, instance, value):
        if isinstance(self.allowed_values, Iterable):
            if value not in self.allowed_values:
                raise ValueError("Field %s can only be certain values"
                                 % (self.name))
        instance.__dict__[self.name] = value

    def __delete__(self, instance):
        raise RuntimeError("Fact fields cannot be deleted")


class SimpleField(FactField):
    """Simple Field base class

        This class verifies values on set based on the fieldType defined
        in the class. Meant to be used as a parent and not directly
    """
    fieldType = object

    def __set__(self, instance, value):
        if not isinstance(value, self.fieldType):
            raise TypeError(
                "Field '%s' expected %s type (inferred to be %s type)"
                % (self.name, self.fieldType.__name__, type(value).__name__))
        super().__set__(instance, value)


class StringField(SimpleField):
    """String Field

        This class accepts str types only
    """
    fieldType = str


class BooleanField(SimpleField):
    """Boolean Field

        This class accepts bool types only
    """
    fieldType = bool


class BytesField(SimpleField):
    """Bytes Field

        This class accepts bytes types only
    """
    fieldType = bytes


class IntegerField(SimpleField):
    """Integer Field

        This class accepts int types only
    """
    fieldType = int


class FloatField(SimpleField):
    """Float Field

        This class accepts float types only
    """
    fieldType = float


class DictField(SimpleField):
    """Dict Field

        This class accepts dict types only
    """
    fieldType = dict


class ListField(FactField):
    """Generic List field

       Ensures type is list, also optionally checks list element types. If
       an element type is specified it uses the ConstrainedList type
       defined below
    """
    def __init__(self, *args, valType=None, **kwargs):
        self.valType = valType
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if not isinstance(value,
                          list) and not isinstance(value, ConstrainedList):
            raise TypeError("Field '%s' expected list type (inferred %s type)"
                            % (self.name, type(value).__name__))
        if self.valType is not None and isinstance(self.valType, type):
            value = ConstrainedList(value, valType=self.valType)
        super().__set__(instance, value)


class ListDictsField(ListField):
    """List of Dicts
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, valType=dict, **kwargs)


class NumericalField(FactField):
    """Field to represent nubers

        Supports the 'int' and 'float' types
    """
    def __set__(self, instance, value):
        if not isinstance(value, int) and not isinstance(value, float):
            raise TypeError(
                "Field '%s' expected int or float types (inferred %s type)"
                % (self.name, type(value).__name__))
        super().__set__(instance, value)


class StrOrBytesField(FactField):
    """String or Bytes field

        This class allows for both 'str' and 'bytes' types. Useful when you
        want to relax checking of either type
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if not isinstance(value, str) and not isinstance(value, bytes):
            raise TypeError(
                "Field '%s' expected str or bytes types (inferred %s type)"
                % (self.name, type(value).__name__))
        super().__set__(instance, value)

    def getShell(self):
        value = super().getShell()

        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode('utf-8')
        else:
            raise TypeError(
                "Field '%s' value must be str or bytes type (inferred %s type)"
                % (self.name, type(value).__name__))


class ConstrainedList(list):
    """Type Constrained List

        This class, based on the built-in list type, does basic type checking
        of members being added to ensure they are of the correct type
    """
    def __init__(self, *args, valType, **kwargs):
        self.valType = valType
        if len(args) > 1:
            raise TypeError(
                "ContrainedList takes at most 1 argument (%d given)"
                % (len(args)))

        # Need to remove the interable if supplied to manually
        # handle it, ensuring types are checked
        if len(args) > 0:
            source = args[0]
            args = tuple(args[1:])
            if not isinstance(source, Iterable):
                raise TypeError("%s object is not iterable"
                                % (type(source).__name__))
        else:
            source = None

        super().__init__(**kwargs)

        if source is not None:
            for item in source:
                self.append(item)

    def __checkClass_(self, value):
        if not isinstance(value, ConstrainedList):
            for val in value:
                if not isinstance(val, self.valType):
                    raise TypeError(
                        ("Invalid type of element, expected %s "
                         "(inferred %s type)")
                        % (self.valType.__name__, type(val).__name__))
        elif value.valType != self.valType:
            raise TypeError(("Cannot add together ConstrainedList of type %s "
                             "with different types (inferred %s type"
                            % (self.valType.__name__, value.valType.__name__)))

    def __checkElement_(self, value):
        if not isinstance(value, self.valType):
            raise TypeError(
                "Expected element to be of type %s (inferred %s type)"
                % (self.valType.__name__, type(value).__name__))

    def __add__(self, value):
        self.__checkClass_(value)
        return super().__add__(value)

    def __iadd__(self, value):
        self.__checkClass_(value)
        return super().__iadd__(value)

    def __setitem__(self, key, value):
        self.__checkElement_(value)
        super().__setitem__(key, value)

    def append(self, value):
        self.__checkElement_(value)
        super().append(value)

    def insert(self, index, value):
        self.__checkElement_(value)
        super().insert(index, value)

    def extend(self, value):
        self.__checkClass_(value)
        super().extend(value)

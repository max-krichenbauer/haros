
#Copyright (c) 2018 Andre Santos
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.


###############################################################################
# Imports
###############################################################################

from .ros_types import (
    INT8_MIN_VALUE, INT8_MAX_VALUE, INT16_MIN_VALUE, INT16_MAX_VALUE,
    INT32_MIN_VALUE, INT32_MAX_VALUE, INT64_MIN_VALUE, INT64_MAX_VALUE,
    UINT8_MAX_VALUE, UINT16_MAX_VALUE, UINT32_MAX_VALUE, UINT64_MAX_VALUE,
    FLOAT32_MIN_VALUE, FLOAT32_MAX_VALUE, FLOAT64_MIN_VALUE, FLOAT64_MAX_VALUE,
    TypeToken, ArrayTypeToken
)


###############################################################################
# Strategy Map
###############################################################################

class StrategyMap(object):
    __slots__ = ("defaults", "custom")

    def __init__(self):
        self.defaults = {} # {ros_type -> TopLevelStrategy}
        self.custom = {} # {msg_type -> [MsgStrategy]}
        self._make_builtins()

    def make_custom(self, msg_type):
        custom = self.custom.get(msg_type)
        if not custom:
            custom = []
            self.custom[msg_type] = custom
        name = "{}_v{}".format(msg_type.replace("/", "_"), len(custom) + 1)
        strategy = MsgStrategy(msg_type, name=name)
        custom.append(strategy)
        return strategy

    def make_defaults(self, msg_data):
        # msg_data :: {msg_type -> {field_name -> type_token}}
        # assume msg_data contains all dependencies
        if (not isinstance(msg_data, dict)
                or not all(isinstance(v, dict) for v in msg_data.itervalues())):
            raise TypeError("expected dict: {msg -> {field -> type}}")
        for msg_type, data in msg_data.iteritems():
            strategy = MsgStrategy(msg_type)
            self.defaults[msg_type] = strategy
            for field_name, type_token in data.iteritems():
                field = FieldStrategy(field_name,
                                      strategy=self._default(type_token))
                strategy.fields[field_name] = field

    def _default(self, type_token):
        if type_token.ros_type == "uint8" and type_token.is_array:
            return ByteArrays(length=type_token.length)
        strategy = Reuse.from_ros_type(type_token.ros_type)
        if type_token.is_array:
            return Arrays(strategy, length=type_token.length)
        return strategy

    def _make_builtins(self):
        self.defaults["bool"] = RosBoolStrategy()
        self.defaults["string"] = RosStringStrategy()
        self.defaults["time"] = RosTimeStrategy()
        self.defaults["duration"] = RosDurationStrategy()
        self.defaults["std_msgs/Header"] = HeaderStrategy()
        for ros_type in RosIntStrategy.TYPES:
            self.defaults[ros_type] = RosIntStrategy(ros_type)
        for ros_type in RosFloatStrategy.TYPES:
            self.defaults[ros_type] = RosFloatStrategy(ros_type)


###############################################################################
# Top-level Strategies
###############################################################################

class TopLevelStrategy(object):
    @property
    def name(self):
        raise NotImplementedError("subclasses must override this property")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        raise NotImplementedError("subclasses must override this method")


class RosBuiltinStrategy(TopLevelStrategy):
    __slots__ = ("ros_type",)

    TYPES = ()

    def __init__(self, ros_type):
        if not ros_type in self.TYPES:
            raise ValueError("unknown built-in type: {}".format(ros_type))
        self.ros_type = ros_type

    @property
    def name(self):
        return "ros_" + self.ros_type # $2


class MsgStrategy(TopLevelStrategy):
    TMP = ("{indent}@{module}.composite\n"
           "{indent}def {name}(draw):\n"
           "{indent}{tab}{var} = {pkg}.{msg}()\n"
           "{definition}\n"
           "{indent}{tab}return {var}")

    __slots__ = ("msg_type", "fields", "_name")

    def __init__(self, msg_type, name=None):
        self.msg_type = msg_type
        self.fields = {}
        self._name = name if name else msg_type.replace("/", "_") # $1

    @property
    def name(self):
        return self._name

    def fill_defaults(self, field_data):
        # field_data :: {field_name -> field_type}
        return () # TODO

    def to_python(self, var_name="msg", module="strategies",
                  indent=0, tab_size=4):
        assert "/" in self.msg_type
        pkg, msg = self.msg_type.split("/")
        ws = " " * indent
        mws = " " * tab_size
        body = "\n".join(f.to_python(var_name=var_name,
                                     module=module,
                                     indent=(indent + tab_size),
                                     tab_size=tab_size)
                         for f in self.fields.itervalues())
        return self.TMP.format(indent=ws, tab=mws, pkg=pkg, msg=msg,
                               name=self._name, var=var_name,
                               definition=body, module=module)


###############################################################################
# Built-in Strategies
###############################################################################

class RosBoolStrategy(RosBuiltinStrategy):
    TYPES = ("bool",)

    TMP = ("{indent}def ros_bool():\n"
           "{indent}{tab}return {module}.booleans()")

    def __init__(self):
        RosBuiltinStrategy.__init__(self, "bool")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        return self.TMP.format(indent=ws, tab=mws, module=module)


class RosIntStrategy(RosBuiltinStrategy):
    TYPES = {
        "char": (0, UINT8_MAX_VALUE),
        "uint8": (0, UINT8_MAX_VALUE),
        "byte": (INT8_MIN_VALUE, INT8_MAX_VALUE),
        "int8": (INT8_MIN_VALUE, INT8_MAX_VALUE),
        "uint16": (0, UINT16_MAX_VALUE),
        "int16": (INT16_MIN_VALUE, INT16_MAX_VALUE),
        "uint32": (0, UINT32_MAX_VALUE),
        "int32": (INT32_MIN_VALUE, INT32_MAX_VALUE),
        "uint64": (0, UINT64_MAX_VALUE),
        "int64": (INT64_MIN_VALUE, INT64_MAX_VALUE)
    }

    TMP = ("{indent}def ros_{ros_type}(min_value={min_value}, "
           "max_value={max_value}):\n"
           "{indent}{tab}if min_value <= {min_value} "
           "or min_value >= {max_value} "
           "or max_value <= {min_value} "
           "or max_value >= {max_value} "
           "or min_value > max_value:\n"
           "{indent}{tab}{tab}"
           "raise ValueError('values out of bounds: {{}}, {{}}'"
           ".format(min_value, max_value))\n"
           "{indent}{tab}return {module}.integers("
           "min_value=max(min_value, {min_value}), "
           "max_value=min(max_value, {max_value}))")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        minv, maxv = self.TYPES[self.ros_type]
        return self.TMP.format(indent=ws, ros_type=self.ros_type,
            min_value=minv, max_value=maxv, tab=mws, module=module)


class RosFloatStrategy(RosBuiltinStrategy):
    TYPES = {
        "float32": (FLOAT32_MIN_VALUE, FLOAT32_MAX_VALUE, 32),
        "float64": (FLOAT64_MIN_VALUE, FLOAT64_MAX_VALUE, 64)
    }

    TMP = ("{indent}def ros_{ros_type}(min_value={min_value}, "
           "max_value={max_value}):\n"
           "{indent}{tab}if min_value <= {min_value} "
           "or min_value >= {max_value} "
           "or max_value <= {min_value} "
           "or max_value >= {max_value} "
           "or min_value > max_value:\n"
           "{indent}{tab}{tab}"
           "raise ValueError('values out of bounds: {{}}, {{}}'"
           ".format(min_value, max_value))\n"
           "{indent}{tab}return {module}.floats("
           "min_value=max(min_value, {min_value}), "
           "max_value=min(max_value, {max_value}), "
           "width={width})")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        minv, maxv, width = self.TYPES[self.ros_type]
        return self.TMP.format(indent=ws, ros_type=self.ros_type, width=width,
            min_value=minv, max_value=maxv, tab=mws, module=module)


class RosStringStrategy(RosBuiltinStrategy):
    TYPES = ("string",)

    TMP = ("{indent}def ros_string():\n"
           "{indent}{tab}return {module}.binary("
           "min_size=0, max_size=256)")

    def __init__(self):
        RosBuiltinStrategy.__init__(self, "string")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        return self.TMP.format(indent=ws, tab=mws, module=module)


# import rospy
class RosTimeStrategy(RosBuiltinStrategy):
    TYPES = ("time",)

    TMP = ("{indent}@{module}.composite\n"
           "{indent}def ros_time(draw):\n"
           "{indent}{tab}secs = draw({module}.integers("
           "min_value=0, max_value=4294967295))\n"
           "{indent}{tab}nsecs = draw({module}.integers("
           "min_value=0, max_value=4294967295))\n"
           "{indent}{tab}return rospy.Time(secs, nsecs)")

    def __init__(self):
        RosBuiltinStrategy.__init__(self, "time")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        return self.TMP.format(indent=ws, tab=mws, module=module)


# import rospy
class RosDurationStrategy(RosBuiltinStrategy):
    TYPES = ("duration",)

    TMP = ("{indent}@{module}.composite\n"
           "{indent}def ros_duration(draw):\n"
           "{indent}{tab}secs = draw({module}.integers("
           "min_value=-2147483648, max_value=2147483647))\n"
           "{indent}{tab}nsecs = draw({module}.integers("
           "min_value=-2147483648, max_value=2147483647))\n"
           "{indent}{tab}return rospy.Duration(secs, nsecs)")

    def __init__(self):
        RosBuiltinStrategy.__init__(self, "duration")

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        return self.TMP.format(indent=ws, tab=mws, module=module)


# import std_msgs.msg as std_msgs
class HeaderStrategy(RosBuiltinStrategy):
    TYPES = ("std_msgs/Header", "Header")

    TMP = ("{indent}@{module}.composite\n"
           "{indent}def std_msgs_Header(draw):\n"
           "{indent}{tab}msg = std_msgs.Header()\n"
           "{indent}{tab}msg.stamp = draw(ros_time())\n"
           "{indent}{tab}msg.frame_id = draw(ros_string())\n"
           "{indent}{tab}return msg")

    def __init__(self):
        RosBuiltinStrategy.__init__(self, "std_msgs/Header")

    @property
    def name(self):
        return "std_msgs_Header"

    def to_python(self, var_name="v", module="strategies",
                  indent=0, tab_size=4):
        ws = " " * indent
        mws = " " * tab_size
        return self.TMP.format(indent=ws, tab=mws, module=module)


###############################################################################
# Constants
###############################################################################

class FieldStrategy(object):
    TMP = "{indent}{var}.{field} = draw({strategy})"

    __slots__ = ("field_name", "strategy", "modifiers")

    def __init__(self, field_name, strategy=None):
        self.field_name = field_name
        self.strategy = strategy
        self.modifiers = []

    def to_python(self, var_name="msg", module="strategies",
                  indent=0, tab_size=4):
        assert not self.strategy is None
        strategy = self.strategy.to_python(module=module)
        lines = [self.TMP.format(indent=(" " * indent), var=var_name,
            field=self.field_name, strategy=strategy)]
        lines.extend(m.to_python(self.field_name, var_name=var_name,
                                 module=module, indent=indent,
                                 tab_size=tab_size)
                     for m in self.modifiers)
        return "\n".join(lines)


###############################################################################
# Constants
###############################################################################

# base field modifier
class FixedValueModifier(object):
    TMP = "{indent}{var}.{field} = {value}"

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def to_python(self, field_name, var_name="msg",
                  module="strategies", indent=0, tab_size=4):
        return self.TMP.format(indent=(" " * indent), var=var_name,
                               field=field_name, value=self.value)

# base field modifier
class StrategyModifier(object):
    TMP = "{indent}{var}.{field} = draw({strategy})"

    __slots__ = ("strategy",)

    def __init__(self, strategy):
        self.strategy = strategy

    def to_python(self, field_name, var_name="msg",
                  module="strategies", indent=0, tab_size=4):
        return self.TMP.format(indent=(" " * indent), var=var_name,
            field=field_name, strategy=self.strategy.to_python(module=module))

# base field modifier
class ExclusionModifier(object):
    TMP = "{indent}assume({var}.{field} != {value})"

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def to_python(self, field_name, var_name="msg",
                  module="strategies", indent=0, tab_size=4):
        return self.TMP.format(indent=(" " * indent), var=var_name,
                               field=field_name, value=self.value)

#composite field modifier
class FixedIndexModifier(object):
    __slots__ = ("index", "modifier")

    def __init__(self, index, modifier):
        self.index = index
        self.modifier = modifier

    def to_python(self, field_name, var_name="msg",
                  module="strategies", indent=0, tab_size=4):
        field = "{}[{}]".format(field_name, self.index)
        return self.modifier.to_python(field, var_name=var_name,
            module=module, indent=indent, tab_size=tab_size)

# composite field modifier
class RandomIndexModifier(object):
    # TODO edge case of var_name == "i"
    IDX = ("{indent}i = draw({module}.integers(min_value=0, "
           "max_value=len({var}.{field})))")

    __slots__ = ("modifier",)

    def __init__(self, modifier):
        self.modifier = modifier

    def to_python(self, field_name, var_name="msg",
                  module="strategies", indent=0, tab_size=4):
        index = self.IDX.format(indent=(" " * indent), module=module,
                                var=var_name, field=field_name)
        field = field_name + "[i]"
        modifier = self.modifier.to_python(field, var_name=var_name,
            module=module, indent=indent, tab_size=tab_size)
        return index + "\n" + modifier


###############################################################################
# Constants
###############################################################################

class Reuse(object):
    @classmethod
    def from_strategy(cls, strategy):
        if not isinstance(strategy, TopLevelStrategy):
            raise TypeError("expected TopLevelStrategy, received: "
                            + repr(strategy))
        return cls(strategy.name)

    @classmethod
    def from_ros_type(cls, ros_type): # depends on $1, $2
        if "/" in ros_type:
            return cls(ros_type.replace("/", "_"))
        elif ros_type == "Header":
            return cls("std_msgs_Header")
        else:
            return cls("ros_" + ros_type)

    __slots__ = ("strategy_name",)

    def __init__(self, strategy_name):
        self.strategy_name = strategy_name

    def to_python(self, module="strategies"):
        return self.strategy_name + "()"


class Arrays(object):
    __slots__ = ("base_strategy", "length")

    def __init__(self, base_strategy, length=None):
        self.base_strategy = base_strategy
        self.length = length

    def to_python(self, module="strategies"):
        if self.length is None:
            tmp = "{}.lists(elements={}, min_size=0, max_size=256)"
            return tmp.format(module, self.base_strategy.to_python())
        assert self.length >= 0
        return "{}.tuples(*[{} for i in xrange({})])".format(
            module, self.base_strategy.to_python(module=module), self.length)


class ByteArrays(object):
    __slots__ = ("length",)

    def __init__(self, length=None):
        self.length = length

    def to_python(self, module="strategies"):
        n = 256 if self.length is None else self.length
        assert n >= 0
        return "{}.binary(min_size=0, max_size={})".format(module, n)


class Integers(object):
    __slots__ = ("min_value", "max_value")

    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    @classmethod
    def int8(cls):
        return cls(min_value=INT8_MIN_VALUE, max_value=INT8_MAX_VALUE)

    @classmethod
    def uint8(cls):
        return cls(min_value=0, max_value=UINT8_MAX_VALUE)

    @classmethod
    def int16(cls):
        return cls(min_value=INT16_MIN_VALUE, max_value=INT16_MAX_VALUE)

    @classmethod
    def uint16(cls):
        return cls(min_value=0, max_value=UINT16_MAX_VALUE)

    @classmethod
    def int32(cls):
        return cls(min_value=INT32_MIN_VALUE, max_value=INT32_MAX_VALUE)

    @classmethod
    def uint32(cls):
        return cls(min_value=0, max_value=UINT32_MAX_VALUE)

    @classmethod
    def int64(cls):
        return cls(min_value=INT64_MIN_VALUE, max_value=INT64_MAX_VALUE)

    @classmethod
    def uint64(cls):
        return cls(min_value=0, max_value=UINT64_MAX_VALUE)

    def to_python(self, module="strategies"):
        return "{}.integers(min_value={}, max_value={})".format(
            module, self.min_value, self.max_value)


class Floats(object):
    __slots__ = ("min_value", "max_value", "width")

    def __init__(self, min_value=None, max_value=None, width=64):
        self.min_value = min_value
        self.max_value = max_value
        self.width = width

    @classmethod
    def float32(cls):
        return cls(min_value=FLOAT32_MIN_VALUE,
                   max_value=FLOAT32_MAX_VALUE, width=32)

    @classmethod
    def float64(cls):
        return cls(min_value=FLOAT64_MIN_VALUE,
                   max_value=FLOAT64_MAX_VALUE, width=64)

    def to_python(self, module="strategies"):
        tmp = "{}.floats(min_value={}, max_value={}, width={})"
        return tmp.format(module, self.min_value, self.max_value, self.width)


class Booleans(object):
    def to_python(self, module="strategies"):
        return module + ".booleans()"


class Strings(object):
    def to_python(self, module="strategies"):
        return module + ".binary(min_size=0, max_size=256)"


###############################################################################
# Test Code
###############################################################################

if __name__ == "__main__":
    TEST_DATA = {
        "geometry_msgs/Twist": {
            "linear": TypeToken("geometry_msgs/Vector3"),
            "angular": TypeToken("geometry_msgs/Vector3")
        },
        "geometry_msgs/Vector3": {
            "x": TypeToken("float64"),
            "y": TypeToken("float64"),
            "z": TypeToken("float64")
        },
        "kobuki_msgs/BumperEvent": {
            "bumper": TypeToken("uint8"),
            "state": TypeToken("uint8")
        },
        "pkg/Msg": {
            "int": TypeToken("int32"),
            "float": TypeToken("float64"),
            "string": TypeToken("string"),
            "twist": TypeToken("geometry_msgs/Twist"),
            "int_list": ArrayTypeToken("int32"),
            "int_array": ArrayTypeToken("int32", length=3),
            "float_list": ArrayTypeToken("float64"),
            "float_array": ArrayTypeToken("float64", length=3),
            "string_list": ArrayTypeToken("string"),
            "string_array": ArrayTypeToken("string", length=3),
            "twist_list": ArrayTypeToken("geometry_msgs/Twist"),
            "twist_array": ArrayTypeToken("geometry_msgs/Twist", length=3),
            "nested_array": ArrayTypeToken("pkg/Nested", length=3)
        },
        "pkg/Nested": {
            "int": TypeToken("int32"),
            "int_array": ArrayTypeToken("int32", length=3),
            "nested_array": ArrayTypeToken("pkg/Nested2", length=3)
        },
        "pkg/Nested2": {
            "int": TypeToken("int32"),
            "int_array": ArrayTypeToken("int32", length=3)
        }
    }

    sm = StrategyMap()
    sm.make_defaults(TEST_DATA)
    strategies = [s.to_python() for s in sm.defaults.itervalues()]
    print "\n\n".join(strategies)

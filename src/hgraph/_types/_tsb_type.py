import functools
from abc import ABC, abstractmethod
from datetime import datetime
from functools import wraps
from typing import Union, Any, Generic, Optional, get_origin, TypeVar, Type, TYPE_CHECKING, Mapping, KeysView, \
    ItemsView, ValuesView, cast, overload

from frozendict import frozendict
from more_itertools import nth

from hgraph._types._schema_type import AbstractSchema
from hgraph._types._time_series_types import TimeSeriesInput, TimeSeriesOutput, SCALAR, DELTA_SCALAR, TimeSeriesDeltaValue, \
    TimeSeries
from hgraph._types._type_meta_data import ParseError

if TYPE_CHECKING:
    from hgraph import Node, Graph, HgTimeSeriesTypeMetaData, HgTypeMetaData, WiringNodeSignature, WiringNodeType, \
        HgTSBTypeMetaData, HgTimeSeriesSchemaTypeMetaData, SourceCodeDetails, WiringNodeInstance

__all__ = ("TimeSeriesSchema", "TSB", "TSB_OUT", "TS_SCHEMA", "is_bundle", "TimeSeriesBundle", "TimeSeriesBundleInput",
           "TimeSeriesBundleOutput", "UnNamedTimeSeriesSchema")


class TimeSeriesSchema(AbstractSchema):
    """
    Describes a time series schema, this is similar to a data class, and produces a data class to represent
    it's point-in-time value.
    """

    @classmethod
    def _parse_type(cls, tp: Type) -> "HgTypeMetaData":
        from hgraph._types._time_series_meta_data import HgTimeSeriesTypeMetaData
        return HgTimeSeriesTypeMetaData.parse(tp)


TS_SCHEMA = TypeVar("TS_SCHEMA", bound=TimeSeriesSchema)


class UnNamedTimeSeriesSchema(TimeSeriesSchema):
    """Use this class to create un-named bundle schemas"""

    @classmethod
    def create_resolved_schema(cls, schema: Mapping[str, "HgTimeSeriesTypeMetaData"]) \
            -> Type["UnNamedTimeSeriesSchema"]:
        """Creates a type instance with root class UnNamedTimeSeriesSchema using the schema provided"""
        return cls._create_resolved_class(schema)


class TimeSeriesBundle(TimeSeriesDeltaValue[Union[TS_SCHEMA, dict[str, Any]], Union[TS_SCHEMA, dict[str, Any]]], ABC,
                       Generic[TS_SCHEMA]):
    """
    Represents a non-homogenous collection of time-series values.
    We call this a time-series bundle.
    """

    def __init__(self, __schema__: TS_SCHEMA, **kwargs):
        self.__schema__: TS_SCHEMA = __schema__
        self._ts_values: Mapping[str, TimeSeriesInput] = {
            k: kwargs.get(k, None) for k in self.__schema__.__meta_data_schema__.keys()
        }  # Initialise the values to None or kwargs provided

    def __class_getitem__(cls, item) -> Any:
        # For now limit to validation of item
        out = super(TimeSeriesBundle, cls).__class_getitem__(item)
        if item is not TS_SCHEMA:
            from hgraph._types._type_meta_data import HgTypeMetaData
            if HgTypeMetaData.parse(item).is_scalar:
                raise ParseError(
                    f"Type '{item}' must be a TimeSeriesSchema or a valid TypeVar (bound to to TimeSeriesSchema)")
            if hasattr(out, "from_ts"):
                fn = out.from_ts
                code = fn.__code__
                out.from_ts = functools.partial(fn, __schema__=item)
                out.from_ts.__code__ = code
        return out

    @property
    def as_schema(self) -> TS_SCHEMA:
        """
        Exposes the TSB as the schema type. This is useful for type completion in tools such as PyCharm / VSCode.
        It is a convenience method, it is possible to access the properties of the schema directly from the TSB
        instances as well.
        """
        return self

    def __getattr__(self, item) -> TimeSeries:
        """
        The time-series value for the property associated to item in the schema
        :param item:
        :return:
        """
        ts_values = self.__dict__.get("_ts_values")
        if item == "_ts_values":
            if ts_values is None:
                raise AttributeError(item)
            return ts_values
        if ts_values and item in ts_values:
            return ts_values[item]
        else:
            return super().__getattribute__(item)

    def __getitem__(self, item: Union[int, str]) -> "TimeSeries":
        """
        If item is of type int, will return the item defined by the sequence of the schema. If it is a str, then
        the item as named.
        """
        if type(item) is int:
            return self._ts_values[nth(iter(self.__schema__.__meta_data_schema__), item)]
        else:
            return self._ts_values[item]

    def keys(self) -> KeysView[str]:
        """The keys of the schema defining the bundle"""
        return self._ts_values.keys()

    @abstractmethod
    def items(self) -> ItemsView[str, TimeSeries]:
        """The items of the bundle"""
        return self._ts_values.items()

    @abstractmethod
    def values(self) -> ValuesView[TimeSeries]:
        """The values of the bundle"""
        return self._ts_values.values()


class TimeSeriesBundleInput(TimeSeriesInput, TimeSeriesBundle[TS_SCHEMA], Generic[TS_SCHEMA]):
    """
    The input form of the bundle. This serves two purposes, one to describe the shape of the code.
    The other is to use as a Marker class for typing system. To make this work we need to implement
    the abstract methods.
    """

    @staticmethod
    def _validate_kwargs(schema: TS_SCHEMA, **kwargs):
        meta_data_schema: dict[str, "HgTypeMetaData"] = schema.__meta_data_schema__
        if any(k not in meta_data_schema for k in kwargs.keys()):
            from hgraph._wiring._wiring_errors import InvalidArgumentsProvided
            raise InvalidArgumentsProvided(tuple(k for k in kwargs.keys() if k not in meta_data_schema))

        from hgraph._wiring._wiring import WiringPort
        for k, v in kwargs.items():
            # If v is a wiring port then we perform a validation of the output type to the expected input type.
            if isinstance(v, WiringPort):
                if cast(WiringPort, v).output_type != meta_data_schema[k]:
                    from hgraph import IncorrectTypeBinding
                    from hgraph import WiringContext
                    from hgraph import STATE
                    with WiringContext(current_arg=k, current_signature=STATE(
                            signature=f"TSB[{schema.__name__}].from_ts({', '.join(kwargs.keys())})")):
                        raise IncorrectTypeBinding(expected_type=meta_data_schema[k], actual_type=v.output_type)

    @staticmethod
    def from_ts(**kwargs) -> "TimeSeriesBundleInput[TS_SCHEMA]":
        """
        Create an instance of the TSB[SCHEMA] from the kwargs provided.
        This should be used in a graph instance only. It produces an instance of an un-bound time-series bundle with
        the time-series values set to the values provided.
        This does not require all values be present, but before wiring the bundle into an input, this will be a
        requirement.
        """
        schema: TS_SCHEMA = kwargs.pop("__schema__")
        fn_details = TimeSeriesBundleInput.from_ts.__code__
        from hgraph import WiringNodeSignature, WiringNodeType, SourceCodeDetails, HgTSBTypeMetaData, \
            HgTimeSeriesSchemaTypeMetaData, WiringNodeInstance
        wiring_node_signature = WiringNodeSignature(
            node_type=WiringNodeType.STUB,
            name=f"TSB[{schema.__name__}].from_ts",
            args=tuple(kwargs.keys()),
            defaults=frozendict(),
            input_types=frozendict(schema.__meta_data_schema__),
            output_type=HgTSBTypeMetaData(HgTimeSeriesSchemaTypeMetaData(schema)),
            src_location=SourceCodeDetails(fn_details.co_filename, fn_details.co_firstlineno),
            active_inputs=None,
            valid_inputs=None,
            unresolved_args=frozenset(),
            time_series_args=frozenset(kwargs.keys()),
            uses_scheduler=False
        )
        TimeSeriesBundleInput._validate_kwargs(schema, **kwargs)
        from hgraph._wiring._wiring import TSBWiringPort, NonPeeredWiringNodeClass
        wiring_node = NonPeeredWiringNodeClass(wiring_node_signature, lambda *args, **kwargs: None)
        wiring_node_instance = WiringNodeInstance(
            node=wiring_node,
            resolved_signature=wiring_node_signature,
            inputs=frozendict(kwargs),
            rank=max(v.rank for k, v in kwargs.items())
        )
        return TSBWiringPort(wiring_node_instance, tuple())

    def copy_with(self, __init_args__: dict = None, **kwargs):
        """
        Creates a new instance of a wiring time bundle using the values of this instance combined / overridden from
        the kwargs provided. Can be used to clone a runtime instance of a bundle as well.
        # TODO: support k: REMOVE semantics to remove a value from the bundle?
        """
        self._validate_kwargs(self.__schema__, **kwargs)
        value = self.__class__[self.__schema__](self.__schema__) if __init_args__ is None else \
            self.__class__[self.__schema__](self.__schema__, **__init_args__)
        value._ts_values = self._ts_values | kwargs
        return value

    @property
    def parent_input(self) -> Optional["TimeSeriesInput"]:
        raise NotImplementedError()

    @property
    def has_parent_input(self) -> bool:
        raise NotImplementedError()

    @property
    def bound(self) -> bool:
        raise NotImplementedError()

    @property
    def output(self) -> Optional[TimeSeriesOutput]:
        raise NotImplementedError()

    def do_bind_output(self, value: TimeSeriesOutput):
        raise NotImplementedError()

    @property
    def active(self) -> bool:
        raise NotImplementedError()

    def make_active(self):
        raise NotImplementedError()

    def make_passive(self):
        raise NotImplementedError()

    @property
    def value(self) -> Optional[SCALAR]:
        raise NotImplementedError()

    @property
    def delta_value(self) -> Optional[DELTA_SCALAR]:
        raise NotImplementedError()

    @property
    def owning_node(self) -> "Node":
        raise NotImplementedError()

    @property
    def owning_graph(self) -> "Graph":
        raise NotImplementedError()

    @property
    def modified(self) -> bool:
        raise NotImplementedError()

    @property
    def valid(self) -> bool:
        raise NotImplementedError()

    @property
    def all_valid(self) -> bool:
        raise NotImplementedError()

    @property
    def last_modified_time(self) -> datetime:
        raise NotImplementedError()

    def items(self) -> ItemsView[str, TimeSeriesInput]:
        return super().items()

    def values(self) -> ValuesView[TimeSeriesInput]:
        return super().values()


class TimeSeriesBundleOutput(TimeSeriesOutput, TimeSeriesBundle[TS_SCHEMA], ABC, Generic[TS_SCHEMA]):
    """
    The output form of the bundle
    """

    def items(self) -> ItemsView[str, TimeSeriesOutput]:
        return super().items()

    def values(self) -> ValuesView[TimeSeriesOutput]:
        return super().values()


TSB = TimeSeriesBundleInput
TSB_OUT = TimeSeriesBundleOutput


def is_bundle(bundle: Union[type, TimeSeriesBundle]) -> bool:
    """Is the value a TimeSeriesBundle type, or an instance of a TimeSeriesBundle"""
    return (origin := get_origin(bundle)) and issubclass(origin, TimeSeriesBundle) or isinstance(bundle,
                                                                                                 TimeSeriesBundle)

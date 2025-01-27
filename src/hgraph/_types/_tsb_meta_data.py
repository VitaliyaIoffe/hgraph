from hashlib import sha1
from typing import Type, Optional, TypeVar, _GenericAlias

from more_itertools import nth

from hgraph._types._time_series_meta_data import HgTimeSeriesTypeMetaData
from hgraph._types._ts_type_var_meta_data import HgTsTypeVarTypeMetaData
from hgraph._types._type_meta_data import ParseError

__all__ = ("HgTimeSeriesSchemaTypeMetaData", "HgTSBTypeMetaData",)


class HgTimeSeriesSchemaTypeMetaData(HgTimeSeriesTypeMetaData):
    """
    Parses time series schema types, for example:
    ```python
    class MySchema(TimeSeriesSchema):
        p1: TS[str]
    ```
    """

    py_type: Type

    def __init__(self, py_type):
        self.py_type = py_type

    def __getitem__(self, item):
        if type(item) is int:
            return nth(self.meta_data_schema.values(), item)
        else:
            return self.meta_data_schema[item]

    def matches(self, tp: "HgTypeMetaData") -> bool:
        return isinstance(tp,
                          HgTimeSeriesSchemaTypeMetaData) and \
            self.meta_data_schema().keys() == tp.meta_data_schema().keys() and \
            all( v.matches(w_v) for v, w_v in zip(self.meta_data_schema.values(), tp.meta_data_schema.values()))

    @property
    def meta_data_schema(self) -> dict[str, "HgTimeSeriesTypeMetaData"]:
        return self.py_type.__meta_data_schema__

    @property
    def is_resolved(self) -> bool:
        return all(v.is_resolved for v in self.meta_data_schema.values())

    def resolve(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], weak=False) -> "HgTypeMetaData":
        if self.is_resolved:
            return self
        else:
            schema = {k: v.resolve(resolution_dict, weak) for k, v in self.meta_data_schema.items()}
            return HgTimeSeriesSchemaTypeMetaData(self.py_type._create_resolved_class(schema))

    def do_build_resolution_dict(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], wired_type: "HgTypeMetaData"):
        super().do_build_resolution_dict(resolution_dict, wired_type)
        wired_type: HgTimeSeriesSchemaTypeMetaData
        if len(self.meta_data_schema) != len(wired_type.meta_data_schema):
            raise ParseError(f"'{self.py_type}' schema does not match '{wired_type.py_type}'")
        if any(k not in wired_type.meta_data_schema for k in self.meta_data_schema.keys()):
            raise ParseError("Keys of schema do not match")
        for v, w_v in zip(self.meta_data_schema.values(), wired_type.meta_data_schema.values()):
            v.build_resolution_dict(resolution_dict, w_v)

    @property
    def has_references(self) -> bool:
        return any(tp.has_references for tp in self.meta_data_schema.values())

    def dereference(self) -> "HgTimeSeriesTypeMetaData":
        if self.has_references:
            return HgTimeSeriesSchemaTypeMetaData(self.py_type.dereference())
        else:
            return self

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tsb_type import TimeSeriesSchema
        if isinstance(value, type) and issubclass(value, TimeSeriesSchema):
            return HgTimeSeriesSchemaTypeMetaData(value)
        return None

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTimeSeriesSchemaTypeMetaData and self.py_type == o.py_type

    def __str__(self) -> str:
        return self.py_type.__name__

    def __repr__(self) -> str:
        return f'HgTimeSeriesSchemaTypeMetaData({repr(self.py_type)})'

    def __hash__(self) -> int:
        return hash(self.py_type)


class HgTSBTypeMetaData(HgTimeSeriesTypeMetaData):
    bundle_schema_tp: HgTimeSeriesSchemaTypeMetaData

    def __init__(self, schema):
        self.bundle_schema_tp = schema

    @property
    def is_resolved(self) -> bool:
        return self.bundle_schema_tp.is_resolved

    @property
    def py_type(self) -> Type:
        from hgraph._types import TSB
        return TSB[self.bundle_schema_tp.py_type]

    def resolve(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], weak=False) -> "HgTypeMetaData":
        if self.is_resolved:
            return self
        else:
            return type(self)(self.bundle_schema_tp.resolve(resolution_dict, weak))

    def do_build_resolution_dict(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], wired_type: "HgTypeMetaData"):
        super().do_build_resolution_dict(resolution_dict, wired_type)
        wired_type: HgTSBTypeMetaData
        self.bundle_schema_tp.build_resolution_dict(resolution_dict, wired_type.bundle_schema_tp)

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tsb_type import TimeSeriesBundleInput
        if isinstance(value, _GenericAlias) and value.__origin__ is TimeSeriesBundleInput:
            bundle_tp = HgTimeSeriesTypeMetaData.parse(value.__args__[0])
            if bundle_tp is None or not isinstance(bundle_tp,
                                                   (HgTimeSeriesSchemaTypeMetaData, HgTsTypeVarTypeMetaData)):
                raise ParseError(f"'{value.__args__[0]}' is not a valid input to TSB")
            return HgTSBTypeMetaData(bundle_tp)

    @property
    def has_references(self) -> bool:
        return self.bundle_schema_tp.has_references

    def dereference(self) -> "HgTimeSeriesTypeMetaData":
        if self.has_references:
            return HgTSBTypeMetaData(self.bundle_schema_tp.dereference())
        else:
            return self

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTSBTypeMetaData and self.bundle_schema_tp == o.bundle_schema_tp

    def __str__(self) -> str:
        return f'TSB[{str(self.bundle_schema_tp)}]'

    def __repr__(self) -> str:
        return f'HgTSTypeMetaData({repr(self.bundle_schema_tp)})'

    def __hash__(self) -> int:
        from hgraph._types import TSB
        return hash(TSB) ^ hash(self.bundle_schema_tp)

    def __getitem__(self, item):
        return self.bundle_schema_tp[item]

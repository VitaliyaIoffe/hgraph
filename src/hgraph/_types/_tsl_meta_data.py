from typing import Type, TypeVar, Optional, _GenericAlias, TYPE_CHECKING, cast

from hgraph._types._type_meta_data import ParseError
from hgraph._types._scalar_type_meta_data import HgScalarTypeMetaData
from hgraph._types._time_series_meta_data import HgTimeSeriesTypeMetaData, HgTypeMetaData

if TYPE_CHECKING:
    from hgraph._types._scalar_types import Size

__all__ = ("HgTSLTypeMetaData", "HgTSLOutTypeMetaData",)


class HgTSLTypeMetaData(HgTimeSeriesTypeMetaData):
    """Parses TSL[..., Size[...]]"""

    value_tp: HgTimeSeriesTypeMetaData
    size_tp: HgScalarTypeMetaData

    def __init__(self, value_tp: HgTimeSeriesTypeMetaData, size_tp: HgScalarTypeMetaData):
        self.value_tp = value_tp
        self.size_tp = size_tp

    def matches(self, tp: "HgTypeMetaData") -> bool:
        return isinstance(tp, HgTSLTypeMetaData) and self.value_tp.matches(tp.value_tp) and self.size_tp.matches(
            tp.size_tp)

    @property
    def size(self) -> "Size":
        return cast("Size", self.size_tp.py_type)

    @property
    def is_resolved(self) -> bool:
        return self.value_tp.is_resolved and self.size_tp.is_resolved

    @property
    def py_type(self) -> Type:
        from hgraph._types import TSL
        return TSL[self.value_tp.py_type, self.size_tp.py_type]

    def resolve(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], weak=False) -> "HgTypeMetaData":
        if self.is_resolved:
            return self
        else:
            return type(self)(self.value_tp.resolve(resolution_dict, weak), self.size_tp.resolve(resolution_dict, weak))

    def do_build_resolution_dict(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], wired_type: "HgTypeMetaData"):
        super().do_build_resolution_dict(resolution_dict, wired_type)
        wired_type: HgTSLTypeMetaData
        self.value_tp.build_resolution_dict(resolution_dict, wired_type.value_tp)
        self.size_tp.build_resolution_dict(resolution_dict, wired_type.size_tp)

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tsl_type import TimeSeriesListInput
        if isinstance(value, _GenericAlias) and value.__origin__ is TimeSeriesListInput:
            v_meta_data = HgTimeSeriesTypeMetaData.parse(value.__args__[0])
            sz_meta_data = HgScalarTypeMetaData.parse(value.__args__[1])
            if v_meta_data is None:
                raise ParseError(f"'{value.__args__[0]}' is not a valid time-series type")
            from hgraph._types._scalar_types import Size
            if sz_meta_data is None or (sz_meta_data.is_resolved and not issubclass(sz_meta_data.py_type, Size)):
                raise ParseError(f"'{value.__args__[1]}' is not a valid Size type")
            return HgTSLTypeMetaData(v_meta_data, sz_meta_data)

    @property
    def has_references(self) -> bool:
        return self.value_tp.has_references

    def dereference(self) -> "HgTimeSeriesTypeMetaData":
        if self.has_references:
            return self.__class__(self.value_tp.dereference(), self.size_tp)
        else:
            return self

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTSLTypeMetaData and self.value_tp == o.value_tp and self.size_tp == o.size_tp

    def _to_str(self, tp: str = 'TSL') -> str:
        return f'TSL[{str(self.value_tp)}, {str(self.size_tp)}]' if self.size_tp else f'TSL[{str(self.value_tp)}]'

    def __str__(self) -> str:
        return self._to_str()

    def __repr__(self) -> str:
        return f'HgTSLTypeMetaData({repr(self.value_tp)}, {repr(self.size_tp)})'

    def __hash__(self) -> int:
        from hgraph._types._ts_type import TS
        return hash(TS) ^ hash(self.value_tp) ^ hash(self.size_tp)

    def __getitem__(self, item):
        return self.value_tp  # All instances of TSL are the same type


class HgTSLOutTypeMetaData(HgTSLTypeMetaData):
    """Parses TSLOut[..., Size[...]]"""

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tsl_type import TimeSeriesListOutput
        if isinstance(value, _GenericAlias) and value.__origin__ is TimeSeriesListOutput:
            v_meta_data = HgTimeSeriesTypeMetaData.parse(value.__args__[0])
            sz_meta_data = HgScalarTypeMetaData.parse(value.__args__[1])
            if v_meta_data is None:
                raise ParseError(f"'{value.__args__[0]}' is not a valid time-series type")
            from hgraph import Size
            if sz_meta_data is None or (sz_meta_data.is_resolved and not issubclass(sz_meta_data.py_type, Size)):
                raise ParseError(f"'{value.__args__[1]}' is not a valid Size type")
            return HgTSLOutTypeMetaData(v_meta_data, sz_meta_data)

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTSLOutTypeMetaData and self.value_tp == o.value_tp and self.size_tp == o.size_tp

    def __str__(self) -> str:
        return self._to_str('TSL_OUT')

    def __repr__(self) -> str:
        return f'HgTSLOutTypeMetaData({repr(self.value_tp)}, {repr(self.size_tp)})'

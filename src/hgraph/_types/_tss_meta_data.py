from typing import Type, TypeVar, Optional, _GenericAlias

from hgraph._types._type_meta_data import HgTypeMetaData
from hgraph._types._scalar_type_meta_data import HgScalarTypeMetaData
from hgraph._types._time_series_meta_data import HgTimeSeriesTypeMetaData


__all__ = ("HgTSSTypeMetaData", "HgTSSOutTypeMetaData",)


class HgTSSTypeMetaData(HgTimeSeriesTypeMetaData):
    """Parses TSS[...]"""

    value_scalar_tp: HgScalarTypeMetaData

    def __init__(self, scalar_type: HgScalarTypeMetaData):
        self.value_scalar_tp = scalar_type

    def matches(self, tp: "HgTypeMetaData") -> bool:
        return isinstance(tp, HgTSSTypeMetaData) and self.value_scalar_tp.matches(tp.value_scalar_tp)

    @property
    def is_resolved(self) -> bool:
        return self.value_scalar_tp.is_resolved

    @property
    def py_type(self) -> Type:
        from hgraph._types import TSS
        return TSS[self.value_scalar_tp.py_type]

    def resolve(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], weak=False) -> "HgTypeMetaData":
        if self.is_resolved:
            return self
        else:
            return type(self)(self.value_scalar_tp.resolve(resolution_dict, weak))

    def do_build_resolution_dict(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], wired_type: "HgTypeMetaData"):
        super().do_build_resolution_dict(resolution_dict, wired_type)
        wired_type: HgTSSTypeMetaData
        self.value_scalar_tp.build_resolution_dict(resolution_dict, wired_type.value_scalar_tp)

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tss_type import TimeSeriesSetInput
        if isinstance(value, _GenericAlias) and value.__origin__ is TimeSeriesSetInput:
            return HgTSSTypeMetaData(HgScalarTypeMetaData.parse(value.__args__[0]))

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTSSTypeMetaData and self.value_scalar_tp == o.value_scalar_tp

    def __str__(self) -> str:
        return f'TSS[{str(self.value_scalar_tp)}]'

    def __repr__(self) -> str:
        return f'HgTSSTypeMetaData({repr(self.value_scalar_tp)})'

    def __hash__(self) -> int:
        from hgraph._types import TSS
        return hash(TSS) ^ hash(self.value_scalar_tp)


class HgTSSOutTypeMetaData(HgTSSTypeMetaData):

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._tss_type import TimeSeriesSetOutput
        if isinstance(value, _GenericAlias) and value.__origin__ is TimeSeriesSetOutput:
            return HgTSSOutTypeMetaData(HgScalarTypeMetaData.parse(value.__args__[0]))

    def __eq__(self, o: object) -> bool:
        return type(o) is HgTSSOutTypeMetaData and self.value_scalar_tp == o.value_scalar_tp

    def __str__(self) -> str:
        return f'TSS_OUT[{str(self.value_scalar_tp)}]'

    def __repr__(self) -> str:
        return f'HgTSSOutTypeMetaData({repr(self.value_scalar_tp)})'

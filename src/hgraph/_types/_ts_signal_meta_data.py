from typing import Type, TypeVar, Optional

__all__ = ("HgSignalMetaData",)

from hgraph._types._tsb_meta_data import HgTimeSeriesTypeMetaData


class HgSignalMetaData(HgTimeSeriesTypeMetaData):
    """Parses SIGNAL"""

    @property
    def is_resolved(self) -> bool:
        return True

    @property
    def py_type(self) -> Type:
        from hgraph._types._time_series_types import SIGNAL
        return SIGNAL

    def matches(self, tp: "HgTypeMetaData") -> bool:
        return isinstance(tp, HgTimeSeriesTypeMetaData)

    def resolve(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], weak=False) -> "HgTypeMetaData":
        return self

    def do_build_resolution_dict(self, resolution_dict: dict[TypeVar, "HgTypeMetaData"], wired_type: "HgTypeMetaData"):
        pass  # SIGNAL has no possible validation or resolution logic

    @classmethod
    def parse(cls, value) -> Optional["HgTypeMetaData"]:
        from hgraph._types._time_series_types import SIGNAL
        if value is SIGNAL:
            return HgSignalMetaData()

    def __eq__(self, o: object) -> bool:
        return type(o) is HgSignalMetaData

    def __str__(self) -> str:
        return 'SIGNAL'

    def __repr__(self) -> str:
        return 'HgSignalMetaData()'

    def __hash__(self) -> int:
        from hgraph._types._time_series_types import SIGNAL
        return hash(SIGNAL)
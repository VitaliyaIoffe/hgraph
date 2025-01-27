import typing

from _pytest.nodes import Node

from hgraph._builder._builder import Builder

if typing.TYPE_CHECKING:
    from hgraph._types._time_series_types import TimeSeriesInput


__all__ = ('InputBuilder',)


class InputBuilder(Builder["TimeSeriesInput"]):

    def make_instance(self, owning_node: Node = None, owning_input: "TimeSeriesInput" = None) -> "TimeSeriesInput":
        """One of owning_node or owning_input must be defined."""
        pass

    def release_instance(self, item: "TimeSeriesInput"):
        pass

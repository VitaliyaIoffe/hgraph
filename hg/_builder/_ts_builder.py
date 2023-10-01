from dataclasses import dataclass

from _pytest.nodes import Node

from hg._builder._input_builder import InputBuilder
from hg._builder._output_builder import OutputBuilder
from hg._builder._scalar_builder import ScalarValueBuilder
from hg._types._time_series_types import TimeSeriesInput, TimeSeriesOutput


@dataclass(frozen=True)
class TimeSeriesValueOutputBuilder(OutputBuilder):

    scalar_value_builder: ScalarValueBuilder

    def make_instance(self, owning_node=None, owning_output=None) -> TimeSeriesOutput:
        pass

    def release_instance(self, item: TimeSeriesOutput):
        pass


@dataclass(frozen=True)
class TimeSeriesValueInputBuilder(InputBuilder):

    def make_instance(self, owning_node: Node = None, owning_input: TimeSeriesInput = None) -> TimeSeriesInput:
        ...

    def release_instance(self, item: TimeSeriesInput):
        ...
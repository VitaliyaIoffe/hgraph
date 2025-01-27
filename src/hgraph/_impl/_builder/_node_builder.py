from dataclasses import dataclass
from typing import Callable

from hgraph._builder._node_builder import NodeBuilder
from hgraph._impl._runtime._node import NodeImpl, GeneratorNodeImpl, PythonPushQueueNodeImpl
from hgraph._types._time_series_types import TimeSeriesOutput
from hgraph._types._tsb_type import TimeSeriesBundleInput


__all__ = ("PythonNodeBuilder", "PythonGeneratorNodeBuilder", "PythonPushQueueNodeBuilder")


@dataclass(frozen=True)
class PythonNodeBuilder(NodeBuilder):
    eval_fn: Callable = None  # The eval fn must be supplied.
    start_fn: Callable = None
    stop_fn: Callable = None

    def make_instance(self, owning_graph_id: tuple[int, ...]) -> NodeImpl:
        node = NodeImpl(
            node_ndx=self.node_ndx,
            owning_graph_id=owning_graph_id,
            signature=self.signature,
            scalars=self.scalars,
            eval_fn=self.eval_fn,
            start_fn=self.start_fn,
            stop_fn=self.stop_fn
        )

        if self.input_builder:
            ts_input: TimeSeriesBundleInput = self.input_builder.make_instance(owning_node=node)
            node.input = ts_input

        if self.output_builder:
            ts_output: TimeSeriesOutput = self.output_builder.make_instance(owning_node=node)
            node.output = ts_output

        return node

    def release_instance(self, item: NodeImpl):
        pass


@dataclass(frozen=True)
class PythonGeneratorNodeBuilder(NodeBuilder):
    eval_fn: Callable = None  # This is the generator function

    def make_instance(self, owning_graph_id: tuple[int, ...]) -> GeneratorNodeImpl:
        node = GeneratorNodeImpl(
            node_ndx=self.node_ndx,
            owning_graph_id=owning_graph_id,
            signature=self.signature,
            scalars=self.scalars,
            eval_fn=self.eval_fn
        )

        if self.output_builder:
            ts_output: TimeSeriesOutput = self.output_builder.make_instance(owning_node=node)
            node.output = ts_output

        return node

    def release_instance(self, item: GeneratorNodeImpl):
        pass


@dataclass(frozen=True)
class PythonPushQueueNodeBuilder(NodeBuilder):
    eval_fn: Callable = None  # This is the generator function

    def make_instance(self, owning_graph_id: tuple[int, ...]) -> PythonPushQueueNodeImpl:
        node = PythonPushQueueNodeImpl(
            node_ndx=self.node_ndx,
            owning_graph_id=owning_graph_id,
            signature=self.signature,
            scalars=self.scalars,
            eval_fn=self.eval_fn
        )

        if self.output_builder:
            ts_output: TimeSeriesOutput = self.output_builder.make_instance(owning_node=node)
            node.output = ts_output

        return node

    def release_instance(self, item: PythonPushQueueNodeImpl):
        pass
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Mapping, TYPE_CHECKING, Any, Protocol

from hg._runtime._lifecycle import ComponentLifeCycle

if TYPE_CHECKING:
    from hg._types import HgTimeSeriesTypeMetaData
    from hg._types._time_series_types import TimeSeriesInput, TimeSeriesOutput
    from hg._types._tsb_type import TimeSeriesBundleInput
    from hg._runtime._graph import Graph
    from hg._wiring._source_code_details import SourceCodeDetails


__all__ = ("Node", "NodeTypeEnum", "NodeSignature")


class NodeTypeEnum(Enum):
    PUSH_SOURCE_NODE = 0
    PULL_SOURCE_NODE = 1
    COMPUTE_NODE = 2
    SINK_NODE = 3


@dataclass
class NodeSignature:
    """
    This is the generic node signature that can be referenced by all instances of the node.
    The resolved scalar values are stored on the instance only.
    """
    name: str
    node_type: NodeTypeEnum
    args: tuple[str, ...]
    time_series_inputs: Optional[Mapping[str, "HgTimeSeriesTypeMetaData"]]
    time_series_output: Optional["HgTimeSeriesTypeMetaData"]
    src_location: "SourceCodeDetails"


class Node(ComponentLifeCycle, Protocol):

    @property
    @abstractmethod
    def node_ndx(self) -> int:
        """
        The relative index of this node within the parent graph's list of nodes.
        """

    @property
    @abstractmethod
    def owning_graph_id(self) -> tuple[int, ...]:
        """
        The path from the root graph to the graph containing this node. This is effectively
        the node_id less the last entry. Thus, the root graph is referenced as (),
        the first child if (node_ndx of nested_1), ...
        """

    @property
    @abstractmethod
    def node_id(self) -> tuple[int, ...]:
        """
        The unique path reference to this node from the root graph running in the system.
        For a node directly attached to the root graph, the path will be:
        (node_ndx)
        For a node within a nested graph structure, it will be something like:
        (node_ndx of nested_1, ..., node_ndx of nested_n, node_ndx)
        For nodes with a dynamic nested structure such as a branch, a unique id (integer) is allocated to
        a branch key and this id is used to represent the key in the path.
        This is similar to the categorical concept in dataframes.
        """

    @property
    @abstractmethod
    def signature(self) -> NodeSignature:
        """
        The signature of the Node provides useful information to describe the node.
        This can be used for exception and debugging purposes.
        """

    @property
    @abstractmethod
    def scalars(self) -> Mapping[str, Any]:
        """
        The scalar values associated to this node. These are the values that are not time-series.
        """

    @property
    @abstractmethod
    def graph(self) -> "Graph":
        """
        The graph that this node is a member of.
        """

    @graph.setter
    @abstractmethod
    def graph(self, value: "Graph"):
        """
        The graph that this node is a member of.
        """

    @property
    @abstractmethod
    def input(self) -> Optional["TimeSeriesBundleInput"]:
        """
        The input as an Unnamed Bundle. This allows the input to be considered as a TSB
        which is helpful for standardising handling of inputs. The bundle schema is the
        collection of inputs that are of time-series types.
        """

    @property
    @abstractmethod
    def inputs(self) -> Optional[Mapping[str, "TimeSeriesInput"]]:
        """
        The inputs associated to this node.
        """

    @property
    @abstractmethod
    def output(self) -> Optional["TimeSeriesOutput"]:
        """
        The output of this node. This could be a TimeSeriesBundleOutput or a single output value.
        """

    @property
    @abstractmethod
    def outputs(self) -> Optional[Mapping[str, "TimeSeriesOutput"]]:
        """
        The outputs of the node. If the node has a single defined output then this is just {"out": Output},
        however if the node was defined with multiple outputs using the "un-named bundle" dictionary format,
        then these are the outputs defined by the dictionary definition.
        """

    def eval(self):
        """Called by the graph evaluation engine when the node has been scheduled for evaluation."""



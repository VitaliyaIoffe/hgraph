from typing import Mapping, Any, TYPE_CHECKING

from frozendict import frozendict

from hgraph._impl._builder._switch_builder import PythonSwitchNodeBuilder
from hgraph._types import SCALAR
from hgraph._wiring._wiring import BaseWiringNodeClass, WiringNodeClass, create_input_output_builders
from hgraph._wiring._wiring_node_signature import WiringNodeSignature
from hgraph._wiring._wiring_utils import wire_nested_graph, extract_stub_node_indices

if TYPE_CHECKING:
    from hgraph._runtime._node import NodeSignature
    from hgraph._builder._node_builder import NodeBuilder

__all__ = ("SwitchWiringNodeClass",)


class SwitchWiringNodeClass(BaseWiringNodeClass):
    """The outer switch node"""

    def __init__(self, signature: WiringNodeSignature,
                 nested_graphs: Mapping[SCALAR, WiringNodeClass],
                 resolved_signature_inner: WiringNodeSignature,
                 reload_on_ticked: bool):
        super().__init__(signature, None)
        self._nested_graphs = nested_graphs
        self._resolved_signature_inner = resolved_signature_inner
        self._reload_on_ticked = reload_on_ticked

    def create_node_builder_instance(self, node_ndx: int, node_signature: "NodeSignature",
                                     scalars: Mapping[str, Any]) -> "NodeBuilder":
        # create nested graphs
        nested_graphs = {k: wire_nested_graph(v, self._resolved_signature_inner, scalars, self.signature) for k, v in
                         self._nested_graphs.items()}
        nested_graph_input_ids = {}
        nested_graph_output_ids = {}
        for k, v in nested_graphs.items():
            nested_graph_input_ids[k], nested_graph_output_ids[k] = \
                extract_stub_node_indices(v, self._resolved_signature_inner.time_series_args)

        input_builder, output_builder = create_input_output_builders(node_signature)

        return PythonSwitchNodeBuilder(node_ndx, node_signature, scalars, input_builder, output_builder,
                                       frozendict(nested_graphs), frozendict(nested_graph_input_ids),
                                       frozendict(nested_graph_output_ids), self._reload_on_ticked)

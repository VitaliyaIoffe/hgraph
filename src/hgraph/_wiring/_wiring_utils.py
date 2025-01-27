from dataclasses import dataclass
from typing import Mapping, Any, cast, TYPE_CHECKING
from collections.abc import Set

from frozendict import frozendict

from hgraph._wiring._wiring import WiringNodeClass, WiringGraphContext

from hgraph._wiring._stub_wiring_node import create_input_stub, create_output_stub
from hgraph._wiring._wiring_node_signature import WiringNodeSignature
from hgraph._types._ref_meta_data import HgREFTypeMetaData
from hgraph._types._time_series_meta_data import HgTimeSeriesTypeMetaData
from hgraph._types._tsd_meta_data import HgTSDTypeMetaData
from hgraph._types._tsl_meta_data import HgTSLTypeMetaData
from hgraph._types._type_meta_data import HgTypeMetaData
from hgraph._wiring._wiring import WiringPort
from hgraph._wiring._wiring_errors import CustomMessageWiringError

if TYPE_CHECKING:
    from hgraph._builder._graph_builder import GraphBuilder

__all__ = ("stub_wiring_port", "StubWiringPort", "as_reference", "wire_nested_graph", "extract_stub_node_indices")


@dataclass(frozen=True)
class StubWiringPort(WiringPort):
    _value_tp: HgTypeMetaData = None

    @property
    def output_type(self) -> HgTypeMetaData:
        return self._value_tp

    @property
    def rank(self) -> int:
        return 1


def stub_wiring_port(value_tp: HgTimeSeriesTypeMetaData) -> WiringPort:
    return StubWiringPort(node_instance=None, _value_tp=value_tp)


def as_reference(tp_: HgTimeSeriesTypeMetaData, is_multiplexed: bool = False) -> HgTypeMetaData:
    """
    Create a reference type for the supplied type if the type is not already a reference type.
    """
    if is_multiplexed:
        # If multiplexed type, we want references to the values not the whole output.
        if type(tp_) is HgTSDTypeMetaData:
            tp_: HgTSDTypeMetaData
            return HgTSDTypeMetaData(tp_.key_tp, HgREFTypeMetaData(tp_.value_tp) if type(
                tp_.value_tp) is not HgREFTypeMetaData else tp_.value_tp)
        elif type(tp_) is HgTSLTypeMetaData:
            tp_: HgTSLTypeMetaData
            return HgTSLTypeMetaData(
                HgREFTypeMetaData(tp_.value_tp) if type(tp_.value_tp) is not HgREFTypeMetaData else tp_.value_tp,
                tp_.size_tp)
        else:
            raise CustomMessageWiringError(f"Unable to create reference for multiplexed type: {tp_}")
    else:
        return HgREFTypeMetaData(tp_) if type(tp_) is not HgREFTypeMetaData else tp_


def wire_nested_graph(fn: WiringNodeClass,
                      resolved_wiring_signature: WiringNodeSignature,
                      scalars: Mapping[str, Any],
                      outer_wiring_node_signature: WiringNodeSignature) -> "GraphBuilder":
    """
    Wire the inner function using stub inputs and wrap stub outputs.
    The outer wiring node signature is used to supply to the wiring graph context, this is for error and stack trace
    uses.
    """
    from hgraph._wiring._graph_builder import create_graph_builder
    inputs_ = {}
    for k, v in resolved_wiring_signature.input_types.items():
        if v.is_scalar:
            inputs_[k] = scalars[k]
        else:
            inputs_[k] = create_input_stub(k, cast(HgTimeSeriesTypeMetaData, v))
    with WiringGraphContext(outer_wiring_node_signature) as context:
        out = fn(**inputs_)
        if out is not None:
            create_output_stub(cast(WiringPort, out))
        sink_nodes = context.pop_sink_nodes()
        return create_graph_builder(sink_nodes)


def extract_stub_node_indices(inner_graph, input_args: Set[str]) \
        -> tuple[frozendict[str, int], int]:
    """Process the stub graph identifying the input and output nodes for the associated stubs."""

    input_node_ids = {}
    output_node_id = None
    STUB_PREFIX = "stub:"
    STUB_PREFIX_LEN = len(STUB_PREFIX)
    for node_builder in inner_graph.node_builders:
        if (inner_node_signature := node_builder.signature).name.startswith(STUB_PREFIX):
            if (arg := inner_node_signature.name[STUB_PREFIX_LEN:]) in input_args:
                input_node_ids[arg] = node_builder.node_ndx
            elif arg == "__out__":
                output_node_id = node_builder.node_ndx
    return frozendict(input_node_ids), output_node_id

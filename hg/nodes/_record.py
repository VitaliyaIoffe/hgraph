from datetime import datetime
from typing import Any

from hg import sink_node, TIME_SERIES_TYPE, ExecutionContext, GlobalState, STATE


@sink_node
def record(ts: TIME_SERIES_TYPE, label: str = "out", record_delta_values: bool = True,
           context: ExecutionContext = None, state: STATE = None):
    """
    This node will record the values of the time series into the provided list.
    """
    state.record_value.append((context.current_engine_time,
                               ts.delta_scalar_value.cast(object) if record_delta_values else ts.scalar_value.cast(
                                   object)))


@record.start
def record_start(label: str, state: STATE):
    value = []
    global_state = GlobalState.instance()
    global_state[f"nodes.{record.signature.name}.{label}"] = value
    state.record_value = value


def get_recorded_value(label: str = "out") -> list[tuple[datetime, Any]]:
    """
    Returns the recorded values for the given label.
    """
    global_state = GlobalState.instance()
    return global_state[f"nodes.{record.signature.name}.{label}"]
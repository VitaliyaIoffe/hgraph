from traceback import print_exc
from typing import Any

from hgraph import graph, run_graph, GlobalState, MIN_TD, HgTypeMetaData, HgTSTypeMetaData, prepare_kwargs, MIN_ST, MIN_DT, \
    WiringContext, WiringError
from hgraph.nodes import replay, record, SimpleArrayReplaySource, set_replay_values, get_recorded_value


def eval_node(node, *args, resolution_dict: [str, Any] = None, **kwargs):
    """
    Evaluates a node using the supplied arguments.
    This will detect time-series inputs in the node and will convert array inputs into time-series inputs.
    If the node returns a result, the results will be collected and returned as an array.

    For nodes that require resolution, it is possible to supply a resolution dictionary to assist
    in resolving correct types when setting up the replay nodes.
    """
    if not hasattr(node, "signature"):
        if callable(node):
            raise RuntimeError(f"The node '{node}' should be decorated with either a node or graph decorator")
        else:
            raise RuntimeError(f"The node '{node}' does not appear to be a node or graph function")
    try:
        with WiringContext(current_signature=node.signature):
            kwargs_ = prepare_kwargs(node.signature, *args, _ignore_defaults=True, **kwargs)
    except WiringError as e:
        e.print_error()
        raise e

    time_series_inputs = tuple(arg for arg in node.signature.args if arg in node.signature.time_series_inputs)
    @graph
    def eval_node_graph():
        inputs = {}
        for ts_arg in time_series_inputs:
            if kwargs_[ts_arg] is None:
                continue
            if resolution_dict is not None and ts_arg in resolution_dict:
                ts_type = resolution_dict[ts_arg]
            else:
                ts_type: HgTypeMetaData = node.signature.input_types[ts_arg]
                if not ts_type.is_resolved:
                    # Attempt auto resolve
                    ts_type = HgTypeMetaData.parse(next(i for i in kwargs_[ts_arg] if i is not None))
                    if ts_type is None or not ts_type.is_resolved:
                        raise RuntimeError(
                            f"Unable to auto resolve type for '{ts_arg}', "
                            f"signature type is '{node.signature.input_types[ts_arg]}'")
                    ts_type = HgTSTypeMetaData(ts_type)
                    print(f"Auto resolved type for '{ts_arg}' to '{ts_type}'")
                ts_type = ts_type.py_type
            inputs[ts_arg] = replay(ts_arg, ts_type)
        for scalar_args in node.signature.scalar_inputs.keys():
            inputs[scalar_args] = kwargs_[scalar_args]

        out = node(**inputs)

        if node.signature.output_type is not None:
            # For now, not to worry about un_named bundle outputs
            record(out)

    GlobalState.reset()
    max_count = 0
    for ts_arg in time_series_inputs:
        v = kwargs_[ts_arg]
        if v is None:
            continue
        max_count = max(max_count, len(v))
        set_replay_values(ts_arg, SimpleArrayReplaySource(v))
    run_graph(eval_node_graph)

    results = get_recorded_value() if node.signature.output_type is not None else []
    if results:
        # For push nodes, there are no time-series inputs, so we compute size of the result from the result.
        max_count = max(max_count, int((results[-1][0] - MIN_DT) / MIN_TD))
    # Extract the results into a list of values without time-stamps, place a None when there is no recorded value.
    if results:
        out = []
        result_iter = iter(results)
        result = next(result_iter)
        for t in _time_iter(MIN_ST, MIN_ST + max_count*MIN_TD, MIN_TD):
            if result and t == result[0]:
                out.append(result[1])
                result = next(result_iter, None)
            else:
                out.append(None)
        return out


def _time_iter(start, end, delta):
    t = start
    while t < end:
        yield t
        t += delta
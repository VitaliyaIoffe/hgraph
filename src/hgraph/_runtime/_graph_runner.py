from datetime import datetime
from typing import Callable

from hgraph._runtime._constants import MIN_ST, MAX_ET
from hgraph._runtime._graph_executor import GraphEngineFactory
from hgraph._runtime._evaluation_engine import EvaluationMode

__all__ = ("run_graph",)


def run_graph(graph: Callable, *args, run_mode: EvaluationMode = EvaluationMode.SIMULATION, start_time: datetime = MIN_ST,
              end_time: datetime = MAX_ET, print_progress: bool=True, **kwargs):
    """
    Use this to initiate the graph engine run loop.

    The run_mode indicates how the graph engine should evaluate the graph, in RunMOde.REAL_TIME the graph will be
    evaluated using the system clock, in RunMode.BACK_TEST the graph will be evaluated using a simulated clock.
    The simulated clock is advanced as fast as possible without following the system clock timings. This allows a
    back-test to be evaluated as fast as possible.

    :param graph: The graph to evaluate
    :param args: Any arguments to pass to the graph
    :param run_mode: The mode to evaluate the graph in
    :param start_time: The time to start the graph
    :param end_time: The time to end the graph
    :param print_progress: If true, print the progress of the graph (will go away and be replaced with logging later)
    :param kwargs: Any additional kwargs to pass to the graph.
    """
    from hgraph._builder._graph_builder import GraphBuilder
    from hgraph._wiring._graph_builder import wire_graph
    if print_progress:
        print()
        print(f"Wiring Graph")
    if not isinstance(graph, GraphBuilder):
        graph_builder = wire_graph(graph, *args, **kwargs)
    else:
        graph_builder = graph
    if print_progress:
        print(f"Initialising Graph Engine")
    engine = GraphEngineFactory.make(graph=graph_builder.make_instance(tuple()), run_mode=run_mode)

    if print_progress:
        print(f"Running Graph from: {start_time} to {end_time}")

    engine.run(start_time, end_time)

    if print_progress:
        print(f"Graph Complete")

    if print_progress:
        print("Done")

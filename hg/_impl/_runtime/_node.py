import functools
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from inspect import signature
from typing import Optional, Mapping, TYPE_CHECKING, Callable, Any, Iterator

from sortedcontainers import SortedList

from hg import ExecutionContext, MIN_DT, MAX_DT
from hg._runtime import NodeSignature, Graph, NodeScheduler

if TYPE_CHECKING:
    from hg._types._ts_type import TimeSeriesInput, TimeSeriesOutput
    from hg._types._tsb_type import TimeSeriesBundleInput

__all__ = ("NodeImpl",)


@dataclass
class NodeImpl:  # Node
    """
    Provide a basic implementation of the Node as a reference implementation.
    """
    node_ndx: int
    owning_graph_id: tuple[int, ...]
    signature: NodeSignature
    scalars: Mapping[str, Any]
    graph: Graph = None
    eval_fn: Callable = None
    start_fn: Callable = None
    stop_fn: Callable = None
    input: Optional["TimeSeriesBundleInput"] = None
    output: Optional["TimeSeriesOutput"] = None
    is_started: bool = False
    _scheduler: Optional["NodeSchedulerImpl"] = None
    _kwargs: dict[str, Any] = None

    @functools.cached_property
    def node_id(self) -> tuple[int, ...]:
        """ Computed once and then cached """
        return self.owning_graph_id + tuple([self.node_ndx])

    @property
    def inputs(self) -> Optional[Mapping[str, "TimeSeriesInput"]]:
        return {k: self.input[k] for k in self.signature.time_series_inputs}

    @property
    def outputs(self) -> Optional[Mapping[str, "TimeSeriesOutput"]]:
        if len(self.signature.time_series_outputs) == 1:
            return {'out': self.output}
        else:
            return {k: self.output[k] for k in self.signature.time_series_outputs}

    @property
    def scheduler(self) -> "NodeScheduler":
        if self._scheduler is None:
            self._scheduler = NodeSchedulerImpl(self)
        return self._scheduler

    def initialise(self):
        pass

    def _initialise_kwargs(self):
        from hg._types._scalar_type_meta_data import Injector
        extras = {}
        for k, s in self.scalars.items():
            if isinstance(s, Injector):
                extras[k] = s(self)
        self._kwargs = {k: v for k, v in {**(self.input or {}), **self.scalars, **extras}.items() if
                        k in self.signature.args}

    def _initialise_inputs(self):
        if self.input:
            for k, ts in self.input.items():
                ts: TimeSeriesInput
                if self.signature.active_inputs is None or k in self.signature.active_inputs:
                    ts.make_active()

    def eval(self):
        scheduled = False if self._scheduler is None else self._scheduler.is_scheduled_now
        if self.input:
            # Perform validity check of inputs
            args = self.signature.valid_inputs if self.signature.valid_inputs is not None else self.signature.time_series_inputs.keys()
            if not all(self.input[k].valid for k in args):
                return  # We should look into caching the result of this check.
                # This check could perhaps be set on a separate call?
            if self._scheduler is not None:
                # It is possible we have scheduled and then remove the schedule,
                # so we need to check that something has caused this to be scheduled.
                if not scheduled and not any(self.input[k].valid for k in args):
                    return
        out = self.eval_fn(**self._kwargs)
        if out is not None:
            self.output.apply_result(out)
        if scheduled:
            self._scheduler.advance()

    def start(self):
        self._initialise_kwargs()
        self._initialise_inputs()
        if self.start_fn is not None:
            self.start_fn(**{k: self._kwargs[k] for k in (signature(self.start_fn).parameters.keys())})

    def stop(self):
        if self.stop_fn is not None:
            self.stop_fn(**{k: self._kwargs[k] for k in (signature(self.stop_fn).parameters.keys())})

    def dispose(self):
        self._kwargs = None  # For neatness purposes only, not required here.

    def notify(self):
        """Notify the graph that this node needs to be evaluated."""
        self.graph.schedule_node(self.node_ndx, self.graph.context.current_engine_time)


class NodeSchedulerImpl(NodeScheduler):

    def __init__(self, node: NodeImpl):
        self._node = node
        self._scheduled_events: SortedList[tuple[datetime, str]] = SortedList[tuple[datetime, str]]()
        self._tags: dict[str, datetime] = {}

    @property
    def next_scheduled_time(self) -> datetime:
        return self._scheduled_events[0][0] if self._scheduled_events else MIN_DT

    @property
    def is_scheduled(self) -> bool:
        return bool(self._scheduled_events)

    @property
    def is_scheduled_now(self) -> bool:
        return self._scheduled_events and self._scheduled_events[0][0] == self._node.graph.context.current_engine_time

    def schedule(self, when: datetime, tag: str = None):
        if tag is not None:
            if tag in self._tags:
                self._scheduled_events.remove((self._tags[tag], tag))
        if when > self._node.graph.context.current_engine_time:
            self._tags[tag] = when
            current_first = self._scheduled_events[0][0] if self._scheduled_events else MAX_DT
            self._scheduled_events.add((when, "" if tag is None else tag))
            if current_first > (next := self.next_scheduled_time):
                self._node.graph.schedule_node(self._node.node_ndx, next)

    def un_schedule(self, tag: str = None):
        if tag is not None:
            if tag in self._tags:
                self._scheduled_events.remove((self._tags[tag], tag))
                del self._tags[tag]
        elif self._scheduled_events:
            self._scheduled_events.pop(0)

    def reset(self):
        self._scheduled_events.clear()
        self._tags.clear()

    def advance(self):
        until = self._node.graph.context.current_engine_time
        while self._scheduled_events and self._scheduled_events[0][0] <= until:
            self._scheduled_events.pop(0)
        if self._scheduled_events:
            self._node.graph.schedule_node(self._node.node_ndx, self._scheduled_events[0][0])


class GeneratorNodeImpl(NodeImpl):  # Node
    generator: Iterator = None
    next_value: object = None

    def start(self):
        self._initialise_kwargs()
        self.generator = self.eval_fn(**self._kwargs)
        self.graph.schedule_node(self.node_ndx, self.graph.context.current_engine_time)

    def eval(self):
        time, out = next(self.generator, (None, None))
        if out is not None and time is not None and time <= self.graph.context.current_engine_time:
            self.output.apply_result(out)
            self.next_value = None
            self.eval()  # We are going to apply now! Prepare next step,
            return
            # This should ultimately either produce no result or a result that is to be scheduled

        if self.next_value is not None:
            self.output.apply_result(self.next_value)
            self.next_value = None

        if time is not None and out is not None:
            self.next_value = out
            self.graph.schedule_node(self.node_ndx, time)


@dataclass
class PythonPushQueueNodeImpl(NodeImpl):  # Node

    receiver: "_SenderReceiverState" = None

    def start(self):
        self._initialise_kwargs()
        self.receiver = _SenderReceiverState(lock=threading.RLock(), queue=deque(), context=self.graph.context)
        self.eval_fn(self.receiver, **self._kwargs)

    def eval(self):
        value = self.receiver.dequeue()
        if value is None:
            return
        self.graph.context.mark_push_has_pending_values()
        self.output.apply_result(value)

    def stop(self):
        self.receiver.stopped = True
        self.receiver = None


@dataclass
class _SenderReceiverState:
    lock: threading.RLock
    queue: deque
    context: ExecutionContext
    stopped: bool = False

    def __call__(self, value):
        self.enqueue(value)

    def enqueue(self, value):
        with self.lock:
            if self.stopped:
                raise RuntimeError("Cannot enqueue into a stopped receiver")
            self.queue.append(value)
            self.context.mark_push_has_pending_values()

    def dequeue(self):
        with self.lock:
            return self.queue.popleft() if self.queue else None

    def __bool__(self):
        with self.lock:
            return bool(self.queue)

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

from typing import cast, Type

from hgraph import TIME_SERIES_TYPE, compute_node, REF, TS, TSL, Size, SIZE, graph, TSS, SCALAR, TSD, REMOVE
from hgraph._impl._types._ref import PythonTimeSeriesReference
from hgraph._impl._types._tss import Removed
from hgraph.test import eval_node


@compute_node
def create_ref(ts: REF[TIME_SERIES_TYPE]) -> REF[TIME_SERIES_TYPE]:
    return ts.value


def test_ref():
    assert eval_node(create_ref[TIME_SERIES_TYPE: TS[int]], ts=[1, 2]) == [1, 2]


@compute_node
def route_ref(condition: TS[bool], ts: REF[TIME_SERIES_TYPE]) -> TSL[REF[TIME_SERIES_TYPE], Size[2]]:
    return cast(TSL, (ts.value, PythonTimeSeriesReference()) if condition.value else (PythonTimeSeriesReference(), ts.value))


def test_route_ref():
    assert eval_node(route_ref[TIME_SERIES_TYPE: TS[int]], condition=[True, None, False, None], ts=[1, 2, None, 4]) == [
        {0: 1}, {0: 2}, {1: 2}, {1: 4}]


@compute_node
def merge_ref(index: TS[int], ts: TSL[REF[TIME_SERIES_TYPE], SIZE]) -> REF[TIME_SERIES_TYPE]:
    return cast(REF, ts[index.value].value)


def test_merge_ref():
    assert eval_node(merge_ref[TIME_SERIES_TYPE: TS[int], SIZE: Size[2]], index=[0, None, 1, None], ts=[(1, -1), (2, -2), None, (4, -4)]) == [1, 2, -2, -4]


@graph
def merge_ref_non_peer(index: TS[int], ts1: TIME_SERIES_TYPE, ts2: TIME_SERIES_TYPE) -> REF[TIME_SERIES_TYPE]:
    return merge_ref(index, TSL.from_ts(ts1, ts2))  # TODO: This TSL building syntax is quite a mouthful, TSL(ts1, ts2) would be preferrable, ideally wiring should accept just (ts1, ts2) here


def test_merge_ref_non_peer():
    assert eval_node(merge_ref_non_peer[TIME_SERIES_TYPE: TS[int]],
                     index=[0, None, 1, None],
                     ts1=[1, 2, None, 4],
                     ts2=[-1, -2, None, -4]
                     ) == [1, 2, -2, -4]


def test_merge_ref_non_peer_complex_inner_ts():
    assert eval_node(merge_ref_non_peer[TIME_SERIES_TYPE: TSL[TS[int], Size[2]]],
                     index=[0, None, 1, None],
                     ts1=[(1, 1), (2, None), None, (None, 4)],
                     ts2=[(-1, -1), (-2, -2), None, (-4, None)]
                     ) == [{0: 1, 1: 1}, {0: 2}, {0: -2, 1: -2}, {0: -4}]


@graph
def merge_ref_non_peer_inner(index: TS[int], ts1: TIME_SERIES_TYPE, ts2: TIME_SERIES_TYPE, ts3: TIME_SERIES_TYPE, ts4: TIME_SERIES_TYPE) -> REF[TSL[TIME_SERIES_TYPE, Size[2]]]:
    return merge_ref(index, TSL.from_ts(TSL.from_ts(ts1, ts2), TSL.from_ts(ts3, ts4)))

def test_merge_ref_inner_non_peer_ts():
    assert eval_node(merge_ref_non_peer_inner[TIME_SERIES_TYPE: TS[int]],
                     index=[0, None, 1, None],
                     ts1=[1, 2, None, None],
                     ts2=[1, None, None, 4],
                     ts3=[-1, -2, None, -4],
                     ts4=[-1, -2, None, None]
                     ) == [{0: 1, 1: 1}, {0: 2}, {0: -2, 1: -2}, {0: -4}]


def test_merge_ref_set():
    assert eval_node(merge_ref_non_peer[TIME_SERIES_TYPE: TSS[int]],
                     index=[0, None, 1, None],
                     ts1=[{1, 2}, None, None, {4}],
                     ts2=[{-1}, {-2}, {-3, Removed(-1)}, {-4}]
                     ) == [{1, 2}, None, {-2, -3, Removed(1), Removed(2)}, {-4}]


@compute_node
def ref_contains(tss: REF[TSS[SCALAR]], item: TS[SCALAR]) -> REF[TS[bool]]:
    return PythonTimeSeriesReference(tss.value.output.ts_contains(item.value))


def test_tss_ref_contains():
    assert eval_node(ref_contains[SCALAR: int],
                     tss=[{1}, {2}, None, {Removed(2)}],
                     item=[2, None, None, None, 1]
                     ) == [False, True, None, False, True]


def test_merge_with_tsd():
    assert eval_node(merge_ref_non_peer[TIME_SERIES_TYPE: TSD[int, TS[int]]],
                     index=[0, None, 1, None],
                     ts1=[{1: 1, 2: 2}, None, None, {4: 4}],
                     ts2=[{-1: -1}, {-2: -2}, {-3: -3, -1: REMOVE}, {-4: -4}]
                     ) == [{1: 1, 2: 2}, None, {-2: -2, -3: -3, 1: REMOVE, 2: REMOVE}, {-4: -4}]


@compute_node
def merge_tsd(tsd1: TSD[SCALAR, REF[TIME_SERIES_TYPE]], tsd2: TSD[SCALAR, REF[TIME_SERIES_TYPE]]) \
        -> TSD[SCALAR, REF[TIME_SERIES_TYPE]]:
    tick = {}
    tick.update({k: v.value for k, v in tsd1.modified_items()})
    tick.update({k: v.value for k, v in tsd2.modified_items() if k not in tsd1})
    tick.update({k: tsd2[k].value if k in tsd2 else REMOVE for k in tsd1.removed_keys()})
    tick.update({k: REMOVE for k in tsd2.removed_keys() if k not in tsd1})
    return tick


def test_merge_tsd():
    assert eval_node(merge_tsd[SCALAR: int, TIME_SERIES_TYPE: TS[int]],
                     tsd1=[{1: 1}, {2: 2}, {3: 3}, {1: REMOVE}, {1: 11}],
                     tsd2=[{1: -1}, {-2: -2}, {1: -1, 3: -3}, None, {-2: REMOVE, 3: REMOVE}]
                     ) == [{1: 1}, {2: 2, -2: -2}, {3: 3}, {1: -1}, {-2: REMOVE, 1: 11}]

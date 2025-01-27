from hgraph import graph, TS, TSS, compute_node, PythonSetDelta
from hgraph.nodes import pass_through
from hgraph.test import eval_node


@compute_node
def create_tss(key: TS[str], add: TS[bool]) -> TSS[str]:
    if add.value:
        return PythonSetDelta(frozenset([key.value]), frozenset())
    else:
        return PythonSetDelta(frozenset(), frozenset([key.value]))


def test_tss_strait():

    assert eval_node(create_tss, key=["a", "b", "a"], add=[True, True, False]) == [
        PythonSetDelta(frozenset("a"), frozenset()),
        PythonSetDelta(frozenset("b"), frozenset()),
        PythonSetDelta(frozenset(), frozenset("a"))]


def test_tss_pass_through():

        @graph
        def pass_through_test(key: TS[str], add: TS[bool]) -> TSS[str]:
            tss = create_tss(key, add)
            return pass_through(tss)

        assert eval_node(pass_through_test, key=["a", "b", "a"], add=[True, True, False]) == [
            PythonSetDelta(frozenset("a"), frozenset()),
            PythonSetDelta(frozenset("b"), frozenset()),
            PythonSetDelta(frozenset(), frozenset("a"))]
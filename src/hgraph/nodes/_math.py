from typing import TypeVar

from hgraph import compute_node, TS

__all__ = ("NUMBER", "add_", "sub_", "mult_", "div_")


NUMBER = TypeVar("NUMBER", int, float)


@compute_node
def add_(lhs: TS[NUMBER], rhs: TS[NUMBER]) -> TS[NUMBER]:
    """ Adds two time-series values of numbers together"""
    return lhs.value + rhs.value


@compute_node
def sub_(lhs: TS[NUMBER], rhs: TS[NUMBER]) -> TS[NUMBER]:
    """ Subtracts two time-series values of numbers together"""
    return lhs.value - rhs.value


@compute_node
def mult_(lhs: TS[NUMBER], rhs: TS[NUMBER]) -> TS[NUMBER]:
    """ Multiplies two time-series values of numbers together"""
    return lhs.value * rhs.value


@compute_node
def div_(lhs: TS[NUMBER], rhs: TS[NUMBER]) -> TS[float]:
    """ Divides two time-series values of numbers together"""
    # TODO: Provide options for improved handling of different scenarios,
    # e.g. divide by zero can be handled in different ways.
    # Add support for integer division
    return lhs.value / rhs.value

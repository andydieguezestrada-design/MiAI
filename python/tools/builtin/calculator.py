from __future__ import annotations

import ast
import operator as op
from typing import Any

from python.tools.base import ToolSpec


_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_UNARYOPS = {ast.UAdd: op.pos, ast.USub: op.neg}


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval(node.left)
        right = _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponente demasiado grande.")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval(node.operand))
    raise ValueError("Expresión no permitida. Solo números y operaciones aritméticas.")


def calculate(expression: str) -> float | int:
    if not expression or len(expression) > 200:
        raise ValueError("Expresión vacía o demasiado larga.")
    tree = ast.parse(expression, mode="eval")
    return _eval(tree.body)


calculator_tool = ToolSpec(
    name="calculator",
    description="Calcula expresiones aritméticas simples de forma segura.",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
    function=calculate,
)

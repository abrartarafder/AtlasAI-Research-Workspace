"""Small, auditable tools available to the research agent."""

import ast
import json
import math
import operator
from urllib.parse import urlparse

from langchain_core.tools import tool


def safe_url(value: str) -> bool:
    """Only allow ordinary web links in research results."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username
    except (TypeError, ValueError):
        return False


def search_web(query: str, max_results: int = 5) -> dict:
    """Search without requiring an additional search API key."""
    from ddgs import DDGS

    query = query.strip()
    if not query or len(query) > 500:
        return {"error": "Use a search query between 1 and 500 characters.", "results": []}
    try:
        results = DDGS(timeout=15).text(query, max_results=max_results)
        cleaned = []
        seen = set()
        for item in results:
            url = item.get("href") or item.get("link") or ""
            if safe_url(url) and url not in seen:
                seen.add(url)
                cleaned.append({"title": str(item.get("title", url))[:300], "url": url,
                                "snippet": str(item.get("body", item.get("snippet", "")))[:1600]})
        return {"query": query, "results": cleaned,
                "error": None if cleaned else "No results found. Try a more specific query."}
    except Exception:
        return {"query": query, "results": [],
                "error": "Web search is temporarily unavailable. Try another query or retry later."}


@tool
def search_tool(query: str) -> str:
    """Search the web for current information. Returns titles, snippets and source URLs."""
    return json.dumps(search_web(query), ensure_ascii=False)


_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
              ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCTIONS = {"sqrt": math.sqrt, "log": math.log, "log10": math.log10,
              "abs": abs, "round": round, "min": min, "max": max}


def calculate(expression: str) -> int | float:
    """Evaluate bounded arithmetic through an AST; never execute Python code."""
    if not expression.strip() or len(expression) > 512:
        raise ValueError("Use an expression between 1 and 512 characters.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid arithmetic expression.") from exc
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError("Expression is too complex.")

    def bounded(value):
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError("Result must be a finite number with magnitude at most 1e100.")
        return value

    def evaluate(node):
        if isinstance(node, ast.Constant):
            return bounded(node.value)
        if isinstance(node, ast.Name) and node.id in {"pi", "e"}:
            return getattr(math, node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return bounded((1 if isinstance(node.op, ast.UAdd) else -1) * evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent must be between -1000 and 1000.")
            return bounded(_OPERATORS[type(node.op)](left, right))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCTIONS and not node.keywords and 1 <= len(node.args) <= 8):
            return bounded(_FUNCTIONS[node.func.id](*(evaluate(arg) for arg in node.args)))
        raise ValueError("Use arithmetic, pi, e, sqrt, log, log10, abs, round, min or max.")

    try:
        return evaluate(tree.body)
    except (ArithmeticError, TypeError) as exc:
        raise ValueError("Calculation failed. Check the numbers and function arguments.") from exc


@tool
def calculator_tool(expression: str) -> str:
    """Calculate arithmetic accurately. Use ** for powers and 0.15 for 15 percent."""
    try:
        return json.dumps({"expression": expression, "result": calculate(expression)})
    except ValueError as exc:
        return json.dumps({"expression": expression, "error": str(exc)})

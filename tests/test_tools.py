from python.tools.defaults import create_default_tool_executor, create_default_tool_registry


def test_builtin_tools_are_registered():
    registry = create_default_tool_registry()
    assert {"calculator", "datetime", "system_info"}.issubset(set(registry.list()))


def test_calculator_executes_safely():
    executor = create_default_tool_executor()
    result = executor.execute("calculator", {"expression": "125 * 48"})
    assert result.ok is True
    assert result.result == 6000


def test_calculator_rejects_python_code():
    executor = create_default_tool_executor()
    result = executor.execute("calculator", {"expression": "__import__('os').getcwd()"})
    assert result.ok is False


def test_unknown_tool_is_reported():
    executor = create_default_tool_executor()
    result = executor.execute("does_not_exist", {})
    assert result.ok is False

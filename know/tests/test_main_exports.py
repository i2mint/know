"""Tests for main package exports from know/__init__.py"""

import pytest


def test_main_imports():
    """Test that main exports can be imported from the package root"""
    from know import ContextFanout, any_value_is_none, ContextualFunc

    # Verify they're all callable or usable
    assert callable(ContextFanout)
    assert callable(any_value_is_none)
    assert callable(ContextualFunc)


def test_any_value_is_none():
    """Test any_value_is_none function behavior"""
    from know import any_value_is_none

    # Test with no None values
    assert any_value_is_none({'a': 1, 'b': 2, 'c': 3}) is False

    # Test with None value
    assert any_value_is_none({'a': 1, 'b': None, 'c': 3}) is True

    # Test with empty dict
    assert any_value_is_none({}) is False

    # Test with all None values
    assert any_value_is_none({'a': None, 'b': None}) is True


def test_contextual_func_basic():
    """Test ContextualFunc basic functionality"""
    from know import ContextualFunc
    from contextlib import contextmanager

    # Track context state
    context_states = []

    @contextmanager
    def test_context():
        context_states.append('entered')
        yield
        context_states.append('exited')

    # Create a simple function
    def add_one(x):
        return x + 1

    # Wrap it with context
    contextual_add = ContextualFunc(add_one, test_context())

    # Test that function works
    assert contextual_add(5) == 6

    # Test that context manager works
    with contextual_add:
        assert contextual_add(10) == 11

    # Verify context was entered and exited
    assert context_states == ['entered', 'exited']

"""Shared pytest configuration.

Registers nicegui's user fixture for viewer smoke tests. The plugin is
inert for tests that don't request the ``user`` fixture.
"""

pytest_plugins = ["nicegui.testing.user_plugin"]

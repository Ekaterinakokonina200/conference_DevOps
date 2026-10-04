"""Общие настройки pytest для всех тестов проекта."""

import pytest


def pytest_sessionfinish(session, exitstatus):
    """Запрет пропуска тестов: skipped/xfailed/xpassed делают прогон неуспешным."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    banned = {
        kind: len(reporter.stats.get(kind, []))
        for kind in ("skipped", "xfailed", "xpassed")
    }
    if any(banned.values()):
        reporter.write_line(
            f"Запрещено пропускать тесты (docs/quality-rules.md): {banned}",
            red=True,
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED

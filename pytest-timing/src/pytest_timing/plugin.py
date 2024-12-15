from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

DEFAULT_OUTPUT_PATH = "test_timing.csv"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("timing")
    group.addoption(
        "--timing-file",
        action="store",
        dest="timing_file",
        default=DEFAULT_OUTPUT_PATH,
        help="Specify a path to the pytest timing output file",
    )


def pytest_configure(config: pytest.Config) -> None:
    plugin = TimingPlugin()
    plugin.configure(str(config.getoption("timing_file")))
    config.pluginmanager.register(plugin, "timing_plugin")


class TimingPlugin:
    """Plugin to track and record test execution times."""

    def __init__(self) -> None:
        self._test_start_times: dict[str, datetime] = {}
        self._test_results: dict[str, str] = {}
        self.timing_file_path: Path | None = None

    def configure(self, timing_file_path: str) -> None:
        """Configure the plugin with the output file path"""
        self.timing_file_path = Path(timing_file_path)

        if not self.timing_file_path.exists():
            self.timing_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.timing_file_path.touch(exist_ok=True)
            with self.timing_file_path.open("w") as f:
                f.write("test_name,start_time,end_time,duration_seconds,result\n")
        else:
            with self.timing_file_path.open("a") as f:
                f.write("------------------ -------------------------------------\n")

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_protocol(self, item: pytest.Item) -> None:
        """Record start time before each test"""
        self._test_start_times[item.nodeid] = datetime.now()
        return None

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo[Any]) -> None:
        """Store test result when it completes"""
        if call.when == "call":  # Store result only for test execution phase
            if call.excinfo is None:
                self._test_results[item.nodeid] = "P"  # Passed
            elif call.excinfo.typename == "AssertionError":
                self._test_results[item.nodeid] = "Fa"  # Failed assert
            else:
                self._test_results[item.nodeid] = "Fx"  # Error/exception
        elif call.when == "setup" and call.excinfo is not None:
            self._test_results[item.nodeid] = "Fe"  # Error during setup
        elif call.when == "setup" and item.get_closest_marker("skip"):
            self._test_results[item.nodeid] = "S"  # Skipped

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_teardown(self, item: pytest.Item) -> None:
        """Record end time and result after each test"""
        if not self.timing_file_path:
            return

        end_time = datetime.now()
        start_time = self._test_start_times.pop(item.nodeid)
        result = self._test_results.pop(item.nodeid, "E")  # Default to E if no result found
        duration = end_time - start_time

        with open(self.timing_file_path, "a") as f:
            f.write(
                f"{item.nodeid},{start_time.strftime('%Y-%m-%d %H:%M:%S.%f')},"
                f"{end_time.strftime('%Y-%m-%d %H:%M:%S.%f')},{duration.total_seconds():.3f},{result}\n"
            )

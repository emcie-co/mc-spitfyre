from datetime import datetime
import os
import pytest

# Global dictionary to store test start times and results
_test_start_times: dict[str, datetime] = {}
_test_results: dict[str, str] = {}

PYTEST_TIMING_OUTPUT_PATH = "test_timing.csv"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("timing")
    group.addoption(
        "--timing-file",
        action="store",
        dest="timing_file",
        default=PYTEST_TIMING_OUTPUT_PATH,
        help="Specify a path to the pytest timing output file",
    )


timing_file_path: str = PYTEST_TIMING_OUTPUT_PATH


def pytest_configure(config: pytest.Config) -> None:
    """Create file with header if it doesn't exist, otherwise do nothing"""
    timing_file_path = config.getoption("timing_file")
    if not os.path.exists(config.getoption("timing_file")):
        with open(timing_file_path, "w") as f:
            f.write("test_name,start_time,end_time,duration_seconds,result\n")
    else:
        with open(timing_file_path, "a") as f:
            f.write("------------------ -------------------------------------\n")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item) -> None:
    """Record start time before each test"""
    _test_start_times[item.nodeid] = datetime.now()
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Store test result when it completes"""
    if call.when == "call":  # Store result only for test execution phase
        if call.excinfo is None:
            _test_results[item.nodeid] = "P"  # Passed
        elif call.excinfo.typename == "AssertionError":
            _test_results[item.nodeid] = "Fa"  # Failed assert
        else:
            _test_results[item.nodeid] = "Fx"  # Error/exception
    elif call.when == "setup" and call.excinfo is not None:
        _test_results[item.nodeid] = "Fe"  # Error during setup
    elif call.when == "setup" and item.get_closest_marker("skip"):
        _test_results[item.nodeid] = "S"  # Skipped


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Record end time and result after each test"""
    end_time = datetime.now()
    start_time = _test_start_times.pop(item.nodeid)
    result = _test_results.pop(item.nodeid, "E")  # Default to E if no result found
    duration = end_time - start_time

    with open(timing_file_path, "a") as f:
        f.write(
            f"{item.nodeid},{start_time.strftime('%Y-%m-%d %H:%M:%S.%f')},"
            f"{end_time.strftime('%Y-%m-%d %H:%M:%S.%f')},{duration.total_seconds():.3f},{result}\n"
        )

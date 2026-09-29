"""Load the HA-independent API/model without importing the HA entrypoint."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "tokyu_bus"
PACKAGE_NAME = "tokyu_bus_unit_test"


def load_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(COMPONENT)]
        sys.modules[PACKAGE_NAME] = package
    qualified = f"{PACKAGE_NAME}.{name}"
    spec = importlib.util.spec_from_file_location(qualified, COMPONENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def api_module():
    return load_module("api")

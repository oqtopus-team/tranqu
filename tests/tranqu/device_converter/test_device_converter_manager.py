from typing import Any

import pytest

from tranqu.device_converter import (
    DeviceConverter,
    DeviceConverterAlreadyRegisteredError,
    DeviceConverterManager,
    DeviceConverterNotFoundError,
    PassThroughDeviceConverter,
)


class DummyDeviceConverter(DeviceConverter):
    def convert(self, device: Any) -> Any:
        return device


class TestDeviceConverterManager:
    def setup_method(self):
        self.manager = DeviceConverterManager()

    def test_register_converter(self):
        converter = DummyDeviceConverter()
        self.manager.register_converter("lib1", "lib2", converter)

        assert self.manager.has_converter("lib1", "lib2")

    def test_register_converter_raises_error_when_already_registered(self):
        converter = DummyDeviceConverter()
        self.manager.register_converter("lib1", "lib2", converter)

        with pytest.raises(
            DeviceConverterAlreadyRegisteredError,
            match=r"Converter already registered for conversion from lib1 to lib2\.",
        ):
            self.manager.register_converter("lib1", "lib2", converter)

    def test_register_converter_with_allow_override(self):
        converter1 = DummyDeviceConverter()
        converter2 = DummyDeviceConverter()

        self.manager.register_converter("lib1", "lib2", converter1)
        self.manager.register_converter("lib1", "lib2", converter2, allow_override=True)

        assert self.manager.fetch_converter("lib1", "lib2") == converter2

    def test_has_converter_returns_true_for_same_lib(self):
        assert self.manager.has_converter("lib1", "lib1")

    def test_has_converter_returns_false_for_unregistered_converter(self):
        assert not self.manager.has_converter("lib1", "lib2")

    def test_fetch_converter_returns_pass_through_for_same_lib(self):
        converter = self.manager.fetch_converter("lib1", "lib1")
        assert isinstance(converter, PassThroughDeviceConverter)

    def test_fetch_converter_raises_error_when_not_found(self):
        with pytest.raises(
            DeviceConverterNotFoundError,
            match=r"Converter not found for conversion from lib1 to lib2\.",
        ):
            self.manager.fetch_converter("lib1", "lib2")

import pytest

from tranqu.device_type_manager import (
    DeviceLibraryAlreadyRegisteredError,
    DeviceTypeManager,
)


class DummyDevice:
    """Dummy device class for testing"""


@pytest.fixture
def device_manager() -> DeviceTypeManager:
    return DeviceTypeManager()


class TestDeviceTypeManager:
    def test_register_type(self, device_manager: DeviceTypeManager) -> None:
        device_manager.register_type("dummy", DummyDevice)
        device = DummyDevice()

        result = device_manager.resolve_lib(device)

        assert result == "dummy"

    def test_resolve_lib_returns_none_for_unregistered_type(
        self, device_manager: DeviceTypeManager
    ) -> None:
        device = DummyDevice()

        result = device_manager.resolve_lib(device)

        assert result is None

    def test_resolve_lib_with_multiple_registrations(
        self, device_manager: DeviceTypeManager
    ) -> None:
        class AnotherDummyDevice:
            pass

        device_manager.register_type("dummy1", DummyDevice)
        device_manager.register_type("dummy2", AnotherDummyDevice)

        device1 = DummyDevice()
        device2 = AnotherDummyDevice()

        assert device_manager.resolve_lib(device1) == "dummy1"
        assert device_manager.resolve_lib(device2) == "dummy2"

    def test_register_type_multiple_times(
        self, device_manager: DeviceTypeManager
    ) -> None:
        device_manager.register_type("dummy", DummyDevice)
        device_manager.register_type("another_dummy", DummyDevice)

        device = DummyDevice()

        assert device_manager.resolve_lib(device) == "another_dummy"

    def test_register_type_raises_error_when_library_already_registered(
        self, device_manager: DeviceTypeManager
    ) -> None:
        device_manager.register_type("dummy", DummyDevice)

        with pytest.raises(
            DeviceLibraryAlreadyRegisteredError,
            match=(
                r"Library 'dummy' is already registered\. "
                r"Use allow_override=True to force registration\."
            ),
        ):
            device_manager.register_type("dummy", DummyDevice)

    def test_register_type_with_allow_override(
        self, device_manager: DeviceTypeManager
    ) -> None:
        device_manager.register_type("dummy", DummyDevice)

        device_manager.register_type("dummy", DummyDevice, allow_override=True)

        device = DummyDevice()
        assert device_manager.resolve_lib(device) == "dummy"

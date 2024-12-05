from typing import Any

from .tranqu_error import TranquError


class DeviceLibNotFoundError(TranquError):
    """Error raised when device library cannot be detected."""


class DeviceTypeManager:
    """Class that manages mapping between device types and library identifiers."""

    def __init__(self) -> None:
        self._type_registry: dict[type, str] = {}

    def register_type(self, device_lib: str, device_type: type) -> None:
        """Register a device type and its library identifier.

        Args:
            device_lib (str): Library identifier (e.g., "qiskit", "oqtopus")
            device_type (Type): Device type class to register

        """
        self._type_registry[device_type] = device_lib

    def detect_lib(self, device: Any) -> str:  # noqa: ANN401
        """Detect library based on device type.

        Args:
            device (Any): Device to inspect

        Returns:
            str: Detected library identifier

        Raises:
            DeviceLibNotFoundError: When device type is not registered

        """
        for device_type, lib in self._type_registry.items():
            if isinstance(device, device_type):
                return lib

        msg = (
            "Could not detect device library. Please specify device_lib or "
            "use register_device_type() to register the device type."
        )
        raise DeviceLibNotFoundError(msg)

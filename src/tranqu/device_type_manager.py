from typing import Any

from .tranqu_error import TranquError


class DeviceLibraryAlreadyRegisteredError(TranquError):
    """Raised when attempting to register a device library that already exists."""


class DeviceTypeManager:
    """Class that manages mapping between device types and library identifiers."""

    def __init__(self) -> None:
        self._type_registry: dict[type[Any], str] = {}

    def register_type(
        self, device_lib: str, device_type: type[Any], *, allow_override: bool = False
    ) -> None:
        """Register a device type and its library identifier.

        Args:
            device_lib (str): Library identifier (e.g., "qiskit", "oqtopus")
            device_type (Type): Device type class to register
            allow_override (bool): When False, prevents overwriting existing
              registrations. Defaults to False.

        Raises:
            DeviceLibraryAlreadyRegisteredError: If the library is already registered
                and allow_override is False.

        """
        if not allow_override and device_lib in self._type_registry.values():
            msg = (
                f"Library '{device_lib}' is already registered. "
                "Use allow_override=True to force registration."
            )
            raise DeviceLibraryAlreadyRegisteredError(msg)

        self._type_registry[device_type] = device_lib

    def resolve_lib(self, device: Any) -> str | None:  # noqa: ANN401
        """Resolve library based on device type.

        Args:
            device (Any): Device to inspect

        Returns:
            str | None: Library identifier for registered device type, None otherwise

        """
        for device_type, lib in self._type_registry.items():
            if isinstance(device, device_type):
                return lib

        return None

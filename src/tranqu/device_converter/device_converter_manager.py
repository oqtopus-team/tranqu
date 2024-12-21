from tranqu.tranqu_error import TranquError

from .device_converter import DeviceConverter
from .pass_through_device_converter import PassThroughDeviceConverter


class DeviceConverterError(TranquError):
    """Base exception for device converter-related errors."""


class DeviceConverterAlreadyRegisteredError(DeviceConverterError):
    """Raised when attempting to register a device converter that already exists."""


class DeviceConverterNotFoundError(DeviceConverterError):
    """Raised when the requested converter is not found."""


class DeviceConverterManager:
    """Manages conversions between devices.

    Provides methods to register, retrieve, and check converters between devices.
    Converters are used to perform conversions from a specific source device
    to a target device.
    """

    def __init__(self) -> None:
        self._converters: dict[tuple[str, str], DeviceConverter] = {}

    def has_converter(self, from_lib: str, to_lib: str) -> bool:
        """Check if a converter exists between the specified devices.

        Args:
            from_lib (str): The name of the source device
            to_lib (str): The name of the target device

        Returns:
            bool: True if a converter exists, False otherwise

        """
        # pass through
        if from_lib == to_lib:
            return True

        return (from_lib, to_lib) in self._converters

    def fetch_converter(self, from_lib: str, to_lib: str) -> DeviceConverter:
        """Retrieve a converter from the specified device to another device.

        Args:
            from_lib (str): The name of the source device
            to_lib (str): The name of the target device

        Returns:
            DeviceConverter: An instance of the converter corresponding to
                the specified source and target devices.
                If the source and target are the same,
                it returns an instance of PassThroughDeviceConverter.

        Raises:
            DeviceConverterNotFoundError:
                Raised when the requested converter is not found.

        """
        if from_lib == to_lib:
            return PassThroughDeviceConverter()

        converter = self._converters.get((from_lib, to_lib))

        if converter is None:
            msg = f"Converter not found for conversion from {from_lib} to {to_lib}."
            raise DeviceConverterNotFoundError(msg)

        return converter

    def register_converter(
        self,
        from_lib: str,
        to_lib: str,
        converter: DeviceConverter,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a converter between the specified devices.

        Args:
            from_lib (str): The name of the source device
            to_lib (str): The name of the target device
            converter (DeviceConverter): The converter instance to register
            allow_override (bool): When False, prevents overwriting existing
              registrations. Defaults to False.

        Raises:
            DeviceConverterAlreadyRegisteredError:
                Raises if trying to re-register an already registered converter
                and allow_override is False.

        """
        key = (from_lib, to_lib)
        if not allow_override and key in self._converters:
            msg = (
                f"Converter already registered for conversion from {from_lib} "
                f"to {to_lib}."
            )
            raise DeviceConverterAlreadyRegisteredError(msg)

        self._converters[key] = converter

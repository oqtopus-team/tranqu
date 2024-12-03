from typing import Any

from .device_converter import DeviceConverter


class PassThroughDeviceConverter(DeviceConverter):
    """A converter that returns the input device as is.

    It is used internally in Tranqu as a placeholder
    when a converter is not needed during transpilation.
    """

    def convert(self, device: Any) -> Any:  # noqa: ANN401 PLR6301
        """Return the input device as is.

        Args:
            device (Any): The device to be converted.

        Returns:
            Any: The device returned without any conversion.

        """
        return device

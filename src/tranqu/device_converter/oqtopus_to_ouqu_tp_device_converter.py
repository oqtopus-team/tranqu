import json
from typing import Any

from .device_converter import DeviceConverter


class OqtopusToOuquTpDeviceConverter(DeviceConverter):
    """Device converter for converting from Oqtopus to ouqu-tp format."""

    @staticmethod
    def convert(device: dict[str, Any]) -> str:
        """Convert a Oqtopus device to ouqu-tp format.

        Args:
            device (dict[str, Any]): The Oqtopus device to be converted.

        Returns:
            str: The converted ouqu-tp format device.

        """
        return json.dumps(device)

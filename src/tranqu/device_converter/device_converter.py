from abc import ABC, abstractmethod
from typing import Any


class DeviceConverter(ABC):
    """Abstract base class for converting devices to different formats.

    Provides abstract methods to be implemented by subclasses for
    specific conversion logic.
    The actual implementation of the conversion will be done in each subclass.
    """

    @abstractmethod
    def convert(self, device: Any) -> Any:  # noqa: ANN401
        """Convert a given device to a different format or representation.

        Subclasses should implement this method to define specific conversion logic.

        Args:
            device (Any): The device to be converted, which can be of any type.

        Returns:
            Any: The converted device in the desired format or representation.

        """

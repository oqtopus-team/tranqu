from abc import ABC, abstractmethod
from typing import Any


class ProgramConverter(ABC):
    """Abstract base class for converting programs to different formats.

    Provides abstract methods to be implemented by subclasses for
    specific conversion logic.
    The actual implementation of the conversion will be done in each subclass.
    """

    @abstractmethod
    def convert(self, program: Any) -> Any:  # noqa: ANN401
        """Convert a given program to a different format or representation.

        Subclasses should implement this method to
        define specific conversion logic.

        Args:
            program (Any): The program to be converted, which can be of any type.

        Returns:
            Any: The converted program in the desired format or representation.

        """

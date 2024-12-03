from tranqu.tranqu_error import TranquError

from .pass_through_program_converter import PassThroughProgramConverter
from .program_converter import ProgramConverter


class ProgramConverterError(TranquError):
    """Base exception for program converter-related errors."""


class ProgramConverterAlreadyRegisteredError(ProgramConverterError):
    """Raised when attempting to re-register an already registered converter."""


class ProgramConverterNotFoundError(ProgramConverterError):
    """Raised when the requested converter is not found."""


class ProgramConverterManager:
    """Manage ProgramConverters for converting between different programs.

    Provides functionality to register, retrieve, and check converters.
    Converters are objects that perform conversions from a specific source
    program to a target program.
    """

    def __init__(self) -> None:
        self._converters: dict[tuple[str, str], ProgramConverter] = {}

    def has_converter(self, from_lib: str, to_lib: str) -> bool:
        """Check if a converter exists between the specified devices.

        Args:
            from_lib (str): The name of the source device (string)
            to_lib (str): The name of the target device (string)

        Returns:
            bool: True if a converter exists, False otherwise

        """
        # pass through
        if from_lib == to_lib:
            return True

        return (from_lib, to_lib) in self._converters

    def fetch_converter(self, from_lib: str, to_lib: str) -> ProgramConverter:
        """Retrieve a converter from the specified program to another program.

        Args:
            from_lib (str): The name of the source program.
            to_lib (str): The name of the target program.

        Returns:
            ProgramConverter: An instance of the converter corresponding to
                the specified source and target programs.
                If the source and target are the same,
                it returns an instance of PassThroughProgramConverter.

        Raises:
            ProgramConverterNotFoundError:
                Raised when the requested converter is not found.

        """
        if from_lib == to_lib:
            return PassThroughProgramConverter()

        converter = self._converters.get((from_lib, to_lib))

        if converter is None:
            msg = f"Converter not found for conversion from {from_lib} to {to_lib}."
            raise ProgramConverterNotFoundError(msg)

        return converter

    def register_converter(
        self,
        from_lib: str,
        to_lib: str,
        converter: ProgramConverter,
    ) -> None:
        """Register a converter between the specified programs.

        Args:
            from_lib (str): The name of the source program.
            to_lib (str): The name of the target program.
            converter (ProgramConverter): The converter instance to register.

        Raises:
            ProgramConverterAlreadyRegisteredError:
                Raised when attempting to re-register an already registered converter.

        """
        key = (from_lib, to_lib)
        if key in self._converters:
            msg = f"Converter already registered for conversion from {from_lib} to {
                to_lib
            }."
            raise ProgramConverterAlreadyRegisteredError(msg)

        self._converters[key] = converter

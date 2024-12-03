from typing import Any

from .program_converter import ProgramConverter


class PassThroughProgramConverter(ProgramConverter):
    """A converter that returns the input program as is.

    It is used internally in Tranqu as a placeholder
    when a converter is not needed during transpilation.
    """

    def convert(self, program: Any) -> Any:  # noqa: ANN401 PLR6301
        """Return the input program as is.

        Args:
            program (Any): The program to be converted.

        Returns:
            Any: The program returned without any conversion.

        """
        return program

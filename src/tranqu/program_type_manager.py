from typing import Any

from .tranqu_error import TranquError


class ProgramLibNotFoundError(TranquError):
    """Error when program library cannot be detected."""


class ProgramTypeManager:
    """Class that manages the mapping between program types and library identifiers."""

    def __init__(self) -> None:
        self._type_registry: dict[type, str] = {}

    def register_type(self, program_lib: str, program_type: type) -> None:
        """Register a program type and its library identifier.

        Args:
            program_lib (str): Library identifier (e.g., "qiskit", "tket")
            program_type (Type): Program type class to register

        """
        self._type_registry[program_type] = program_lib

    def detect_lib(self, program: Any) -> str:  # noqa: ANN401
        """Detect the library based on the program type.

        Args:
            program (Any): Program to inspect

        Returns:
            str: Detected library identifier

        Raises:
            ProgramLibNotFoundError: If the program type is not registered

        """
        for program_type, lib in self._type_registry.items():
            if isinstance(program, program_type):
                return lib

        msg = (
            "Could not detect program library. Please either "
            "specify program_lib or register the program type "
            "using register_program_type()."
        )
        raise ProgramLibNotFoundError(msg)

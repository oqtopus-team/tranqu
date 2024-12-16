from typing import Any


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

    def detect_lib(self, program: Any) -> str | None:  # noqa: ANN401
        """Detect the library based on the program type.

        Args:
            program (Any): Program to inspect

        Returns:
            str | None: Library identifier for registered program type, None otherwise

        """
        for program_type, lib in self._type_registry.items():
            if isinstance(program, program_type):
                return lib

        return None

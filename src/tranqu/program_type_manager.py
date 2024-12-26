from typing import Any

from .tranqu_error import TranquError


class ProgramTypeError(TranquError):
    """Base exception for program type-related errors."""


class ProgramLibraryAlreadyRegisteredError(ProgramTypeError):
    """Raised when attempting to register a program library that already exists."""


class ProgramTypeManager:
    """Class that manages the mapping between program types and library identifiers."""

    def __init__(self) -> None:
        self._type_registry: dict[type[Any], str] = {}

    def register_type(
        self, program_lib: str, program_type: type[Any], *, allow_override: bool = False
    ) -> None:
        """Register a program type with its corresponding library identifier.

        Args:
            program_lib (str): Library identifier (e.g., "qiskit", "tket")
            program_type (type[Any]): Type of the program to register
            allow_override (bool): When False, prevents overwriting existing
              registrations. Defaults to False.

        Raises:
            ProgramLibraryAlreadyRegisteredError: If the library is already
              registered and allow_override is False.

        """
        if not allow_override and program_lib in self._type_registry.values():
            msg = (
                f"Library '{program_lib}' is already registered. "
                "Use allow_override=True to force registration."
            )
            raise ProgramLibraryAlreadyRegisteredError(msg)

        self._type_registry[program_type] = program_lib

    def resolve_lib(self, program: Any) -> str | None:  # noqa: ANN401
        """Resolve the library identifier for a given program instance.

        Args:
            program (Any): Program instance to inspect

        Returns:
            The library identifier if the program type is registered, None otherwise.

        """
        for program_type, lib in self._type_registry.items():
            if isinstance(program, program_type):
                return lib

        return None

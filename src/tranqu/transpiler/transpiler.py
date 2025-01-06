from abc import ABC, abstractmethod
from typing import Any

from tranqu.transpile_result import TranspileResult


class Transpiler(ABC):
    """Abstract base class for transpiling specified quantum circuits.

    This class provides an abstract method to transpile a given quantum circuit and
    return a `TranspileResult`.
    The specific implementation of the transpiler must be defined in subclasses.

    Args:
            program_lib (str): The program format that this transpiler handles.

    """

    def __init__(self, program_lib: str) -> None:
        self._program_lib = program_lib

    @property
    def program_lib(self) -> str:
        """Returns the program format that this transpiler handles.

        Returns:
            str: The program format identifier (e.g., "qiskit", "tket").

        """
        return self._program_lib

    @abstractmethod
    def transpile(
        self,
        program: Any,  # noqa: ANN401
        options: dict | None = None,
        device: Any | None = None,  # noqa: ANN401
    ) -> TranspileResult:
        """Abstract method to transpile the specified quantum circuit.

        This method transpiles the given quantum circuit and
        returns a `TranspileResult`.
        The specific implementation of the transpilation must be defined in subclasses.

        Args:
            program (Any): The circuit object or code converted to
                the transpiler's target (e.g., Qiskit, Tket, OpenQASM3, etc.).
            options (dict | None, optional): Transpilation options. Defaults to
                an empty dictionary.
            device (Any | None, optional): The target device for transpilation.
                Defaults to None.

        Returns:
            TranspileResult: The result of the transpilation, including
                the transpiled quantum circuit, statistical information,
                and mapping between virtual and physical quantum bits.

        """

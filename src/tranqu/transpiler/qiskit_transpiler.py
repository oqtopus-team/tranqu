import copy
from typing import Any

from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit import transpile as qiskit_transpile

from tranqu.transpile_result import TranspileResult

from .base_qiskit_transpiler import BaseQiskitTranspiler


class QiskitTranspiler(BaseQiskitTranspiler):
    """Transpile quantum circuits using Qiskit.

    It optimizes quantum circuits using Qiskit's `transpile()` function.
    """

    def transpile(
        self,
        program: QuantumCircuit,
        options: dict | None = None,
        device: Any | None = None,  # noqa: ANN401
    ) -> TranspileResult:
        """Transpile the specified quantum circuit and return a TranspileResult.

        Args:
            program (QuantumCircuit): The quantum circuit to transpile.
            options (dict, optional): Transpilation options.
                Defaults to an empty dictionary.
            device (Any, optional): The target device for transpilation.
                Defaults to None.

        Returns:
            TranspileResult: An object containing the transpilation result,
                including the transpiled quantum circuit, statistics,
                and the mapping of virtual qubits to physical qubits.

        """
        _options = copy.deepcopy(options or {})
        if device is not None:
            _options["backend"] = device

        transpiled_program = qiskit_transpile(program, **_options)
        return self._create_transpile_result(program, transpiled_program)

from typing import Any

import pytest
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu import Tranqu


class TestOuquTpTranspiler:
    @pytest.fixture
    def tranqu(self) -> Tranqu:
        return Tranqu()

    @pytest.fixture
    def simple_device(self) -> dict[str, Any]:
        return {
            "name": "simple_device",
            "qubits": [
                {
                    "id": 0,
                    "fidelity": 0.99,
                    "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                },
                {
                    "id": 1,
                    "fidelity": 0.98,
                    "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                },
            ],
            "couplings": [
                {
                    "control": 0,
                    "target": 1,
                    "fidelity": 0.95,
                    "gate_duration": {"cx": 100.0},
                }
            ],
        }

    def test_transpile_simple_qasm3_program(
        self, tranqu: Tranqu, simple_device: dict[str, Any]
    ):
        program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;

h q[0];
cx q[0],q[1];
"""
        result = tranqu.transpile(
            program=program,
            program_lib="openqasm3",
            transpiler_lib="ouqu-tp",
            device=simple_device,
            device_lib="oqtopus",
        )

        assert isinstance(result.transpiled_program, str)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

    def test_transpile_qiskit_program(
        self, tranqu: Tranqu, simple_device: dict[str, Any]
    ):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        result = tranqu.transpile(
            program=circuit,
            program_lib="qiskit",
            transpiler_lib="ouqu-tp",
            device=simple_device,
            device_lib="oqtopus",
        )

        assert isinstance(result.transpiled_program, QuantumCircuit)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

    def test_transpile_tket_program(
        self, tranqu: Tranqu, simple_device: dict[str, Any]
    ):
        circuit = TketCircuit(2)
        circuit.H(0)
        circuit.CX(0, 1)

        result = tranqu.transpile(
            program=circuit,
            program_lib="tket",
            transpiler_lib="ouqu-tp",
            device=simple_device,
            device_lib="oqtopus",
        )

        assert isinstance(result.transpiled_program, TketCircuit)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

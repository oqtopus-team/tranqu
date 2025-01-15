from typing import Any

import pytest
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.circuit import Parameter  # type: ignore[import-untyped]
from qiskit.circuit.library import (  # type: ignore[import-untyped]
    CXGate,
    RZGate,
    SXGate,
    XGate,
)
from qiskit.providers import BackendV2  # type: ignore[import-untyped]
from qiskit.transpiler import (  # type: ignore[import-untyped]
    InstructionProperties,
    Target,
)

from tranqu import Tranqu
from tranqu.device_converter.qiskit_device import QiskitDevice


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

    @pytest.fixture
    def oqtopus_device(self) -> dict[str, Any]:
        return {
            "name": "oqtopus_device",
            "qubits": [
                {
                    "id": 0,
                    "fidelity": 0.90,
                    "meas_error": {
                        "prob_meas1_prep0": 0.01,
                        "prob_meas0_prep1": 0.02,
                    },
                    "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                },
                {
                    "id": 1,
                    "meas_error": {
                        "prob_meas1_prep0": 0.01,
                        "prob_meas0_prep1": 0.02,
                    },
                    "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                },
                {
                    "id": 2,
                    "fidelity": 0.99,
                    "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                },
                {
                    "id": 3,
                    "fidelity": 0.99,
                    "meas_error": {
                        "prob_meas1_prep0": 0.01,
                        "prob_meas0_prep1": 0.02,
                    },
                },
            ],
            "couplings": [
                {
                    "control": 0,
                    "target": 2,
                    "fidelity": 0.8,
                    "gate_duration": {"cx": 60.0},
                },
                {"control": 0, "target": 1, "fidelity": 0.8},
                {"control": 1, "target": 0, "fidelity": 0.25},
                {"control": 1, "target": 3, "fidelity": 0.25},
                {"control": 2, "target": 0, "fidelity": 0.25},
                {"control": 2, "target": 3, "fidelity": 0.25},
                {"control": 3, "target": 1, "fidelity": 0.9},
                {"control": 3, "target": 2, "fidelity": 0.9},
            ],
            "timestamp": "2024-10-31 14:03:48.568126",
        }

    @pytest.fixture
    def qiskit_device(self) -> BackendV2:
        target = Target()

        x_props = {
            (0,): InstructionProperties(duration=60e-9, error=0.01),
            (1,): InstructionProperties(duration=60e-9, error=0.02),
        }
        sx_props = {
            (0,): InstructionProperties(duration=30e-9, error=0.01),
            (1,): InstructionProperties(duration=30e-9, error=0.02),
        }
        rz_props = {
            (0,): InstructionProperties(duration=0, error=0.01),
            (1,): InstructionProperties(duration=0, error=0.02),
        }

        cx_props = {
            (0, 1): InstructionProperties(duration=100e-9, error=0.05),
        }

        target.add_instruction(XGate(), x_props)
        target.add_instruction(SXGate(), sx_props)
        theta = Parameter("theta")
        target.add_instruction(RZGate(theta), rz_props)
        target.add_instruction(CXGate(), cx_props)

        return QiskitDevice("test_device", target)

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

    def test_transpile_oqtopus_qasm3_program(
        self, tranqu: Tranqu, oqtopus_device: dict[str, Any]
    ):
        program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];

c = measure q;
"""
        result = tranqu.transpile(
            program=program,
            program_lib="openqasm3",
            transpiler_lib="ouqu-tp",
            device=oqtopus_device,
            device_lib="oqtopus",
        )

        assert isinstance(result.transpiled_program, str)
        assert result.stats != {}
        expect_virtual_physical_mapping = {
            "qubit_mapping": {0: 3, 1: 1},
            "bit_mapping": {0: 0, 1: 1},
        }
        assert dict(result.virtual_physical_mapping) == expect_virtual_physical_mapping

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

    def test_transpile_qasm3_program_with_qiskit_device(
        self, tranqu: Tranqu, qiskit_device: BackendV2
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
            device=qiskit_device,
            device_lib="qiskit",
        )

        assert isinstance(result.transpiled_program, str)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

    def test_transpile_qiskit_program_with_qiskit_device(
        self, tranqu: Tranqu, qiskit_device: BackendV2
    ):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        result = tranqu.transpile(
            program=circuit,
            program_lib="qiskit",
            transpiler_lib="ouqu-tp",
            device=qiskit_device,
            device_lib="qiskit",
        )

        assert isinstance(result.transpiled_program, QuantumCircuit)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

    def test_transpile_tket_program_with_qiskit_device(
        self, tranqu: Tranqu, qiskit_device: BackendV2
    ):
        circuit = TketCircuit(2)
        circuit.H(0)
        circuit.CX(0, 1)

        result = tranqu.transpile(
            program=circuit,
            program_lib="tket",
            transpiler_lib="ouqu-tp",
            device=qiskit_device,
            device_lib="qiskit",
        )

        assert isinstance(result.transpiled_program, TketCircuit)
        assert result.stats != {}
        assert result.virtual_physical_mapping != {}

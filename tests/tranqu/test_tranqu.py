# mypy: disable-error-code="import-untyped"

import re

import pytest
from qiskit import QuantumCircuit as QiskitCircuit

from tranqu import Tranqu, __version__
from tranqu.program_converter import ProgramConverter
from tranqu.transpiler_dispatcher import (
    DeviceConversionPathNotFoundError,
    ProgramConversionPathNotFoundError,
)


class EnigmaCircuit:
    """Custom circuit class"""


class EnigmaToQiskitConverter(ProgramConverter):
    def convert(self, _program: EnigmaCircuit) -> QiskitCircuit:
        return QiskitCircuit()


class QiskitToEnigmaConverter(ProgramConverter):
    def convert(self, _program: QiskitCircuit) -> EnigmaCircuit:
        return EnigmaCircuit()


class TestTranqu:
    def test_version(self):
        assert isinstance(__version__, str)
        # Check if the version string follows semantic versioning format
        assert re.match(r"^\d+\.\d+\.\d+(-\w+(\.\d+)?)?$", __version__)

    class TestCustomProgramsAndConverters:
        def test_transpile_custom_circuit_with_qiskit_transpiler(self):
            tranqu = Tranqu()
            tranqu.register_program_converter(
                "enigma",
                "qiskit",
                EnigmaToQiskitConverter(),
            )
            tranqu.register_program_converter(
                "qiskit",
                "enigma",
                QiskitToEnigmaConverter(),
            )
            circuit = EnigmaCircuit()

            result = tranqu.transpile(circuit, "enigma", "qiskit")

            assert isinstance(result.transpiled_program, EnigmaCircuit)

    class TestOqtopusDevice:
        def test_transpile_openqasm3_program_for_oqtopus_device_with_qiskit_transpiler(
            self,
        ):
            tranqu = Tranqu()
            openqasm3_program = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0],q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""
            oqtopus_device = {
                "name": "local_device",
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

            result = tranqu.transpile(
                openqasm3_program,
                program_lib="openqasm3",
                transpiler_lib="qiskit",
                transpiler_options={"optimization_level": 2},
                device=oqtopus_device,
                device_lib="oqtopus",
            )

            expected_program = """OPENQASM 3.0;
include "stdgates.inc";
bit[2] c;
rz(pi/2) $3;
sx $3;
rz(pi/2) $3;
cx $3, $2;
c[0] = measure $3;
c[1] = measure $2;
"""
            assert result.transpiled_program == expected_program

    def test_program_conversion_path_not_found(self):
        tranqu = Tranqu()
        circuit = EnigmaCircuit()

        with pytest.raises(
            ProgramConversionPathNotFoundError,
            match="No ProgramConverter path found to convert from enigma to qiskit",
        ):
            tranqu.transpile(circuit, "enigma", "qiskit")

    def test_device_conversion_path_not_found(self):
        tranqu = Tranqu()
        circuit = QiskitCircuit(2)
        device = {"name": "custom_device", "qubits": [], "couplings": []}

        with pytest.raises(
            DeviceConversionPathNotFoundError,
            match="No DeviceConverter path found to convert from custom to qiskit",
        ):
            tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=device,
                device_lib="custom",
            )

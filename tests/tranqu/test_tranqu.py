# mypy: disable-error-code="import-untyped"

import re

import pytest
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit_ibm_runtime.fake_provider import FakeSantiagoV2

from tranqu import Tranqu, __version__
from tranqu.device_converter import (
    OqtoqusToQiskitDeviceConverter,
    QiskitToOuquTpDeviceConverter,
)
from tranqu.program_converter import (
    Openqasm3ToTketProgramConverter,
    ProgramConverter,
    QiskitToOpenqasm3ProgramConverter,
    TketToQiskitProgramConverter,
)
from tranqu.transpiler.transpiler_manager import TranspilerNotFoundError
from tranqu.transpiler_dispatcher import (
    DeviceConversionPathNotFoundError,
    DeviceNotSpecifiedError,
    ProgramConversionPathNotFoundError,
    ProgramLibResolutionError,
    ProgramNotSpecifiedError,
    TranspilerLibNotSpecifiedError,
)


class EnigmaCircuit:
    """Custom circuit class"""


class EnigmaToQiskitConverter(ProgramConverter):
    def convert(self, _program: EnigmaCircuit) -> QiskitCircuit:
        return QiskitCircuit()


class QiskitToEnigmaConverter(ProgramConverter):
    def convert(self, _program: QiskitCircuit) -> EnigmaCircuit:
        return EnigmaCircuit()


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


class TestTranqu:
    def test_version(self):
        assert isinstance(__version__, str)
        # Check if the version string follows semantic versioning format
        assert re.match(r"^\d+\.\d+\.\d+(-\w+(\.\d+)?)?$", __version__)

    class TestCustomProgramsAndConverters:
        def test_transpile_custom_circuit_with_qiskit_transpiler(self, tranqu: Tranqu):
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

            result = tranqu.transpile(
                circuit, program_lib="enigma", transpiler_lib="qiskit"
            )

            assert isinstance(result.transpiled_program, EnigmaCircuit)

    class TestOqtopusDevice:
        def test_transpile_openqasm3_program_for_oqtopus_device_with_qiskit_transpiler(
            self, tranqu: Tranqu
        ):
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
                "device_id": "local_device",
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

    def test_program_conversion_via_qiskit(self, tranqu: Tranqu):
        tranqu._program_converter_manager._converters.clear()  # noqa: SLF001

        tranqu.register_program_converter(
            "tket",
            "qiskit",
            TketToQiskitProgramConverter(),
        )
        tranqu.register_program_converter(
            "qiskit",
            "openqasm3",
            QiskitToOpenqasm3ProgramConverter(),
        )
        tranqu.register_program_converter(
            "openqasm3",
            "tket",
            Openqasm3ToTketProgramConverter(),
        )

        result = tranqu.transpile(
            TketCircuit(1),
            program_lib="tket",
            transpiler_lib="ouqu-tp",
        )

        assert isinstance(result.transpiled_program, TketCircuit)

    def test_device_conversion_via_qiskit(self, tranqu: Tranqu):
        oqtopus_device = {
            "device_id": "test_device",
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
                    "fidelity": 0.97,
                    "gate_duration": {"cx": 300.0},
                }
            ],
        }
        tranqu._device_converter_manager._converters.clear()  # noqa: SLF001
        tranqu.register_device_type("oqtopus", dict)
        tranqu.register_device_converter(
            "oqtopus", "qiskit", OqtoqusToQiskitDeviceConverter()
        )
        tranqu.register_device_converter(
            "qiskit", "ouqu-tp", QiskitToOuquTpDeviceConverter()
        )

        result = tranqu.transpile(
            TketCircuit(2),
            transpiler_lib="ouqu-tp",
            device=oqtopus_device,
        )

        assert isinstance(result.transpiled_program, TketCircuit)

    def test_program_conversion_path_not_found(self, tranqu: Tranqu):
        circuit = EnigmaCircuit()

        with pytest.raises(
            ProgramConversionPathNotFoundError,
            match="No ProgramConverter path found to convert from enigma to qiskit",
        ):
            tranqu.transpile(circuit, program_lib="enigma", transpiler_lib="qiskit")

    def test_device_conversion_path_not_found(self, tranqu: Tranqu):
        circuit = QiskitCircuit(2)
        device = {"device_id": "custom_device", "qubits": [], "couplings": []}

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

    def test_resolve_program_lib(self, tranqu: Tranqu):
        circuit = QiskitCircuit(1)

        result = tranqu.transpile(
            circuit,
            transpiler_lib="qiskit",
        )

        assert isinstance(result.transpiled_program, QiskitCircuit)

    def test_resolve_program_lib_with_tket_circuit(self, tranqu: Tranqu):
        circuit = TketCircuit(1)

        result = tranqu.transpile(
            circuit,
            transpiler_lib="qiskit",
        )

        assert isinstance(result.transpiled_program, TketCircuit)

    def test_resolve_device_lib(self, tranqu: Tranqu):
        device = FakeSantiagoV2()

        result = tranqu.transpile(
            QiskitCircuit(1),
            transpiler_lib="qiskit",
            device=device,
        )

        assert isinstance(result.transpiled_program, QiskitCircuit)

    def test_program_not_specified(self, tranqu: Tranqu):
        with pytest.raises(
            ProgramNotSpecifiedError,
            match=r"No program specified\.",
        ):
            tranqu.transpile(
                program=None,
                transpiler_lib="qiskit",
            )

    def test_transpiler_lib_not_specified(self, tranqu: Tranqu):
        circuit = QiskitCircuit(1)

        with pytest.raises(
            TranspilerLibNotSpecifiedError,
            match=r"No transpiler library specified\.",
        ):
            tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib=None,
            )

    def test_transpiler_lib_not_exist(self, tranqu: Tranqu):
        tranqu.register_default_transpiler_lib("nop")
        circuit = QiskitCircuit(1)

        with pytest.raises(
            TranspilerNotFoundError,
            match="Unknown transpiler: nop",
        ):
            tranqu.transpile(
                circuit,
                program_lib="qiskit",
            )

    def test_program_lib_not_found(self, tranqu: Tranqu):
        class UnknownCircuit:
            pass

        circuit = UnknownCircuit()

        with pytest.raises(
            ProgramLibResolutionError, match=r"Could not resolve program library\."
        ):
            tranqu.transpile(
                circuit,
                transpiler_lib="qiskit",
            )

    def test_device_not_specified_error(self, tranqu: Tranqu):
        circuit = QiskitCircuit(1)

        with pytest.raises(
            DeviceNotSpecifiedError,
            match=r"Device library is specified but no device is specified\.",
        ):
            tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=None,
                device_lib="qiskit",
            )

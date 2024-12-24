import json
from typing import Any, ClassVar

from qiskit.providers import BackendV2  # type: ignore[import-untyped]
from qiskit.transpiler import InstructionProperties  # type: ignore[import-untyped]

from .device_converter import DeviceConverter


class QiskitToOuquTpDeviceConverter(DeviceConverter):
    """Device converter for converting from Qiskit to ouqu-tp format."""

    _SINGLE_QUBIT_GATES: ClassVar[list[str]] = ["x", "sx", "rz"]
    _TWO_QUBIT_GATE = "cx"
    _NANO_SECONDS = 1e9

    def convert(self, device: BackendV2) -> str:
        """Convert a Qiskit device to ouqu-tp format.

        Args:
            device (BackendV2): The Qiskit device to be converted.

        Returns:
            str: The converted ouqu-tp format device.

        """
        ouqu_tp_device = {
            "name": device.name,
            "qubits": self._convert_qubits(device),
            "couplings": self._convert_couplings(device),
        }

        return json.dumps(ouqu_tp_device)

    def _convert_qubits(self, device: BackendV2) -> list[dict[str, Any]]:
        qubits = []
        target = device.target

        for qubit in range(device.num_qubits):
            qubit_info = {"id": qubit, "gate_duration": {}, "fidelity": None}

            for gate_name in self._SINGLE_QUBIT_GATES:
                if target.instruction_supported(gate_name, (qubit,)):
                    props = target[gate_name][qubit,]
                    if props:
                        self._update_properties(qubit_info, props, gate_name)

            qubits.append(qubit_info)

        return qubits

    def _convert_couplings(self, device: BackendV2) -> list[dict[str, Any]]:
        couplings = []
        target = device.target
        coupling_map = device.coupling_map

        if coupling_map:
            for control, target_qubit in coupling_map:
                coupling_info = {
                    "control": control,
                    "target": target_qubit,
                    "gate_duration": {},
                    "fidelity": None,
                }

                qargs = (control, target_qubit)
                if target.instruction_supported(self._TWO_QUBIT_GATE, qargs):
                    props = target[self._TWO_QUBIT_GATE][qargs]
                    if props:
                        self._update_properties(
                            coupling_info,
                            props,
                            self._TWO_QUBIT_GATE,
                        )

                couplings.append(coupling_info)

        return couplings

    def _update_properties(
        self,
        info: dict[str, Any],
        props: InstructionProperties,
        gate_name: str,
    ) -> None:
        if props.duration is not None:
            info["gate_duration"][gate_name] = props.duration * self._NANO_SECONDS
        if props.error is not None:
            info["fidelity"] = 1 - props.error

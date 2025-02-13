# mypy: disable-error-code="import-untyped"

from typing import Any

from qiskit.circuit import Parameter
from qiskit.circuit.library import (
    CXGate,
    Measure,
    RZGate,
    SXGate,
    XGate,
)
from qiskit.providers import BackendV2
from qiskit.transpiler import InstructionProperties, Target

from .device_converter import DeviceConverter
from .device_converter_manager import DeviceConverterError
from .qiskit_device import QiskitDevice


class OqtoqusToQiskitDeviceConverter(DeviceConverter):
    """Device converter for converting from Oqtopus to Qiskit format."""

    def convert(self, device: Any) -> BackendV2:  # noqa: ANN401
        """Convert a Oqtopus device to Qiskit device format.

        Args:
            device (Any): The Oqtopus device to be converted.

        Returns:
            BackendV2: The converted Qiskit format device.

        Raises:
            DeviceConverterError: If the conversion fails.

        """
        if "device_id" in device:
            device_id = device["device_id"]
        else:
            msg = "The device information is missing the key 'device_id'."
            raise DeviceConverterError(msg)

        if "qubits" not in device:
            msg = "The device information is missing the key 'qubits'."
            raise DeviceConverterError(msg)

        if "couplings" not in device:
            msg = "The device information is missing the key 'couplings'."
            raise DeviceConverterError(msg)

        target = self._convert_oqtopus_device_to_qiskit_target(device)

        return QiskitDevice(device_id, target)

    @staticmethod
    def _convert_oqtopus_device_to_qiskit_target(oqtopus_device: dict) -> Target:  # noqa: PLR0914
        target = Target()

        # x, sx, rz instructions
        x_props = {}
        sx_props = {}
        rz_props = {}
        meas_props = {}
        for qubit in oqtopus_device["qubits"]:
            # duration, error of gates
            gate_duration = qubit.get("gate_duration", {})
            x_duration = gate_duration["x"] * 1e-9 if "x" in gate_duration else None
            sx_duration = gate_duration["sx"] * 1e-9 if "sx" in gate_duration else None
            rz_duration = gate_duration["rz"] * 1e-9 if "rz" in gate_duration else None
            error = 1 - qubit["fidelity"] if "fidelity" in qubit else None

            # error of measurements
            meas_error_dict = qubit.get("meas_error", {})
            prob_meas1_prep0 = meas_error_dict.get("prob_meas1_prep0")
            prob_meas0_prep1 = meas_error_dict.get("prob_meas0_prep1")
            if prob_meas1_prep0 is not None and prob_meas0_prep1 is not None:
                meas_error = (prob_meas1_prep0 + prob_meas0_prep1) / 2
            else:
                meas_error = None

            # create InstructionProperties
            x_props[int(qubit["id"]),] = InstructionProperties(
                duration=x_duration,
                error=error,
            )
            sx_props[int(qubit["id"]),] = InstructionProperties(
                duration=sx_duration,
                error=error,
            )
            rz_props[int(qubit["id"]),] = InstructionProperties(
                duration=rz_duration,
                error=error,
            )
            meas_props[int(qubit["id"]),] = InstructionProperties(error=meas_error)

        target.add_instruction(XGate(), x_props)
        target.add_instruction(SXGate(), sx_props)
        theta = Parameter("theta")
        target.add_instruction(RZGate(theta), rz_props)
        target.add_instruction(Measure(), meas_props)

        # cx instructions
        cx_props = {}
        for coupling in oqtopus_device["couplings"]:
            duration = coupling.get("gate_duration", {}).get("cx")
            error = 1 - coupling["fidelity"] if "fidelity" in coupling else None
            cx_props[int(coupling["control"]), int(coupling["target"])] = (
                InstructionProperties(duration=duration, error=error)
            )
        target.add_instruction(CXGate(), cx_props)

        return target

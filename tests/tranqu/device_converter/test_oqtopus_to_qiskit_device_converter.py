import pytest
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from tranqu.device_converter import DeviceConverterError, OqtoqusToQiskitDeviceConverter


class TestOqtoqusToQiskitDeviceConverter:
    def setup_method(self):
        self.converter = OqtoqusToQiskitDeviceConverter()

    def test_convert_valid_device(self):
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

        result = self.converter.convert(oqtopus_device)

        assert isinstance(result, BackendV2)

    def test_convert_invalid_device_no_name(self):
        oqtopus_device = {
            "qubits": [],
            "couplings": [],
        }

        with pytest.raises(DeviceConverterError):
            self.converter.convert(oqtopus_device)

    def test_convert_invalid_device_no_qubits(self):
        oqtopus_device = {
            "device_id": "local_device",
            "couplings": [],
        }

        with pytest.raises(DeviceConverterError):
            self.converter.convert(oqtopus_device)

    def test_convert_invalid_device_no_couplings(self):
        oqtopus_device = {
            "device_id": "local_device",
            "qubits": [],
        }

        with pytest.raises(DeviceConverterError):
            self.converter.convert(oqtopus_device)

    def test_convert_empty_device(self):
        oqtopus_device = {
            "device_id": "local_device",
            "qubits": [],
            "couplings": [],
        }

        result = self.converter.convert(oqtopus_device)

        assert isinstance(result, BackendV2)

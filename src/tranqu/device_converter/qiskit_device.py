from typing import Any

from qiskit.providers import BackendV2  # type: ignore[import-untyped]
from qiskit.providers.options import Options  # type: ignore[import-untyped]
from qiskit.transpiler import Target  # type: ignore[import-untyped]


class QiskitDevice(BackendV2):
    """Device class extending Qiskit's BackendV2.

    This class represents a target device used in Qiskit's transpiler.

    Args:
        name (str): Name of the device.
        target (Target): Target information used in the transpiler.

    """

    def __init__(self, name: str, target: Target) -> None:
        super().__init__(name=name)
        self._target = target

    @property
    def target(self) -> Any:  # noqa: ANN401
        """Retrieve the target information of the device.

        Returns:
            Target: Target information used in the transpiler.

        """
        return self._target

    @property
    def max_circuits(self) -> Any:  # noqa: ANN401
        """Raise an exception for unsupported functionality.

        Raises:
            NotImplementedError: 'max_circuits' function is not supported.

        """
        msg = "'max_circuits' function is not supported."
        raise NotImplementedError(msg)

    @classmethod
    def _default_options(cls) -> Options:
        return Options()

    def run(self, _run_input: Any, **_options: dict[str, Any]) -> Any:  # noqa: ANN401
        """Raise an exception for unsupported functionality.

        Raises:
            NotImplementedError: 'run' function is not supported.

        """
        msg = "'run' function is not supported."
        raise NotImplementedError(msg)

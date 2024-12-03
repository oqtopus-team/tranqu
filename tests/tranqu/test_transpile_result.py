import pytest
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu import Tranqu
from tranqu.transpile_result import TranspileResult


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


@pytest.fixture
def transpile_data():
    stats = {
        "before": {"n_qubits": 1, "n_gates_1q": 2, "n_gates_2q": 0, "depth": 2},
        "after": {"n_qubits": 1, "n_gates_1q": 0, "n_gates_2q": 0, "depth": 0},
    }
    virtual_physical_mapping = {
        "qubit_mapping": {0: 1, 1: 0, 2: 2},
        "bit_mapping": {0: 0, 1: 1},
    }
    return stats, virtual_physical_mapping


class TestTraspileResult:
    def test_stats(self, tranqu: Tranqu):
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.h(0)

        result = tranqu.transpile(
            circuit,
            program_lib="qiskit",
            transpiler_lib="qiskit",
        )

        assert result.stats.before.n_qubits == 1
        assert result.stats.before.n_gates_1q == 2
        assert result.stats.before.n_gates_2q == 0
        assert result.stats.before.depth == 2

        assert result.stats.after.n_qubits == 1
        assert result.stats.after.n_gates_1q == 0
        assert result.stats.after.n_gates_2q == 0
        assert result.stats.after.depth == 0

    def test_qubit_mapping(self, tranqu: Tranqu):
        circuit = QuantumCircuit(3)

        result = tranqu.transpile(
            circuit,
            program_lib="qiskit",
            transpiler_lib="qiskit",
            transpiler_options={"initial_layout": [1, 0, 2]},
        )

        assert result.virtual_physical_mapping.qubit_mapping == {0: 1, 1: 0, 2: 2}
        assert result.virtual_physical_mapping.bit_mapping == {}

    def test_bit_mapping(self, tranqu: Tranqu):
        circuit = QuantumCircuit(2, 2)

        result = tranqu.transpile(
            circuit,
            program_lib="qiskit",
            transpiler_lib="qiskit",
            transpiler_options={"initial_layout": [0, 1]},
        )

        assert result.virtual_physical_mapping.qubit_mapping == {0: 0, 1: 1}
        assert result.virtual_physical_mapping.bit_mapping == {0: 0, 1: 1}

    def test_transpile_result_to_dict(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        transpiled_program = "dummy_program"
        result = TranspileResult(transpiled_program, stats, virtual_physical_mapping)
        result_dict = result.to_dict()

        expected_dict = {
            "stats": stats,
            "virtual_physical_mapping": virtual_physical_mapping,
        }

        assert result_dict == expected_dict

    def test_transpile_result_repr(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        transpiled_program = "dummy_program"
        result = TranspileResult(transpiled_program, stats, virtual_physical_mapping)

        assert repr(result) == repr(stats)

    def test_transpile_result_str(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        transpiled_program = "dummy_program"
        result = TranspileResult(transpiled_program, stats, virtual_physical_mapping)

        expected_str = str(stats)
        assert str(result) == expected_str

    def test_transpile_result_equality(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        transpiled_program_1 = "dummy_program_1"
        transpiled_program_2 = "dummy_program_2"

        result_1 = TranspileResult(
            transpiled_program_1, stats, virtual_physical_mapping
        )
        result_2 = TranspileResult(
            transpiled_program_1, stats, virtual_physical_mapping
        )
        result_3 = TranspileResult(
            transpiled_program_2, stats, virtual_physical_mapping
        )

        assert result_1 == result_2
        assert result_1 != result_3
        assert result_1 != "NOT A DICT"

    def test_transpile_result_len(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        result = TranspileResult("dummy_program", stats, virtual_physical_mapping)

        assert len(result) == len(stats)

    def test_transpile_result_getitem(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        result = TranspileResult("dummy_program", stats, virtual_physical_mapping)

        before_stats = result["before"]
        assert before_stats["n_qubits"] == 1
        assert before_stats["n_gates_1q"] == 2
        assert before_stats["n_gates_2q"] == 0
        assert before_stats["depth"] == 2

        after_stats = result["after"]
        assert after_stats["n_qubits"] == 1
        assert after_stats["n_gates_1q"] == 0
        assert after_stats["n_gates_2q"] == 0
        assert after_stats["depth"] == 0

    def test_transpile_result_iter(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        result = TranspileResult("dummy_program", stats, virtual_physical_mapping)

        keys = list(result)
        assert keys == ["before", "after"]

    def test_transpile_result_hash(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        transpiled_program_1 = "dummy_program_1"
        transpiled_program_2 = "dummy_program_2"

        result_1 = TranspileResult(
            transpiled_program_1, stats, virtual_physical_mapping
        )
        result_2 = TranspileResult(
            transpiled_program_1, stats, virtual_physical_mapping
        )
        result_3 = TranspileResult(
            transpiled_program_2, stats, virtual_physical_mapping
        )

        assert hash(result_1) == hash(result_2)
        assert hash(result_1) != hash(result_3)

    def test_nested_dict_accessor_attribute_error(self, transpile_data: tuple):
        stats, virtual_physical_mapping = transpile_data
        result = TranspileResult("dummy_program", stats, virtual_physical_mapping)

        with pytest.raises(AttributeError, match="No such attribute: non_existent"):
            _ = result.stats.non_existent

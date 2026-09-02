from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tranqu.transpiler.tket_layout_mapper import TketLayoutMapper


@dataclass
class FakeCircuit:
    qubits: list[object]
    bits: list[object]


@dataclass
class FakeIndexedQubit:
    index: object


def test_create_mapping_uses_identity_when_final_map_is_missing() -> None:
    mapper = TketLayoutMapper()
    circuit = FakeCircuit(qubits=[object(), object()], bits=[object()])

    mapping = mapper.create_mapping_from_compilation_unit(
        cast("Any", SimpleNamespace()),
        cast("Any", circuit),
    )

    assert mapping == {
        "qubit_mapping": {0: 0, 1: 1},
        "bit_mapping": {0: 0},
    }


def _qubit_index(mapper: TketLayoutMapper, qubit: object, circuit: FakeCircuit) -> int:
    return mapper._qubit_index(qubit, cast("Any", circuit))  # ruff: ignore[private-member-access]


def test_qubit_index_returns_integer_index() -> None:
    mapper = TketLayoutMapper()

    assert (
        _qubit_index(mapper, FakeIndexedQubit(3), FakeCircuit(qubits=[], bits=[])) == 3
    )


def test_qubit_index_supports_sequence_indices() -> None:
    mapper = TketLayoutMapper()

    assert (
        _qubit_index(mapper, FakeIndexedQubit((2,)), FakeCircuit(qubits=[], bits=[]))
        == 2
    )


def test_qubit_index_falls_back_to_circuit_position() -> None:
    mapper = TketLayoutMapper()
    qubit = object()
    circuit = FakeCircuit(qubits=[object(), qubit], bits=[])

    assert _qubit_index(mapper, qubit, circuit) == 1


def test_qubit_index_raises_for_unknown_qubit() -> None:
    mapper = TketLayoutMapper()
    circuit = FakeCircuit(qubits=[object()], bits=[])

    with pytest.raises(ValueError, match="not found"):
        _qubit_index(mapper, object(), circuit)

"""Provides a class to hold the results of quantum circuit transpilation.

The `TranspileResult` class holds the transpiled program, statistical information
before and after transpilation, and the mapping between virtual and physical (qu)bits.
This object is returned as the return value of the `transpile()` method in `Tranqu`.

Example:
    The following example demonstrates how to access the statistical information and
    virtual-physical qubit mapping of a transpile result.

        >>> from tranqu import Tranqu
        >>> from qiskit import QuantumCircuit
        >>> tranqu = Tranqu()
        >>> circuit = QuantumCircuit(2)
        >>> circuit.swap(0, 1)
        >>> result = tranqu.transpile(circuit, program_lib="qiskit",
            transpiler_lib="qiskit",
            transpiler_options={"basis_gates": ["cx"],
                                "coupling_map": [[0, 1], [1, 0]]})
        >>> print(result.stats.after.n_gates)
        3
        >>> print(result.virtual_physical_mapping.qubit_mapping)
        {0: 0, 1: 1}

You can obtain the transpiled program from `TranspileResult`:

- `transpile_result.transpiled_program`: The transpiled program

You can also obtain the following statistical information:

- `transpile_result.stats.before.n_qubits`:
    Number of qubits in the circuit before transpilation
- `transpile_result.stats.before.n_gates_1q`:
    Number of 1-qubit gates before transpilation
- `transpile_result.stats.before.n_gates_2q`:
    Number of 2-qubit gates before transpilation
- `transpile_result.stats.before.depth`: Depth of the circuit before transpilation
- `transpile_result.stats.after.n_qubits`:
    Number of qubits in the circuit after transpilation
- `transpile_result.stats.after.n_gates_1q`: Number of 1-qubit gates after transpilation
- `transpile_result.stats.after.n_gates_2q`: Number of 2-qubit gates after transpilation
- `transpile_result.stats.after.depth`: Depth of the circuit after transpilation

You can also obtain the virtual-physical mapping information for
qubits and classical bits:

- `transpile_result.virtual_physical_mapping.qubit_mapping`:
    Mapping between virtual and physical qubits
- `transpile_result.virtual_physical_mapping.bit_mapping`:
    Mapping between virtual and physical classical bits

"""

from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Any


class NestedDictAccessor:
    """A utility class for accessing nested dictionary attributes.

    This class allows for easy access to nested dictionary attributes
    using dot notation. If a value in the dictionary is itself a dictionary,
    and the key is not in the specified stop keys, it returns another
    NestedDictAccessor instance for further nested access.

    Args:
        d (dict): The dictionary to be accessed.
        stop_keys (set[str] | None, optional): A set of keys where nested
            access should stop. If None, all keys are accessible.

    Raises:
        AttributeError: If an attribute name is not found in the dictionary.

    """

    def __init__(self, d: dict, stop_keys: set[str] | None = None) -> None:
        self._d = d
        self._stop_keys = stop_keys

    def __delitem__(self, key: str) -> None:
        """Delete the key via subscript (e.g., del obj[key]).

        Args:
            key (str): The key to delete.

        Raises:
            KeyError: If the key is not found in the dictionary.

        """
        if key in self._d:
            del self._d[key]
        else:
            msg = f"Key not found: {key}"
            raise KeyError(msg)

    def __getattr__(self, item: str) -> Any:  # noqa: ANN401
        """Retrieve an attribute from the nested dictionary.

        Args:
            item (str): The attribute name to retrieve.

        Returns:
            Any: The value associated with the attribute name. If the value is a
            dictionary and the attribute name is not in the stop keys, it returns
            a NestedDictAccessor for further nested access.

        Raises:
            AttributeError: If the attribute name is not found in the dictionary.

        """
        if item in self._d:
            value = self._d[item]
            if isinstance(value, dict) and (
                self._stop_keys is None or item not in self._stop_keys
            ):
                return NestedDictAccessor(value, self._stop_keys)
            return value

        msg = f"No such attribute: {item}"
        raise AttributeError(msg)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """Retrieve an item via subscript (e.g., obj[key]).

        Args:
            key (str): The key to retrieve.

        Returns:
            Any: The value associated with the attribute name. If the value is a
            dictionary and the attribute name is not in the stop keys, it returns
            a NestedDictAccessor for further nested access.

        Raises:
            KeyError: If the key is not found in the dictionary.

        """
        if key in self._d:
            value = self._d[key]
            if isinstance(value, dict) and (
                self._stop_keys is None or key not in self._stop_keys
            ):
                return NestedDictAccessor(value, self._stop_keys)
            return value

        msg = f"Key not found: {key}"
        raise KeyError(msg)

    def __iter__(self) -> Iterator:
        """Return an iterator over the keys of the internal dictionary.

        Returns:
            Iterator: An iterator over the keys of the dictionary.

        """
        return iter(self._d)

    def __repr__(self) -> str:
        """Return a string representation of the NestedDictAccessor.

        Returns:
            str: A string representation of the internal dictionary.

        """
        return repr(self._d)

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Set the key and the value via subscript (e.g., obj[key] = value).

        Args:
            key (str): The key to set.
            value (Any): The value to set.

        """
        self._d[key] = value

    def __str__(self) -> str:
        """Return a string representation of the NestedDictAccessor.

        Returns:
            str: A string representation of the internal dictionary.

        """
        return str(self._d)

    def items(self) -> ItemsView[Any, Any]:
        """Return an iterator over the (key, value) pairs of the dictionary.

        Returns:
            Iterator: A view over (key, value) pairs.

        """
        return self._d.items()

    def keys(self) -> KeysView[Any]:
        """Return an iterator over the keys of the dictionary.

        Returns:
            KeysView[Any]: A view over the keys.

        """
        return self._d.keys()

    def values(self) -> ValuesView[Any]:
        """Return an iterator over the values of the dictionary.

        Returns:
            ValuesView[Any]: A view over the values.

        """
        return self._d.values()


class TranspileResult:
    """Hold transpilation results.

    Args:
        transpiled_program: The quantum program after transpilation.
        stats: Statistical information before and after transpilation.
        virtual_physical_mapping: Mapping between virtual quantum bits and
            physical quantum bits.

    """

    def __init__(
        self,
        transpiled_program: Any,  # noqa: ANN401
        stats: dict[str, dict[str, int]],
        virtual_physical_mapping: dict[str, dict[int, int]],
    ) -> None:
        self.transpiled_program = transpiled_program
        self._stats = stats
        self.stats = self._nested_dict_accessor(stats)
        self._virtual_physical_mapping = virtual_physical_mapping
        self.virtual_physical_mapping = self._nested_dict_accessor(
            virtual_physical_mapping,
            stop_keys={"qubit_mapping", "bit_mapping"},
        )

    def __repr__(self) -> str:
        """Return a string representation of the TranspileResult.

        Returns:
            str: A string representation of the internal statistics dictionary.

        """
        return repr(self._stats)

    def __str__(self) -> str:
        """Return a string representation of the transpilation statistics.

        Returns:
            str: A string representation of the statistics dictionary.

        """
        return str(self._stats)

    def __eq__(self, other: object) -> bool:
        """Check equality with another TranspileResult object.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if the other object is a TranspileResult and all
            attributes (transpiled_program, _stats, _virtual_physical_mapping)
            are equal, False otherwise.

        """
        if not isinstance(other, TranspileResult):
            return False
        return (
            self.transpiled_program == other.transpiled_program
            and self._stats == other._stats
            and self._virtual_physical_mapping == other._virtual_physical_mapping
        )

    def __len__(self) -> int:
        """Return the number of statistical entries.

        Returns:
            int: The number of entries in the statistics dictionary.

        """
        return len(self._stats)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """Retrieve a value from the statistical information.

        Args:
            key (str): The key corresponding to the desired statistical information.

        Returns:
            Any: The value associated with the specified key
              in the statistical information.

        """
        return self._stats[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over the statistical information.

        Returns:
            An iterator over the keys of the statistical information dictionary.

        """
        return iter(self._stats)

    def __hash__(self) -> int:
        """Return a hash value for the TranspileResult.

        Returns:
            int: A hash value based on the transpiled program,
              stats, and virtual_physical_mapping.

        """
        return hash((
            self.transpiled_program,
            frozenset((k, frozenset(v.items())) for k, v in self._stats.items()),
            frozenset(
                (k, frozenset(v.items()))
                for k, v in self._virtual_physical_mapping.items()
            ),
        ))

    def to_dict(self) -> dict[str, Any]:
        """Convert the TranspileResult to a dictionary.

        Returns:
            dict[str, Any]: A dictionary representation of the TranspileResult,
            containing the statistical information and the virtual-physical
            qubit and bit mappings.

        """
        return {
            "stats": self._stats,
            "virtual_physical_mapping": self._virtual_physical_mapping,
        }

    @staticmethod
    def _nested_dict_accessor(
        d: dict, stop_keys: set[str] | None = None
    ) -> NestedDictAccessor:
        return NestedDictAccessor(d, stop_keys)

import pytest

from tranqu.program_type_manager import (
    ProgramLibraryAlreadyRegisteredError,
    ProgramTypeManager,
)


class DummyProgram:
    """Dummy program class for testing"""


class TestProgramTypeManager:
    @pytest.fixture
    def manager(self):
        return ProgramTypeManager()

    def test_register_type(self, manager: ProgramTypeManager):
        manager.register_type("dummy", DummyProgram)
        program = DummyProgram()

        result = manager.resolve_lib(program)

        assert result == "dummy"

    def test_resolve_lib_returns_none_for_unregistered_type(
        self, manager: ProgramTypeManager
    ):
        program = DummyProgram()

        result = manager.resolve_lib(program)

        assert result is None

    def test_resolve_lib_with_multiple_registrations(self, manager: ProgramTypeManager):
        class AnotherDummyProgram:
            pass

        manager.register_type("dummy1", DummyProgram)
        manager.register_type("dummy2", AnotherDummyProgram)

        program1 = DummyProgram()
        program2 = AnotherDummyProgram()

        assert manager.resolve_lib(program1) == "dummy1"
        assert manager.resolve_lib(program2) == "dummy2"

    def test_register_type_multiple_times(self, manager: ProgramTypeManager):
        manager.register_type("dummy", DummyProgram)
        manager.register_type("another_dummy", DummyProgram)

        program = DummyProgram()

        # The last registered library identifier is returned
        assert manager.resolve_lib(program) == "another_dummy"

    def test_register_type_raises_error_when_lib_already_registered(
        self, manager: ProgramTypeManager
    ):
        manager.register_type("dummy", DummyProgram)

        class AnotherProgram:
            pass

        with pytest.raises(
            ProgramLibraryAlreadyRegisteredError,
            match=(
                r"Library 'dummy' is already registered\. "
                r"Use allow_override=True to force registration\."
            ),
        ):
            manager.register_type("dummy", AnotherProgram)

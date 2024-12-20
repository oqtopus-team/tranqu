import pytest

from tranqu.program_type_manager import (
    ProgramLibraryAlreadyRegisteredError,
    ProgramTypeManager,
)


class DummyProgram:
    """Dummy program class for testing"""


class TestProgramTypeManager:
    def setup_method(self):
        self.manager = ProgramTypeManager()

    def test_register_type(self):
        self.manager.register_type("dummy", DummyProgram)
        program = DummyProgram()

        result = self.manager.detect_lib(program)

        assert result == "dummy"

    def test_detect_lib_returns_none_for_unregistered_type(self):
        program = DummyProgram()

        result = self.manager.detect_lib(program)

        assert result is None

    def test_detect_lib_with_multiple_registrations(self):
        class AnotherDummyProgram:
            pass

        self.manager.register_type("dummy1", DummyProgram)
        self.manager.register_type("dummy2", AnotherDummyProgram)

        program1 = DummyProgram()
        program2 = AnotherDummyProgram()

        assert self.manager.detect_lib(program1) == "dummy1"
        assert self.manager.detect_lib(program2) == "dummy2"

    def test_register_type_multiple_times(self):
        self.manager.register_type("dummy", DummyProgram)
        self.manager.register_type("another_dummy", DummyProgram)

        program = DummyProgram()

        # The last registered library identifier is returned
        assert self.manager.detect_lib(program) == "another_dummy"

    def test_register_type_raises_error_when_lib_already_registered(self):
        self.manager.register_type("dummy", DummyProgram)

        class AnotherProgram:
            pass

        with pytest.raises(
            ProgramLibraryAlreadyRegisteredError,
            match=(
                "Library 'dummy' is already registered. "
                "Use allow_override=True to force registration."
            ),
        ):
            (self.manager.register_type("dummy", AnotherProgram),)

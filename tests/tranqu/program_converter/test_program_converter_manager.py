from typing import Any

import pytest

from tranqu.program_converter import (
    PassThroughProgramConverter,
    ProgramConverter,
    ProgramConverterAlreadyRegisteredError,
    ProgramConverterManager,
    ProgramConverterNotFoundError,
)


class TestFooBarConverter(ProgramConverter):
    def convert(self, program: Any):
        return program


class BazToQuxConverter(ProgramConverter):
    def convert(self, program: Any):
        return program


class TestProgramConverterManager:
    def setup_method(self):
        self.manager = ProgramConverterManager()

    def test_fetch_converter(self):
        self.manager.register_converter("foo", "bar", TestFooBarConverter())

        converter = self.manager.fetch_converter("foo", "bar")

        assert isinstance(converter, TestFooBarConverter)

    def test_fetch_converter_not_found(self):
        with pytest.raises(ProgramConverterNotFoundError):
            self.manager.fetch_converter("baz", "qux")

    def test_register_converter(self):
        self.manager.register_converter("foo", "bar", TestFooBarConverter())

        converter = self.manager.fetch_converter("foo", "bar")

        assert isinstance(converter, TestFooBarConverter)

    def test_register_converter_twice(self):
        self.manager.register_converter("foo", "bar", TestFooBarConverter)

        with pytest.raises(
            ProgramConverterAlreadyRegisteredError,
            match=r"Converter already registered for conversion from foo to bar\.",
        ):
            self.manager.register_converter("foo", "bar", TestFooBarConverter)

    def test_register_pass_through_converter(self):
        self.manager.register_converter("foo", "foo", PassThroughProgramConverter)

        converter = self.manager.fetch_converter("foo", "foo")

        assert isinstance(converter, PassThroughProgramConverter)

    def test_register_converter_with_allow_override(self):
        converter1 = TestFooBarConverter()
        converter2 = BazToQuxConverter()

        self.manager.register_converter("foo", "bar", converter1)
        self.manager.register_converter("foo", "bar", converter2, allow_override=True)

        assert self.manager.fetch_converter("foo", "bar") == converter2

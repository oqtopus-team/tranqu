from tranqu.program_converter import PassThroughProgramConverter


class TestPassThroughProgramConverter:
    def setup_method(self):
        self.converter = PassThroughProgramConverter()

    def test_convert(self):
        program = "sample program"
        result = self.converter.convert(program)
        assert result == program

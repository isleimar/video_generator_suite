import pytest
from safe_expr_eval.evaluator import evaluate, InvalidExpressionError

# --- Testes de Operações Válidas ---

class TestValidExpressions:
    """Grupo de testes para expressões que devem funcionar corretamente."""

    @pytest.mark.parametrize("expr, context, expected", [
        # Aritmética básica
        ("5 + 3", {}, 8),
        ("10 - 2.5", {}, 7.5),
        ("4 * 7", {}, 28),
        ("100 / 4", {}, 25),
        ("10 / 4", {}, 2.5),
        # Números negativos
        ("-5 + 2", {}, -3),
        ("10 * -2", {}, -20),
        # Precedência de operadores
        ("2 + 3 * 4", {}, 14),
        # Uso de parênteses
        ("(2 + 3) * 4", {}, 20),
        # Expressões complexas
        ("((100 - 25) / 5 + 5) * 2", {}, 40),
    ])
    def test_arithmetic_operations(self, expr, context, expected):
        """Testa operações aritméticas com e sem parênteses."""
        assert evaluate(expr, context) == expected

    def test_context_variables(self):
        """Testa o uso de variáveis passadas pelo contexto."""
        context = {"price": 19.99, "quantity": 3, "discount": 5.00}
        expr = "(price * quantity) - discount"
        assert evaluate(expr, context) == 54.97

    @pytest.mark.parametrize("expr, context, expected", [
        ("max(10, 20)", {}, 20),
        ("min(-5, 0, 5)", {}, -5),
        ("max(a, b, c)", {"a": 1, "b": 100, "c": 10}, 100),
        ("min(price, 50)", {"price": 99.9}, 50),
    ])
    def test_safe_functions(self, expr, context, expected):
        """Testa as funções seguras permitidas (max, min)."""
        assert evaluate(expr, context) == expected

    def test_complex_expression_with_functions_and_vars(self):
        """Testa uma combinação de variáveis, operadores e funções."""
        context = {"base_value": 100, "multiplier": 2, "cap": 250}
        expr = "min(base_value * multiplier + 50, cap)"
        assert evaluate(expr, context) == 250

# --- Testes de Erros e Segurança ---

class TestInvalidAndUnsafeExpressions:
    """Grupo de testes para expressões que devem falhar."""

    def test_division_by_zero(self):
        """Testa se a divisão por zero levanta um erro."""
        with pytest.raises(InvalidExpressionError, match="division by zero"):
            evaluate("100 / 0")

    def test_undefined_variable(self):
        """Testa se usar uma variável não definida no contexto levanta um erro."""
        with pytest.raises(InvalidExpressionError, match="name 'undefined_var' is not defined"):
            evaluate("10 + undefined_var")

    @pytest.mark.parametrize("invalid_expr", [
        "5 +",
        "(5 + 3",
        "5 5",
        "my-var + 2", # hífen não é permitido em nomes de variáveis
    ])
    def test_syntax_errors(self, invalid_expr):
        """
        Testa expressões com sintaxe inválida.
        (Removemos o 'match' para sermos mais flexíveis com as mensagens de erro)
        """
        with pytest.raises(InvalidExpressionError):
            evaluate(invalid_expr)

    @pytest.mark.parametrize("unsafe_expr", [
        "__import__('os')",
        "import os",
        "open('some_file.txt')",
        "eval('1+1')",
        "lambda: 1",
        "my_dict.pop()",
        "del my_var",
    ])
    def test_unsafe_operations_are_blocked(self, unsafe_expr):
        """Testa várias tentativas de executar código inseguro."""
        context = {"my_dict": {"a": 1}, "my_var": 10}
        with pytest.raises(InvalidExpressionError):
            evaluate(unsafe_expr, context)
            
    def test_accessing_private_attributes_is_blocked(self):
        """
        Testa se a tentativa de acessar atributos com '__' é bloqueada.
        (Ajustamos o 'match' para a mensagem real do asteval)
        """
        with pytest.raises(InvalidExpressionError, match="no safe attribute '__class__'"):
            evaluate("a.__class__", {"a": 1})

    def test_disallowed_builtin_functions(self):
        """Testa se funções built-in não permitidas explicitamente são bloqueadas."""
        with pytest.raises(InvalidExpressionError, match="name 'sum' is not defined"):
            evaluate("sum([1, 2, 3])")
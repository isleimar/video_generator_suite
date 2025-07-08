from typing import Any, Dict
from asteval import Interpreter, get_ast_names

class InvalidExpressionError(Exception):
    """Exceção para expressões inválidas, inseguras ou que falharam na avaliação."""
    pass

def evaluate(expression: str, context: Dict[str, Any] = None) -> Any:
    """
    Avalia uma expressão matemática de forma segura usando um contexto.

    Esta função usa a biblioteca 'asteval' para criar um ambiente "sandbox"
    e previnir a execução de código malicioso.

    Args:
        expression: A string contendo a expressão a ser avaliada.
        context: Um dicionário com variáveis disponíveis para a expressão.

    Returns:
        O resultado da avaliação da expressão.

    Raises:
        InvalidExpressionError: Se a expressão for sintaticamente inválida,
                                usar nomes não definidos, ou tentar executar
                                operações inseguras.
    """
    if context is None:
        context = {}

    # Cria um interpretador seguro.
    # 'builtins_if_trusted=False' e 'use_builtin_funcs=False' são cruciais para a segurança.
    aeval = Interpreter(
        symtable=context, 
        builtins_if_trusted=False, 
        use_builtin_funcs=False
    )

    # Adicionamos manualmente apenas as funções que consideramos seguras.
    aeval.symtable['max'] = max
    aeval.symtable['min'] = min

    # Validação de segurança extra: verifica se a expressão tenta acessar atributos
    # que poderiam levar a vulnerabilidades (ex: __import__)
    try:
        names = get_ast_names(expression)
        for name in names:
            if name.startswith('_'):
                raise InvalidExpressionError(f"Acesso a atributos privados/mágicos ('{name}') não é permitido.")
    except Exception as exc:
        raise InvalidExpressionError(f"Erro de sintaxe na expressão: {exc}") from exc


    # Executa a avaliação
    try:
        result = aeval.eval(expression)
        return result
    except Exception as exc:
        # Captura qualquer erro durante a avaliação (divisão por zero, nome não encontrado, etc.)
        # e o encapsula em nossa exceção personalizada.
        raise InvalidExpressionError(f"Erro ao avaliar a expressão: {exc}") from exc
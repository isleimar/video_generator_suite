import ast
from typing import Any, Dict
from asteval import Interpreter

class InvalidExpressionError(Exception):
    """Exceção para expressões inválidas, inseguras ou que falharam na avaliação."""
    pass

def evaluate(expression: str, context: Dict[str, Any] = None) -> Any:
    """
    Avalia uma expressão matemática de forma segura usando um contexto,
    com validação de sintaxe e de execução.
    """
    if context is None:
        context = {}

    # --- CAMADA 1: Pré-validação de Sintaxe com compile() ---
    # Bloqueia 'statements' (del, import) e erros de sintaxe grosseiros.
    try:
        compile(expression, '<string>', 'eval')
    except (SyntaxError, TypeError, ValueError) as exc:
        raise InvalidExpressionError(f"Expressão ou sintaxe inválida: {exc}") from exc

    # --- CAMADA 2: Avaliação Segura e Verificação de Erros com Asteval ---
    aeval = Interpreter(
        symtable=context.copy(),
        builtins_if_trusted=False,
        use_builtin_funcs=False
    )
    aeval.symtable.update({'max': max, 'min': min})

    # A avaliação é feita, e então o buffer de erros é verificado.
    result = aeval.eval(expression)

    if aeval.error:
        # Se o asteval encontrou um erro de execução (ex: NameError, ZeroDivisionError),
        # pegamos a mensagem e levantamos nossa exceção.
        last_error = aeval.error[-1]
        raise InvalidExpressionError(last_error.msg) from last_error.exc
            
    return result
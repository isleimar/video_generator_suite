import re
import copy
from graphlib import TopologicalSorter, CycleError
from typing import Dict, Any, List, Set, Tuple

from video_model.models import Project, BaseElement
from safe_expr_eval.evaluator import evaluate, InvalidExpressionError

class ResolverError(Exception):
    pass

class CircularDependencyError(ResolverError):
    pass

class AttributeReferenceError(ResolverError):
    pass

class Resolver:
    def __init__(self, project: Project):
        if not isinstance(project, Project):
            raise TypeError("O objeto fornecido ao Resolver deve ser do tipo Project.")
        
        self.raw_project = project
        self.resolved_project = copy.deepcopy(project)
        self.graph = TopologicalSorter()
        self.resolved_values: Dict[str, Any] = {}
        self.ref_pattern = re.compile(r'([a-zA-Z_][a-zA-Z_0-9]*\.[a-zA-Z_][a-zA-Z_0-9]*)')

    def resolve(self) -> Project:
        self._build_dependency_graph()
        self._calculate_resolved_values()
        return self.resolved_project

    def _get_node_name(self, owner_name: str, attr: str) -> str:
        return f"{owner_name}.{attr}"

    def _build_dependency_graph(self):
        # (Este método permanece o mesmo da versão anterior)
        all_elements = {el.name: el for el in self.resolved_project.elements if el.name}
        attributes_to_scan: List[Tuple[str, object, str]] = []
        for attr in ['width', 'height', 'duration']:
            attributes_to_scan.append(('video', self.resolved_project, attr))
        for el_name, element in all_elements.items():
            for attr in ['start', 'end', 'x', 'y', 'width', 'height', 'opacity', 'rotation']:
                attributes_to_scan.append((el_name, element, attr))

        for owner_name, owner_obj, attr in attributes_to_scan:
            node_name = self._get_node_name(owner_name, attr)
            value = getattr(owner_obj, attr, None)
            
            if isinstance(value, str) and value.startswith('expr:'):
                expression = value[5:].strip()
                dependencies = self._find_dependencies(expression, owner_name)
                self.graph.add(node_name, *dependencies)
            else:
                self.graph.add(node_name)
                self.resolved_values[node_name] = value

    def _find_dependencies(self, expression: str, current_element_name: str) -> Set[str]:
        # (Este método permanece o mesmo da versão anterior)
        raw_refs = self.ref_pattern.findall(expression)
        dependencies = set()
        safe_functions = {'max', 'min'}
        for ref in raw_refs:
            if ref in safe_functions:
                continue
            if ref.startswith('self.'):
                dep_name = ref.replace('self', current_element_name, 1)
                dependencies.add(dep_name)
            else:
                dependencies.add(ref)
        return dependencies

    def _calculate_resolved_values(self):
        try:
            sorted_nodes = list(self.graph.static_order())
        except CycleError as e:
            cycle = " -> ".join(e.args[1])
            raise CircularDependencyError(f"Dependência circular detectada: {cycle}") from e

        for node_name in sorted_nodes:
            if node_name in self.resolved_values:
                continue
            
            owner_name, attr = node_name.split('.', 1)
            owner_obj = self._get_owner_obj(owner_name)
            expression_str = getattr(owner_obj, attr)
            expression = expression_str[5:].strip()

            context, transformed_expression = self._build_context_and_transform_expr(expression, owner_name)
            
            try:
                resolved_value = evaluate(transformed_expression, context)
            except InvalidExpressionError as e:
                raise ResolverError(f"Erro na expressão para '{node_name}': {e}") from e

            self.resolved_values[node_name] = resolved_value
            setattr(owner_obj, attr, resolved_value)

    def _get_owner_obj(self, owner_name: str) -> Any:
        """Busca o objeto dono de um atributo (Project ou um BaseElement)."""
        if owner_name == 'video':
            return self.resolved_project
        try:
            return next(el for el in self.resolved_project.elements if el.name == owner_name)
        except StopIteration:
            raise AttributeReferenceError(f"Elemento '{owner_name}' referenciado em uma expressão não foi encontrado.")

    def _build_context_and_transform_expr(self, expression: str, current_element_name: str) -> Tuple[Dict[str, Any], str]:
        """
        Cria o contexto e transforma a expressão para usar chaves de contexto achatadas.
        Ex: 'self.width' e 'video.width' são transformados para 'self_width' e 'video_width'.
        Também verifica se alguma dependência tem o valor None.
        """
        context = {}
        transformed_expression = expression
        
        # Encontra todas as referências originais na expressão (ex: 'self.width')
        original_refs = self._find_raw_refs(expression)

        for ref in original_refs:
            # Converte a referência para um nome de nó concreto (ex: 'self.width' -> 'logo.width')
            node_name = ref.replace('self', current_element_name, 1)
            
            if node_name not in self.resolved_values:
                raise ResolverError(f"Dependência '{node_name}' não foi resolvida a tempo para a expressão '{expression}'.")

            resolved_value = self.resolved_values[node_name]
            
            # **NOVA VERIFICAÇÃO**: Garante que não estamos usando um valor Nulo em cálculos.
            if resolved_value is None:
                raise AttributeReferenceError(
                    f"Atributo '{node_name}' referenciado na expressão '{expression}' não foi definido ou não tem valor."
                )
            
            # Cria uma chave segura para o contexto (ex: 'self_width')
            context_key = ref.replace('.', '_')
            context[context_key] = resolved_value
            
            # Substitui a referência original na expressão pela chave segura
            transformed_expression = transformed_expression.replace(ref, context_key)
            
        return context, transformed_expression

    def _find_raw_refs(self, expression: str) -> Set[str]:
        """Encontra as referências brutas, incluindo 'self'."""
        refs = self.ref_pattern.findall(expression)
        safe_functions = {'max', 'min'}
        return {ref for ref in refs if ref not in safe_functions}
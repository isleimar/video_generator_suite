import re
import copy
from graphlib import TopologicalSorter, CycleError
from typing import Dict, Any, List, Set, Tuple

# Importações dos nossos outros pacotes
from video_model.models import Project, BaseElement
from safe_expr_eval.evaluator import evaluate, InvalidExpressionError

# --- Exceções Específicas do Módulo ---

class ResolverError(Exception):
    """Classe base para erros durante a resolução da timeline."""
    pass

class CircularDependencyError(ResolverError):
    """Levantada quando uma dependência circular é detectada."""
    pass

class AttributeReferenceError(ResolverError):
    """Levantada quando uma referência em uma expressão não pode ser encontrada."""
    pass


class Resolver:
    """
    Resolve uma estrutura de projeto com atributos dinâmicos ('expr:')
    para uma estrutura com valores numéricos concretos.
    """

    def __init__(self, project: Project):
        """
        Inicializa o resolver com o projeto bruto.

        Args:
            project: O objeto Project carregado do YAML, contendo expressões.
        """
        if not isinstance(project, Project):
            raise TypeError("O objeto fornecido ao Resolver deve ser do tipo Project.")
        
        # Trabalhamos em uma cópia profunda para não modificar o objeto original
        self.project = copy.deepcopy(project)
        self.graph = TopologicalSorter()
        # Mapeia um nó do grafo (ex: 'element.my_logo.width') para seu valor resolvido
        self.resolved_values: Dict[str, Any] = {}
        # Regex para encontrar referências no formato 'objeto.atributo'
        self.ref_pattern = re.compile(r'([a-zA-Z_][a-zA-Z_0-9]*\.[a-zA-Z_][a-zA-Z_0-9]*)')

    def resolve(self) -> Project:
        """
        Orquestra o processo completo de resolução da timeline.

        Returns:
            Um novo objeto Project com todos os atributos dinâmicos calculados.
        """
        print("Iniciando resolução de dependências...")
        self._build_dependency_graph()
        print("Grafo de dependências construído. Calculando valores...")
        self._calculate_resolved_values()
        print("Resolução concluída.")
        return self.project

    def _get_node_name(self, element_name: str, attr: str) -> str:
        """Cria um nome de nó único e consistente."""
        return f"{element_name}.{attr}"

    def _build_dependency_graph(self):
        """
        Varre todo o projeto, encontra expressões e constrói o grafo de dependências.
        """
        all_elements = {el.name: el for el in self.project.elements if el.name}
        
        # --- Passo 1: Adicionar todos os atributos como nós no grafo ---
        attributes_to_scan: List[Tuple[str, object, str]] = []

        # Adicionar atributos globais do vídeo
        for attr in ['width', 'height', 'duration']:
            attributes_to_scan.append(('video', self.project, attr))

        # Adicionar atributos de cada elemento
        for el_name, element in all_elements.items():
            for attr in ['start', 'end', 'x', 'y', 'width', 'height', 'opacity', 'rotation']:
                attributes_to_scan.append((el_name, element, attr))

        # --- Passo 2: Analisar cada atributo e adicionar suas dependências ---
        for owner_name, owner_obj, attr in attributes_to_scan:
            node_name = self._get_node_name(owner_name, attr)
            value = getattr(owner_obj, attr, None)
            
            if isinstance(value, str) and value.startswith('expr:'):
                expression = value[5:].strip()
                dependencies = self._find_dependencies(expression, owner_name)
                self.graph.add(node_name, *dependencies)
            else:
                # É um valor estático, não tem dependências. Adiciona ao grafo para garantir que exista.
                self.graph.add(node_name)
                # Valores estáticos podem ser "resolvidos" imediatamente.
                self.resolved_values[node_name] = value

    def _find_dependencies(self, expression: str, current_element_name: str) -> Set[str]:
        """Encontra todas as dependências em uma string de expressão."""
        found_refs = self.ref_pattern.findall(expression)
        dependencies = set()
        for ref in found_refs:
            if ref.startswith('self.'):
                # Substitui 'self' pelo nome do elemento atual
                dep_name = ref.replace('self', current_element_name, 1)
                dependencies.add(dep_name)
            else:
                dependencies.add(ref)
        return dependencies

    def _calculate_resolved_values(self):
        """
        Executa a ordenação topológica e calcula cada valor na ordem correta.
        """
        try:
            # Prepara o grafo e detecta ciclos de uma vez
            sorted_nodes_generator = self.graph.static_order()
        except CycleError as e:
            # Formata a mensagem de erro para ser mais legível
            cycle = " -> ".join(e.args[1])
            raise CircularDependencyError(f"Dependência circular detectada: {cycle}") from e

        # Itera sobre os nós na ordem correta
        for node_name in sorted_nodes_generator:
            if node_name in self.resolved_values:
                # Valor estático, já resolvido. Pula.
                continue
            
            owner_name, attr = node_name.split('.', 1)

            # Encontra o objeto e a expressão
            if owner_name == 'video':
                owner_obj = self.project
            else:
                # Encontra o elemento pelo nome
                try:
                    owner_obj = next(el for el in self.project.elements if el.name == owner_name)
                except StopIteration:
                    raise AttributeReferenceError(f"Elemento '{owner_name}' referenciado em uma expressão não foi encontrado.")

            expression_str = getattr(owner_obj, attr)
            expression = expression_str[5:].strip()

            # Constrói o contexto para a avaliação
            context = self._build_evaluation_context(expression, owner_name)
            
            # Avalia a expressão
            try:
                resolved_value = evaluate(expression, context)
            except InvalidExpressionError as e:
                raise ResolverError(f"Erro na expressão para '{node_name}': {e}") from e

            # Armazena o valor resolvido e atualiza o objeto no modelo
            self.resolved_values[node_name] = resolved_value
            setattr(owner_obj, attr, resolved_value)

    def _build_evaluation_context(self, expression: str, current_element_name: str) -> Dict[str, Any]:
        """Cria o dicionário de contexto com os valores das dependências."""
        context = {}
        dependencies = self._find_dependencies(expression, current_element_name)

        for dep_name in dependencies:
            if dep_name not in self.resolved_values:
                # Isso não deveria acontecer se a ordenação topológica estiver correta
                raise ResolverError(f"Dependência '{dep_name}' não resolvida a tempo para '{expression}'. Verifique a lógica do grafo.")

            # Mapeia a referência completa (ex: 'logo.width') para a chave no contexto
            context_key = dep_name.replace('.', '_') # Chave segura para o contexto
            context[context_key] = self.resolved_values[dep_name]
        
        # Adiciona o próprio objeto 'self' e 'video' ao contexto
        # Aqui, estamos adicionando apenas os valores já resolvidos
        # A expressão em si deve usar o formato `elemento_atributo`
        # Ex: "expr: self_width / 2" após o pré-processamento para o motor de avaliação.
        # A biblioteca `asteval` lida com o formato `obj.attr` se passarmos o objeto
        # mas por segurança, passamos apenas os valores primitivos.
        # Esta é uma área que pode ser otimizada dependendo do motor de expressão.
        
        return context
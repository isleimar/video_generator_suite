import pytest
import copy

from video_model.models import Project, VideoElement, ImageElement
from timeline_resolver.resolver import Resolver, CircularDependencyError, AttributeReferenceError, ResolverError

# --- Casos de Teste para o Resolver ---

class TestTimelineResolver:
    """Conjunto de testes exaustivo para a classe Resolver."""

    def test_resolve_project_with_no_expressions(self):
        """
        Garante que um projeto com apenas valores estáticos seja resolvido sem alterações.
        """
        elements = [
            VideoElement(name="vid1", start=0, end=10, width=1280, height=720)
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        
        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.duration == 10
        assert resolved_project.elements[0].end == 10

    def test_resolve_simple_expression_without_dependencies(self):
        """Testa uma expressão simples que não depende de outros atributos."""
        project = Project(width=1920, height=1080, duration="expr: 15.5 * 2")
        
        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.duration == 31.0

    def test_resolve_dependency_on_video_attribute(self):
        """Testa uma expressão que depende de um atributo global do vídeo."""
        elements = [
            ImageElement(name="logo", x="expr: video.width - 100", start=0, end=5)
        ]
        project = Project(width=1920, height=1080, duration=5, elements=elements)
        
        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.elements[0].x == 1820

    def test_resolve_dependency_between_elements(self):
        """Testa uma expressão que depende do atributo de outro elemento."""
        elements = [
            VideoElement(name="intro", start=0, end=10),
            VideoElement(name="main", start="expr: intro.end + 2", end=30)
        ]
        project = Project(width=1280, height=720, duration=30, elements=elements)

        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.elements[1].start == 12

    def test_resolve_dependency_on_self(self):
        """Testa uma expressão que usa 'self' para se referir ao próprio elemento."""
        elements = [
            ImageElement(name="logo", width=200, x="expr: (1920 - self.width) / 2", start=0, end=10)
        ]
        project = Project(width=1920, height=1080, duration=10, elements=elements)
        
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        
        assert resolved_project.elements[0].x == (1920 - 200) / 2

    def test_resolve_chained_dependencies(self):
        """Testa uma cadeia de dependências: C depende de B, que depende de A."""
        elements = [
            VideoElement(name="A", start=0, end=5),
            VideoElement(name="B", start="expr: A.end", end="expr: self.start + 10"), # end = 15
            VideoElement(name="C", start="expr: B.end + 5") # start = 20
        ]
        project = Project(width=1280, height=720, duration=30, elements=elements)

        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.elements[2].start == 20

    def test_resolve_complex_expression_with_function(self):
        """Testa uma expressão complexa com a função max() e múltiplas dependências."""
        elements = [
            VideoElement(name="track1", start=0, end=15),
            VideoElement(name="track2", start=5, end=30),
            ImageElement(name="logo", start="expr: min(track1.start, track2.start)")
        ]
        project = Project(
            width=1280, height=720, 
            duration="expr: max(track1.end, track2.end)", 
            elements=elements
        )

        resolver = Resolver(project)
        resolved_project = resolver.resolve()

        assert resolved_project.duration == 30
        assert resolved_project.elements[2].start == 0

    def test_immutability_of_original_project(self):
        """Garante que o objeto de projeto original não seja modificado."""
        elements = [VideoElement(name="vid", start=0, end="expr: 10 + 5")]
        original_project = Project(width=1280, height=720, duration=20, elements=elements)
        # Cria uma cópia para garantir que o original não mude
        project_to_compare = copy.deepcopy(original_project)

        resolver = Resolver(original_project)
        resolver.resolve()

        # Verifica se o objeto original permanece inalterado
        assert original_project.elements[0].end == "expr: 10 + 5"
        assert original_project == project_to_compare


    # --- Testes de Detecção de Erros ---

    def test_simple_circular_dependency_raises_error(self):
        """Testa se uma dependência circular direta (A -> B -> A) levanta um erro."""
        elements = [
            VideoElement(name="A", start="expr: B.start"),
            VideoElement(name="B", start="expr: A.start")
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        
        with pytest.raises(CircularDependencyError) as excinfo:
            resolver.resolve()
        
        # Verifica se a mensagem de erro contém o ciclo
        assert "A.start" in str(excinfo.value)
        assert "B.start" in str(excinfo.value)

    def test_self_referential_circular_dependency_raises_error(self):
        """Testa se uma dependência circular em 'self' (A.start -> A.end -> A.start) é detectada."""
        elements = [
            VideoElement(name="A", start="expr: self.end", end="expr: self.start + 10")
        ]
        project = Project(width=1280, height=720, duration=20, elements=elements)
        resolver = Resolver(project)

        with pytest.raises(CircularDependencyError):
            resolver.resolve()
            
    def test_longer_circular_dependency_chain_raises_error(self):
        """Testa um ciclo mais longo (A -> B -> C -> A)."""
        elements = [
            VideoElement(name="A", start="expr: C.end"),
            VideoElement(name="B", start="expr: A.start"),
            VideoElement(name="C", end="expr: B.start"),
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        
        with pytest.raises(CircularDependencyError):
            resolver.resolve()

    def test_undefined_element_reference_raises_error(self):
        """Testa se uma referência a um elemento que não existe levanta um erro."""
        elements = [
            VideoElement(name="A", start="expr: NON_EXISTENT.end")
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        
        # O erro é pego quando tentamos acessar o objeto dono do atributo
        with pytest.raises(AttributeReferenceError, match="Elemento 'NON_EXISTENT' referenciado em uma expressão não foi encontrado."):
            resolver.resolve()

    def test_undefined_attribute_reference_raises_error(self):
        """Testa se uma referência a um atributo que não existe levanta um erro."""
        elements = [
            VideoElement(name="A"),
            VideoElement(name="B", start="expr: A.non_existent_attribute")
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)

        # O erro vem do 'safe_expr_eval' e é encapsulado pelo Resolver
        with pytest.raises(ResolverError, match="name 'A_non_existent_attribute' is not defined"):
            resolver.resolve()
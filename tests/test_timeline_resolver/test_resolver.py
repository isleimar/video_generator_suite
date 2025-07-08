import pytest
import copy

from video_model.models import Project, VideoElement, ImageElement
from timeline_resolver.resolver import Resolver, CircularDependencyError, AttributeReferenceError, ResolverError

class TestTimelineResolver:
    def test_resolve_project_with_no_expressions(self):
        elements = [VideoElement(name="vid1", start=0, path="dummy.mp4", end=10, width=1280, height=720)]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.duration == 10
        assert resolved_project.elements[0].end == 10

    def test_resolve_simple_expression_without_dependencies(self):
        project = Project(width=1920, height=1080, duration="expr: 15.5 * 2")
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.duration == 31.0

    def test_resolve_dependency_on_video_attribute(self):
        elements = [ImageElement(name="logo", start=0, path="dummy.png", x="expr: video.width - 100", end=5)]
        project = Project(width=1920, height=1080, duration=5, elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.elements[0].x == 1820

    def test_resolve_dependency_between_elements(self):
        elements = [
            VideoElement(name="intro", start=0, path="v1.mp4", end=10),
            VideoElement(name="main", start="expr: intro.end + 2", path="v2.mp4", end=30)
        ]
        project = Project(width=1280, height=720, duration=30, elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.elements[1].start == 12

    def test_resolve_dependency_on_self(self):
        elements = [ImageElement(name="logo", start=0, path="l.png", width=200, x="expr: (1920 - self.width) / 2", end=10)]
        project = Project(width=1920, height=1080, duration=10, elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.elements[0].x == (1920 - 200) / 2

    def test_resolve_chained_dependencies(self):
        elements = [
            VideoElement(name="A", start=0, path="a.mp4", end=5),
            VideoElement(name="B", start="expr: A.end", path="b.mp4", end="expr: self.start + 10"),
            VideoElement(name="C", start="expr: B.end + 5", path="c.mp4")
        ]
        project = Project(width=1280, height=720, duration=30, elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.elements[2].start == 20

    def test_resolve_complex_expression_with_function(self):
        elements = [
            VideoElement(name="track1", start=0, path="t1.mp4", end=15),
            VideoElement(name="track2", start=5, path="t2.mp4", end=30),
            ImageElement(name="logo", start="expr: min(track1.start, track2.start)", path="l.png")
        ]
        project = Project(width=1280, height=720, duration="expr: max(track1.end, track2.end)", elements=elements)
        resolver = Resolver(project)
        resolved_project = resolver.resolve()
        assert resolved_project.duration == 30
        assert resolved_project.elements[2].start == 0

    def test_immutability_of_original_project(self):
        elements = [VideoElement(name="vid", start=0, path="v.mp4", end="expr: 10 + 5")]
        original_project = Project(width=1280, height=720, duration=20, elements=elements)
        project_to_compare = copy.deepcopy(original_project)
        resolver = Resolver(original_project)
        resolver.resolve()
        assert original_project.elements[0].end == "expr: 10 + 5"
        assert original_project == project_to_compare

    def test_simple_circular_dependency_raises_error(self):
        elements = [
            VideoElement(name="A", start="expr: B.start", path="a.mp4"),
            VideoElement(name="B", start="expr: A.start", path="b.mp4")
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        with pytest.raises(CircularDependencyError) as excinfo:
            resolver.resolve()
        assert "A.start" in str(excinfo.value)
        assert "B.start" in str(excinfo.value)

    def test_self_referential_circular_dependency_raises_error(self):
        elements = [VideoElement(name="A", start="expr: self.end", path="a.mp4", end="expr: self.start + 10")]
        project = Project(width=1280, height=720, duration=20, elements=elements)
        resolver = Resolver(project)
        with pytest.raises(CircularDependencyError):
            resolver.resolve()
            
    def test_longer_circular_dependency_chain_raises_error(self):
        elements = [
            VideoElement(name="A", start="expr: C.end", path="a.mp4"),
            VideoElement(name="B", start="expr: A.start", path="b.mp4"),
            VideoElement(name="C", start=0, path="c.mp4", end="expr: B.start"), # Adicionado start=0 que faltava
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        with pytest.raises(CircularDependencyError):
            resolver.resolve()

    def test_undefined_element_reference_raises_error(self):
        elements = [VideoElement(name="A", start="expr: NON_EXISTENT.end", path="a.mp4")]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        with pytest.raises(AttributeReferenceError, match="Elemento 'NON_EXISTENT' referenciado em uma expressão não foi encontrado."):
            resolver.resolve()

    def test_undefined_attribute_reference_raises_error(self):
        """Testa se uma referência a um atributo que é None levanta um erro."""
        elements = [
            VideoElement(name="A", start=0, path="a.mp4"), # 'end' é None por padrão
            VideoElement(name="B", start="expr: A.end", path="b.mp4")
        ]
        project = Project(width=1280, height=720, duration=10, elements=elements)
        resolver = Resolver(project)
        
        # CORREÇÃO: O teste agora espera o erro correto (AttributeReferenceError)
        # com a mensagem correta.
        with pytest.raises(AttributeReferenceError, match="Atributo 'A.end' referenciado na expressão 'A.end' não foi definido ou não tem valor."):
            resolver.resolve()
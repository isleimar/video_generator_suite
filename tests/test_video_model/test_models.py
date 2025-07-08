import pytest
from video_model.models import (
    Project, BaseElement, ImageElement, VideoElement, TextElement, RectangleElement,
    KW_ONLY
)

# --- Testes para a Instanciação Direta das Classes ---

class TestElementInstantiation:
    """Verifica a criação direta de objetos de elemento e a aplicação de regras de construtor."""

    def test_image_element_creation_with_all_args(self):
        """Testa se um ImageElement pode ser criado com argumentos posicionais e nomeados."""
        img = ImageElement(
            name="logo",
            start=5,
            type="image",
            path="images/logo.png",
            end=15,
            x=100,
            opacity=0.8
        )
        assert img.name == "logo"
        assert img.start == 5
        assert img.path == "images/logo.png"
        assert img.end == 15
        assert img.x == 100
        assert img.opacity == 0.8
        # Testa se um valor padrão não especificado está correto
        assert img.y == 0

    def test_rectangle_element_uses_defaults(self):
        """Testa se um RectangleElement usa seus valores padrão corretamente."""
        rect = RectangleElement(
            name="background",
            start=0,
            type="rectangle", # 'type' é posicional
            # Todos os outros são nomeados
            end=10
        )
        assert rect.color == "#FFFFFF"
        assert rect.corner_radius == 0
        assert rect.type == "rectangle"

    def test_missing_required_positional_argument_raises_error(self):
        """Testa se a falta de um argumento posicional (ex: start) levanta TypeError."""
        with pytest.raises(TypeError):
            # 'start' está faltando
            ImageElement(name="logo", type="image", path="images/logo.png")

    def test_missing_required_keyword_only_argument_raises_error(self):
        """Testa se a falta de um argumento nomeado obrigatório (ex: path) levanta TypeError."""
        with pytest.raises(TypeError):
            # 'path' está faltando para ImageElement
            ImageElement(name="logo", start=0, type="image")
            
    def test_passing_keyword_arg_as_positional_raises_error(self):
        """Testa se tentar passar um argumento nomeado por posição levanta TypeError."""
        with pytest.raises(TypeError):
            # O 'end=10' deveria ser passado com a chave, pois vem depois de KW_ONLY
            BaseElement("name", 0, "type", 10)


# --- Testes para o Método de Fábrica `Project.from_dict` ---

class TestProjectFromDictFactory:
    """Verifica a lógica de construção do projeto a partir de um dicionário."""

    def test_from_dict_creates_all_element_types_correctly(self):
        """Testa se o factory pode criar um projeto com um elemento de cada tipo."""
        test_data = {
            "width": 1920, "height": 1080, "duration": 60,
            "elements": [
                {"name": "img1", "start": 0, "type": "image", "path": "a.png"},
                {"name": "vid1", "start": 10, "type": "video", "path": "b.mp4"},
                {"name": "txt1", "start": 20, "type": "text", "text": "Hello"},
                {"name": "rect1", "start": 30, "type": "rectangle"},
            ]
        }
        project = Project.from_dict(test_data)
        assert isinstance(project, Project)
        assert len(project.elements) == 4
        assert isinstance(project.elements[0], ImageElement)
        assert isinstance(project.elements[1], VideoElement)
        assert isinstance(project.elements[2], TextElement)
        assert isinstance(project.elements[3], RectangleElement)
        assert project.elements[1].name == "vid1"
        assert project.elements[2].text == "Hello"

    def test_from_dict_applies_defaults_for_omitted_fields(self):
        """Testa se os valores padrão são aplicados ao criar de um dicionário."""
        test_data = {
            "width": 1280, "height": 720, "duration": 10,
            "elements": [
                # Este elemento tem apenas os campos obrigatórios
                {"name": "logo", "start": 0, "type": "image", "path": "logo.png"}
            ]
        }
        project = Project.from_dict(test_data)
        logo_element = project.elements[0]
        
        assert logo_element.x == 0
        assert logo_element.y == 0
        assert logo_element.opacity == 1.0
        assert logo_element.end is None

    def test_from_dict_loads_expressions_as_strings(self):
        """Garante que o factory carrega expressões como strings, sem avaliá-las."""
        test_data = {
            "width": 1920, "height": 1080, "duration": "expr: track.end",
            "elements": [
                {"name": "track", "start": 0, "type": "video", "path": "v.mp4", "end": 30},
                {"name": "title", "start": "expr: track.start + 1", "type": "text", "text": "Title"}
            ]
        }
        project = Project.from_dict(test_data)
        
        assert project.duration == "expr: track.end"
        assert project.elements[1].start == "expr: track.start + 1"
        
    def test_from_dict_with_unknown_element_type_raises_value_error(self):
        """Testa se um 'type' de elemento desconhecido levanta um ValueError."""
        test_data = {"width": 10, "height": 10, "duration": 1, "elements": [
            {"name": "bad", "start": 0, "type": "circle"}
        ]}
        
        with pytest.raises(ValueError, match="Tipo de elemento desconhecido ou não especificado: circle"):
            Project.from_dict(test_data)
            
    def test_from_dict_with_missing_element_type_raises_value_error(self):
        """Testa se a ausência da chave 'type' em um elemento levanta um ValueError."""
        test_data = {"width": 10, "height": 10, "duration": 1, "elements": [
            {"name": "bad", "start": 0} # 'type' está faltando
        ]}

        with pytest.raises(ValueError, match="Tipo de elemento desconhecido ou não especificado: None"):
            Project.from_dict(test_data)

    def test_from_dict_with_missing_required_field_raises_type_error(self):
        """Testa se a ausência de um campo obrigatório (ex: path) levanta TypeError."""
        test_data = {"width": 10, "height": 10, "duration": 1, "elements": [
            # ImageElement requer 'path', que está faltando
            {"name": "bad_image", "start": 0, "type": "image"}
        ]}

        with pytest.raises(TypeError):
            Project.from_dict(test_data)
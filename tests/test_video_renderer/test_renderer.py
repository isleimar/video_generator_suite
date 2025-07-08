import pytest
from unittest.mock import MagicMock, patch

from video_model.models import Project, ImageElement, VideoElement, RectangleElement, TextElement
from video_renderer.renderer import Renderer

# --- Fixtures ---

@pytest.fixture
def project_with_image():
    """Cria um projeto com um elemento de imagem para testes."""
    elements = [
        ImageElement(name="logo", start=2, path="logo.png", width=200, height=100)
    ]
    return Project(width=1920, height=1080, duration=10, elements=elements)

@pytest.fixture
def project_with_rectangle():
    """Cria um projeto com um elemento de retângulo para testes."""
    elements = [
        RectangleElement(name="bg", start=0, width=800, height=600, color="#FF0000")
    ]
    return Project(width=1920, height=1080, duration=10, elements=elements)


@pytest.fixture
def project_with_text():
    """Cria um projeto com um elemento de texto para testes."""
    font_spec = {
        "path": "Arial.ttf",
        "size": 72,
        "color": "#FFFFFF",
        "stroke": {"color": "black", "width": 2}
    }
    elements = [
        TextElement(name="title", start=1, text="Hello World", font=font_spec)
    ]
    return Project(width=1920, height=1080, duration=10, elements=elements)

@pytest.fixture
def project_with_video():
    """Cria um projeto com um elemento de vídeo para testes."""
    elements = [
        VideoElement(name="trailer", start=5, path="trailer.mp4", width=1280, height=720, volume=0.7)
    ]
    return Project(width=1920, height=1080, duration=30, elements=elements)


# --- Classe de Testes ---

class TestRenderer:
    # MUDANÇA: Patch direto na classe que queremos simular
    @patch('video_renderer.renderer.ImageClip')
    def test_create_image_clip_calls_moviepy_correctly(self, mock_image_clip, project_with_image):
        """Testa a criação de um clipe de imagem."""
        mock_instance = MagicMock()
        mock_image_clip.return_value = mock_instance

        renderer = Renderer(project_with_image)
        image_element = project_with_image.elements[0]
        
        renderer._create_image_clip(image_element)

        mock_image_clip.assert_called_once_with("logo.png")
        # MUDANÇA: .resize se torna .resized
        mock_instance.resized.assert_called_once_with(width=200, height=100)

    # MUDANÇA: Patch direto na classe que queremos simular
    @patch('video_renderer.renderer.TextClip')
    def test_create_text_clip_calls_moviepy_correctly(self, mock_text_clip, project_with_text):
        """Testa a criação de um clipe de texto."""
        renderer = Renderer(project_with_text)
        text_element = project_with_text.elements[0]

        renderer._create_text_clip(text_element)

        # Verifica se TextClip foi chamado com os parâmetros corretos
        mock_text_clip.assert_called_once_with(
            txt="Hello World",
            font="Arial.ttf",
            fontsize=72,
            color="FFFFFF", # Verifica se o '#' foi removido
            stroke_color="black",
            stroke_width=2
        )
import pytest
from unittest.mock import MagicMock, patch

from video_model.models import Project, ImageElement, VideoElement, RectangleElement
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
    @patch('video_renderer.renderer.VideoFileClip')
    def test_create_video_clip_calls_moviepy_correctly(self, mock_video_clip, project_with_video):
        """Testa a criação de um clipe de vídeo com volume e resize."""
        mock_instance = MagicMock()
        mock_instance.volumex.return_value = mock_instance
        mock_video_clip.return_value = mock_instance

        renderer = Renderer(project_with_video)
        video_element = project_with_video.elements[0]

        renderer._create_video_clip(video_element)

        mock_video_clip.assert_called_once_with("trailer.mp4")
        mock_instance.volumex.assert_called_once_with(0.7)
        # MUDANÇA: .resize se torna .resized
        mock_instance.resized.assert_called_once_with(width=1280, height=720)
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
    
    @patch('video_renderer.renderer.CompositeVideoClip')
    @patch('video_renderer.renderer.ColorClip')
    def test_render_video_orchestrates_correctly(self, mock_color_clip, mock_composite_clip, project_with_video):
        """
        Testa se render_video orquestra a criação do canvas, elementos e composição final.
        """
        # Prepara os mocks
        mock_canvas_instance = MagicMock()
        mock_color_clip.return_value = mock_canvas_instance

        # --- A LINHA DA CORREÇÃO ESTÁ AQUI ---
        # Dizemos ao mock do canvas para ter um atributo 'size' com o valor correto.
        mock_canvas_instance.size = (project_with_video.width, project_with_video.height)

        mock_final_clip_instance = MagicMock()
        mock_composite_clip.return_value = mock_final_clip_instance
        
        renderer = Renderer(project_with_video)
        
        # Mock para o método interno para não re-testar a criação de clipes
        mock_element_clip = MagicMock()
        renderer._create_clip_for_element = MagicMock(return_value=mock_element_clip)

        # Executa o método principal
        renderer.render_video("output.mp4", fps=30)

        # 1. Verifica se o canvas foi criado com os parâmetros corretos
        mock_color_clip.assert_called_once_with(
            size=(project_with_video.width, project_with_video.height),
            color=project_with_video.background_color,
            duration=project_with_video.duration
        )

        # 2. Verifica se a criação de clipes foi chamada para o nosso elemento
        renderer._create_clip_for_element.assert_called_once_with(project_with_video.elements[0])
        
        # 3. Verifica se a composição final foi criada com o canvas e o clipe do elemento
        mock_composite_clip.assert_called_once_with(
            [mock_canvas_instance, mock_element_clip],
            size=(project_with_video.width, project_with_video.height)
        )

        # 4. Verifica se o arquivo final foi escrito
        mock_final_clip_instance.write_videofile.assert_called_once_with(
            "output.mp4", fps=30, codec='libx264'
        )
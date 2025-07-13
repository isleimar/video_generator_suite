import pytest
from unittest.mock import MagicMock, patch

from utils.color import hex_to_rgb

from video_model.models import (
    Project, ImageElement, VideoElement, RectangleElement, TextElement, AudioElement
)
from video_renderer.renderer import Renderer

from video_renderer.renderer import Loop_fx

# Importamos a classe base do MoviePy para usar no 'spec' do mock
try:
    from moviepy.video.VideoClip import VideoClip as BaseVideoClip
except ImportError:
    # Se o moviepy não estiver instalado, define um objeto genérico para que a coleta de teste não falhe
    BaseVideoClip = type('BaseVideoClip', (object,), {})

# --- Fixtures (Definidas no nível do módulo para fácil acesso) ---

@pytest.fixture
def project_with_image():
    elements = [ImageElement(name="logo", start=2, path="logo.png", width=200, height=100)]
    return Project(width=1920, height=1080, duration=10, elements=elements)

@pytest.fixture
def project_with_video():
    elements = [VideoElement(name="trailer", start=5, path="trailer.mp4", width=1280, height=720, volume=0.7)]
    return Project(width=1920, height=1080, duration=30, elements=elements)

@pytest.fixture
def project_with_rectangle():
    elements = [RectangleElement(name="bg", start=0, width=800, height=600, color="#FF0000")]
    return Project(width=1920, height=1080, duration=10, elements=elements)

@pytest.fixture
def project_with_text():
    font_spec = {"path": "Arial.ttf", "size": 72, "color": "#FFFFFF"}
    elements = [TextElement(name="title", start=1, text="Hello World", font=font_spec)]
    return Project(width=1920, height=1080, duration=10, elements=elements)

@pytest.fixture
def project_with_audio():
    elements = [AudioElement(name="music", start=0, path="music.mp3", volume=0.5)]
    return Project(width=1920, height=1080, duration=60, elements=elements)

@pytest.fixture
def project_with_looping_video():
    elements = [
        VideoElement(name="bg_loop", start=0, path="loop.mp4", end=20, loop=True)
    ]
    return Project(width=1280, height=720, duration=20, elements=elements)


# --- Classe de Testes para o Renderer ---

class TestRenderer:

    @patch('video_renderer.renderer.ImageClip')
    def test_create_image_clip(self, mock_clip, project_with_image):
        mock_instance = MagicMock()
        mock_clip.return_value = mock_instance
        renderer = Renderer(project_with_image)
        renderer._create_image_clip(project_with_image.elements[0])
        mock_clip.assert_called_once_with("logo.png")
        mock_instance.resized.assert_called_once_with((200, 100))

    @patch('video_renderer.renderer.VideoFileClip')
    def test_create_video_clip(self, mock_clip, project_with_video):
        mock_instance = MagicMock()
        mock_instance.with_volume_scaled.return_value = mock_instance
        mock_clip.return_value = mock_instance
        renderer = Renderer(project_with_video)
        renderer._create_video_clip(project_with_video.elements[0])
        mock_clip.assert_called_once_with("trailer.mp4")
        mock_instance.with_volume_scaled.assert_called_once_with(0.7)
        mock_instance.resized.assert_called_once_with((1280, 720))

    @patch('video_renderer.renderer.ColorClip')
    def test_create_rectangle_clip(self, mock_clip, project_with_rectangle):
        renderer = Renderer(project_with_rectangle)
        renderer._create_rectangle_clip(project_with_rectangle.elements[0])
        mock_clip.assert_called_once_with(size=(800, 600), color="#FF0000")

    @patch('video_renderer.renderer.TextClip')
    def test_create_text_clip(self, mock_clip, project_with_text):
        renderer = Renderer(project_with_text)
        renderer._create_text_clip(project_with_text.elements[0])
        mock_clip.assert_called_once_with(
            text="Hello World", font="Arial.ttf", font_size=72,
            color="#FFFFFF", stroke_color=None, stroke_width=0
        )

    @patch('video_renderer.renderer.AudioFileClip')
    def test_create_audio_clip(self, mock_clip, project_with_audio):
        mock_instance = MagicMock()
        mock_clip.return_value = mock_instance
        renderer = Renderer(project_with_audio)
        renderer._create_audio_clip(project_with_audio.elements[0])
        mock_clip.assert_called_once_with("music.mp3")
        mock_instance.with_volume_scaled.assert_called_once_with(0.5)

    # MUDANÇA: Removemos o patch de BaseVideoClip e o argumento do teste
    @patch('video_renderer.renderer.CompositeVideoClip')
    @patch('video_renderer.renderer.ColorClip')
    def test_render_video_orchestration(self, mock_color_clip, mock_composite_clip, project_with_video):
        """
        Testa se render_video orquestra a criação do canvas, elementos e composição final.
        """
        mock_canvas = MagicMock()
        mock_color_clip.return_value = mock_canvas
        mock_canvas.size = (project_with_video.width, project_with_video.height)
        mock_final_clip = MagicMock()
        mock_composite_clip.return_value = mock_final_clip
        
        renderer = Renderer(project_with_video)
        
        # --- CORREÇÃO FINAL AQUI ---
        # Criamos um mock que se conforma à especificação de um BaseVideoClip.
        # Agora, isinstance(mock_element_clip, BaseVideoClip) retornará True.
        mock_element_clip = MagicMock(spec=BaseVideoClip)
        
        renderer._create_clip_for_element = MagicMock(return_value=mock_element_clip)

        # Executa o método principal
        renderer.render_video("output.mp4", fps=30)

        # 1. Verifica se o canvas foi criado corretamente
        expected_rgb_color = hex_to_rgb(project_with_video.background_color)
        mock_color_clip.assert_called_once_with(
            size=(project_with_video.width, project_with_video.height),
            color=expected_rgb_color,
            duration=project_with_video.duration
        )

        # 2. Verifica se a criação de clipes foi chamada
        renderer._create_clip_for_element.assert_called_once_with(project_with_video.elements[0])
        
        # 3. Verifica se a composição final foi criada com os clipes corretos
        mock_composite_clip.assert_called_once_with(
            [mock_canvas, mock_element_clip],
            size=mock_canvas.size
        )

        # 4. Verifica se o arquivo final foi escrito
        mock_final_clip.write_videofile.assert_called_once_with(
            "output.mp4", fps=30, codec='libx264', temp_audiofile_path='tmp/'
        )
    
    @patch('video_renderer.renderer.Loop_fx')
    @patch('video_renderer.renderer.VideoFileClip')
    def test_looping_video_is_handled_correctly(self, mock_video_clip, mock_loop_fx, project_with_looping_video):
        """Testa se a lógica de loop é acionada quando necessário."""
        # Supomos que o vídeo original tem 5 segundos de duração
        # 1. Preparamos os mocks
        mock_clip_instance = MagicMock(duration=5)
        mock_video_clip.return_value = mock_clip_instance
        
        # Quando Loop_fx() for chamado, ele retornará um mock da *instância*
        mock_loop_instance = MagicMock()
        mock_loop_fx.return_value = mock_loop_instance
        
        # Quando .apply() for chamado na instância, ele deve retornar o clipe
        # para que a chamada .with_duration() possa ser encadeada
        mock_loop_instance.apply.return_value = mock_clip_instance
        
        # 2. Executamos o código
        renderer = Renderer(project_with_looping_video)
        element = project_with_looping_video.elements[0]
        renderer._create_clip_for_element(element)

        # 3. Verificamos o comportamento
        # Assert que a classe Loop_fx foi instanciada uma vez
        mock_loop_fx.assert_called_once_with()
        # Assert que o método .apply() da instância foi chamado com o clipe
        mock_loop_instance.apply.assert_called_once_with(mock_clip_instance)
        # Assert que .with_duration() foi chamado no clipe retornado por .apply()
        mock_clip_instance.with_duration.assert_called_once_with(20)
    
    @patch('video_renderer.renderer.FILTER_REGISTRY')
    @patch('video_renderer.renderer.ImageClip')
    def test_filter_application(self, mock_image_clip, mock_filter_registry, project_with_image):
        """Testa se a lógica de aplicação de filtros é chamada corretamente."""
                
        # 1. Primeiro, modificamos os dados de teste
        image_element = project_with_image.elements[0]
        image_element.filters = [{"type": "fade", "duration_in": 2.0}]
        
        # 2. Preparamos os mocks
        mock_clip_instance = MagicMock()
        mock_image_clip.return_value = mock_clip_instance
        
        # Garante que as chamadas de método em cadeia retornem o mesmo mock
        mock_clip_instance.with_duration.return_value = mock_clip_instance
        mock_clip_instance.with_start.return_value = mock_clip_instance
        mock_clip_instance.with_position.return_value = mock_clip_instance
        mock_clip_instance.with_opacity.return_value = mock_clip_instance
        mock_clip_instance.rotate.return_value = mock_clip_instance
        mock_clip_instance.resized.return_value = mock_clip_instance

        mock_fade_func = MagicMock(return_value=mock_clip_instance)
        mock_filter_registry.get.return_value = mock_fade_func
        
        # 3. SÓ AGORA criamos o Renderer, com os dados já modificados
        renderer = Renderer(project_with_image)

        # 4. Executamos a ação
        renderer._create_clip_for_element(image_element)

        # 5. Verificamos o resultado
        mock_filter_registry.get.assert_called_once_with("fade")
        mock_fade_func.assert_called_once_with(mock_clip_instance, duration_in=2.0)

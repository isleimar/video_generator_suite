import pytest
from unittest.mock import MagicMock, patch

from video_model.models import Project, ImageElement
from video_renderer.renderer import Renderer

@pytest.fixture
def resolved_project():
    """Cria um objeto de projeto simples e já resolvido para os testes."""
    elements = [
        ImageElement(
            # Argumentos posicionais
            name="logo",
            start=2,
            # CORREÇÃO: O argumento 'type' foi removido desta chamada
            
            # Argumentos apenas-nomeados (keyword-only)
            path="logo.png",
            end=8,
            x=100,
            y=150,
            width=200,
            height=100
        )
    ]
    return Project(width=1920, height=1080, duration=10, elements=elements)


@patch('video_renderer.renderer.mp') # Simula todo o módulo moviepy.editor
def test_renderer_initialization(mock_mp, resolved_project):
    """Testa se o renderizador é inicializado corretamente."""
    renderer = Renderer(resolved_project)
    assert renderer.project == resolved_project

@patch('video_renderer.renderer.mp')
def test_render_video_calls_composition_and_write(mock_mp, resolved_project):
    """
    Testa se o método render_video chama as funções corretas do MoviePy.
    (Este teste está como placeholder e vai passar sem fazer nada por enquanto)
    """
    # Configura os mocks para não fazer nada, mas registrar que foram chamados
    mock_composite = MagicMock()
    mock_mp.CompositeVideoClip.return_value = mock_composite
    
    renderer = Renderer(resolved_project)
    # A lógica principal do teste está comentada pois a implementação não foi feita
    pass

@patch('video_renderer.renderer.mp') # Simula todo o módulo moviepy.editor
def test_create_image_clip_calls_moviepy_correctly(mock_mp, resolved_project):
    """
    Testa se o método _create_image_clip chama as funções do MoviePy com os argumentos corretos.
    """
    mock_image_clip_instance = MagicMock()
    mock_mp.ImageClip.return_value = mock_image_clip_instance

    renderer = Renderer(resolved_project)
    image_element = resolved_project.elements[0]
    
    # Executa o método que queremos testar
    renderer._create_image_clip(image_element)

    # 1. Verifica se ImageClip foi chamado com o caminho correto
    mock_mp.ImageClip.assert_called_once_with("logo.png")

    # 2. CORREÇÃO: Verifica se o método .resize foi chamado com a largura e altura corretas
    #    que estão definidas na fixture (width=200, height=100).
    mock_image_clip_instance.resize.assert_called_once_with(
        width=image_element.width, 
        height=image_element.height
    )

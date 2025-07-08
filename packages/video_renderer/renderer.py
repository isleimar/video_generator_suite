# packages/video_renderer/renderer.py
from __future__ import annotations
from video_model.models import Project, BaseElement, ImageElement, VideoElement, TextElement, RectangleElement, AudioElement, SubtitleElement
from .filters import FILTER_REGISTRY

# É importante fazer a importação do moviepy dentro de um try/except
# para que outros pacotes não quebrem se ele não estiver instalado.
try:
    import moviepy.editor as mp
    from moviepy.video.VideoClip import ColorClip
except ImportError:
    print("AVISO: A biblioteca MoviePy não está instalada. O renderizador não funcionará.")
    mp = None
    ColorClip = None

class Renderer:
    def __init__(self, resolved_project: Project):
        if not mp:
            raise ImportError("A biblioteca MoviePy é necessária para a renderização.")
        self.project = resolved_project

    def render_video(self, output_path: str):
        """
        Renderiza o projeto resolvido para um arquivo de vídeo.

        # TODO: Implementar a lógica de renderização.
        # 1. Criar o clipe de fundo principal (canvas) usando ColorClip.
        #    canvas = ColorClip(size=(self.project.width, self.project.height),
        #                       color=self.project.background_color,
        #                       duration=self.project.duration)
        # 2. Criar uma lista para armazenar os clipes de cada elemento.
        # 3. Iterar sobre self.project.elements:
        #    a. Chamar self._create_clip_for_element(element) para cada um.
        #    b. Adicionar o clipe retornado à lista.
        # 4. Usar mp.CompositeVideoClip([canvas] + lista_de_clipes) para combinar tudo.
        # 5. Chamar final_clip.write_videofile(output_path, codec='libx264', fps=24).
        """
        print(f"Simulando renderização para: {output_path}")
        # Placeholder
        if not self.project.elements:
            print("Nenhum elemento para renderizar.")
            return
            
        final_clip = self._create_clip_for_element(self.project.elements[0])
        print(f"Clipe para o elemento '{self.project.elements[0].name}' criado (simulado).")


    def _create_clip_for_element(self, element: BaseElement) -> mp.Clip:
        """Fábrica de clipes que despacha para o método de criação correto."""
        
        # Mapeia o tipo do elemento para o método que o cria
        creation_methods = {
            "image": self._create_image_clip,
            "video": self._create_video_clip,
            # TODO: Adicionar os outros tipos (text, rectangle, etc.)
        }
        
        method = creation_methods.get(element.type)
        if not method:
            raise NotImplementedError(f"A criação de clipes para o tipo '{element.type}' não foi implementada.")
            
        # 1. Cria o clipe base
        clip = method(element)
        
        # 2. Define duração, início, posição, etc.
        # TODO: Implementar a lógica para set_start, set_duration, set_position...
        # clip = clip.set_start(element.start).set_duration(element.end - element.start)
        # clip = clip.set_position((element.x, element.y))
        
        # 3. Aplica filtros
        # TODO: Iterar sobre element.filters e aplicar cada um usando o FILTER_REGISTRY
        
        return clip

    def _create_image_clip(self, element: ImageElement) -> mp.ImageClip:
        """
        Cria um ImageClip a partir de um ImageElement.
        """
        # Cria o clipe de imagem a partir do caminho
        clip = mp.ImageClip(element.path)
        
        # Se as dimensões foram especificadas, redimensiona o clipe
        if element.width is not None or element.height is not None:
            clip = clip.resize(width=element.width, height=element.height)
            
        return clip

    def _create_video_clip(self, element: VideoElement) -> mp.VideoFileClip:
        """
        Cria um VideoFileClip a partir de um VideoElement.
        # TODO: Implementar
        """
        return ColorClip(size=(100, 100), color=(0, 255, 0), duration=5) # Placeholder
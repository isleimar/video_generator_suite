from __future__ import annotations
from video_model.models import Project, BaseElement, ImageElement, VideoElement, RectangleElement, TextElement
from .filters import FILTER_REGISTRY

# Importamos as classes diretamente do pacote principal, como você descobriu.
from moviepy import (
    ImageClip, VideoFileClip, ColorClip, CompositeVideoClip, TextClip
)

class Renderer:
    def __init__(self, resolved_project: Project):
        self.project = resolved_project

    def render_video(self, output_path: str, fps: int = 24):
        """
        Renderiza o projeto resolvido para um arquivo de vídeo, compondo todos os elementos.
        """
        # 1. Cria o clipe de fundo principal (canvas)
        canvas = ColorClip(
            size=(int(self.project.width), int(self.project.height)),
            color=self.project.background_color,
            duration=self.project.duration
        )
        
        # 2. Processa cada elemento e o transforma em um clipe configurado
        element_clips = []
        for element in self.project.elements:
            # Pula elementos de áudio por enquanto na composição de vídeo
            if element.type == 'audio':
                continue
            
            clip = self._create_clip_for_element(element)
            element_clips.append(clip)
            
        # 3. Compõe o vídeo final com o canvas e todos os clipes de elementos
        final_video = CompositeVideoClip([canvas] + element_clips, size=canvas.size)
        
        # TODO: Adicionar faixas de áudio globais ao 'final_video'
        
        # 4. Escreve o arquivo de vídeo final
        final_video.write_videofile(output_path, fps=fps, codec='libx264')

    def _create_clip_for_element(self, element: BaseElement) -> "mp.Clip":
        """
        Fábrica de clipes que cria, configura e retorna um clipe pronto para composição.
        """
        creation_methods = {
            "image": self._create_image_clip,
            "video": self._create_video_clip,
            "rectangle": self._create_rectangle_clip,
            "text": self._create_text_clip,
            # TODO: Adicionar 'audio' e 'subtitles'
        }
        method = creation_methods.get(element.type)
        if not method:
            raise NotImplementedError(f"A criação de clipes para o tipo '{element.type}' não foi implementada.")
            
        # 1. Cria o clipe base
        clip = method(element)
        
        # 2. Define a duração do clipe
        duration = element.end - element.start if element.end is not None else clip.duration
        clip = clip.set_duration(duration)

        # 3. Define a posição na tela e o tempo de início
        clip = clip.set_position((element.x, element.y)).set_start(element.start)
        
        # 4. Aplica opacidade e rotação
        if element.opacity < 1.0:
            clip = clip.set_opacity(element.opacity)
        if element.rotation != 0:
            clip = clip.rotate(element.rotation)

        # 5. Aplica filtros
        for filt in element.filters:
            filter_func = FILTER_REGISTRY.get(filt.get("type"))
            if filter_func:
                filter_params = {k: v for k, v in filt.items() if k != "type"}
                clip = filter_func(clip, **filter_params)
        
        return clip

    def _create_image_clip(self, element: ImageElement) -> "ImageClip":
        """Cria um ImageClip a partir de um ImageElement."""
        clip = ImageClip(element.path)
        if element.width is not None or element.height is not None:
            # MUDANÇA: .resize() se torna .resized()
            clip = clip.resized(width=element.width, height=element.height)
        return clip

    def _create_video_clip(self, element: VideoElement) -> "VideoFileClip":
        """Cria um VideoFileClip a partir de um VideoElement."""
        clip = VideoFileClip(element.path)
        if element.volume != 1.0:
            clip = clip.volumex(element.volume) # .volumex() ainda é válido
        if element.width is not None or element.height is not None:
            # MUDANÇA: .resize() se torna .resized()
            clip = clip.resized(width=element.width, height=element.height)
        return clip

    def _create_rectangle_clip(self, element: RectangleElement) -> "ColorClip":
        """Cria um ColorClip a partir de um RectangleElement."""
        if element.width is None or element.height is None:
            raise ValueError("RectangleElement deve ter 'width' e 'height' definidos.")
        
        return ColorClip(
            size=(int(element.width), int(element.height)),
            color=element.color
        )

    def _create_text_clip(self, element: TextElement) -> "TextClip":
        """Cria um TextClip a partir de um TextElement."""
        # MoviePy espera que os parâmetros da fonte estejam em um formato específico.
        # Nós extraímos os valores do dicionário 'font' do nosso modelo.
        font_details = element.font
        
        # O TextClip espera que a cor seja passada sem o '#', mas aceita nomes de cores.
        # Nós removemos o '#' se ele existir.
        color = font_details.get("color", "white").lstrip('#')

        return TextClip(
            txt=element.text,
            font=font_details.get("path"),
            fontsize=font_details.get("size", 24),
            color=color,
            stroke_color=font_details.get("stroke", {}).get("color"),
            stroke_width=font_details.get("stroke", {}).get("width", 0),
        )
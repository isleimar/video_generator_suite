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

    def render_video(self, output_path: str):
        """Renderiza o projeto resolvido para um arquivo de vídeo."""
        # TODO: Implementar a lógica de composição completa
        pass

    def _create_clip_for_element(self, element: BaseElement) -> "VideoFileClip | ImageClip | ColorClip | TextClip":
        """Fábrica de clipes que despacha para o método de criação correto."""
        creation_methods = {
            "image": self._create_image_clip,
            "video": self._create_video_clip,
            "rectangle": self._create_rectangle_clip,            
            "text": self._create_text_clip,
        }
        method = creation_methods.get(element.type)
        if not method:
            raise NotImplementedError(f"A criação de clipes para o tipo '{element.type}' não foi implementada.")
        
        return method(element)

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
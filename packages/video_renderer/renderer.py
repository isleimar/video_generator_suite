from __future__ import annotations
from utils.color import hex_to_rgb
from video_model.models import (
    Project, BaseElement, ImageElement, VideoElement, RectangleElement, 
    TextElement, AudioElement, SubtitleElement
)
from .filters import FILTER_REGISTRY
import logging

from moviepy import (
    ImageClip, VideoFileClip, ColorClip, CompositeVideoClip, TextClip,
    AudioFileClip, CompositeAudioClip
)
from moviepy.video.VideoClip import VideoClip as BaseVideoClip # Usado para type hints
from moviepy.video.fx import Loop as Loop_fx
from moviepy.video.fx import Rotate

from .subtitle_generator import SubtitleGenerator

class Renderer:
    def __init__(self, resolved_project: Project):
        self.project = resolved_project

    def render_video(self, output_path: str, fps: int = 24):
        """Renderiza o projeto resolvido, compondo todos os elementos."""
        rgb_background = hex_to_rgb(self.project.background_color)
        canvas = ColorClip(
            size=(int(self.project.width), int(self.project.height)),
            color=rgb_background,
            duration=self.project.duration
        )
        
        video_clips = []
        audio_clips = []
        
        for element in self.project.elements:
            # Ignoramos os tipos 'audio' e 'subtitles' neste laço,
            # pois eles são tratados de forma especial mais tarde.
            if element.type in ['audio', 'subtitles']:
                continue            
            clip = self._create_clip_for_element(element)
            video_clips.append(clip)
            
        final_video = CompositeVideoClip([canvas] + video_clips, size=canvas.size)        
        
        # Pega todos os elementos de áudio para compor
        audio_elements = [el for el in self.project.elements if el.type == 'audio']
        for element in audio_elements:
            clip = self._create_clip_for_element(element)
            audio_clips.append(clip)

        if audio_clips:
            final_audio = CompositeAudioClip(audio_clips)
            final_video.audio = final_audio.with_duration(final_video.duration)
        
        # Após compor o vídeo, procuramos por elementos de legenda para aplicar
        subtitle_elements = [el for el in self.project.elements if el.type == 'subtitles']
        if subtitle_elements:
            logging.info(f"Aplicando legenda do elemento '{subtitle_elements[0].name}'...")
            subtitle_gen = SubtitleGenerator(
                subtitle_elements[0], 
                int(self.project.width), 
                int(self.project.height)
            )
            final_video = subtitle_gen.apply_to_clip(final_video)

        final_video.write_videofile(output_path, fps=fps, codec='libx264', temp_audiofile_path='tmp/')

    # CORREÇÃO: A anotação de tipo usa a união das classes reais
    def _create_clip_for_element(self, element: BaseElement) -> "BaseVideoClip | AudioFileClip":
        """Fábrica de clipes que cria, configura e retorna um clipe pronto para composição."""
        creation_methods = {
            "image": self._create_image_clip, "video": self._create_video_clip,
            "rectangle": self._create_rectangle_clip, "text": self._create_text_clip,
            "audio": self._create_audio_clip,
        }
        method = creation_methods.get(element.type)
        if not method:
            raise NotImplementedError(f"Criação para o tipo '{element.type}' não foi implementada.")
            
        clip = method(element)

        is_looping = getattr(element, 'loop', False)
        has_end = element.end is not None
        clip_natural_duration = clip.duration 

        final_duration = 0

        if is_looping:
            if has_end:
                # REGRA 4: Loop com 'end' definido
                element_duration = element.end - element.start
                max_possible_duration = self.project.duration - element.start
                final_duration = min(element_duration, max_possible_duration)
            else:
                # REGRA 3: Loop sem 'end' definido
                final_duration = self.project.duration - element.start
            
            # Aplica o efeito de loop se necessário
            clip = Loop_fx().apply(clip).with_duration(final_duration)
        else: # not is_looping
            if has_end:
                # REGRA 2: Sem loop, com 'end' definido
                element_duration = element.end - element.start
                # A duração é a definida pelo elemento, mas não pode ser maior que a do clipe original                
                final_duration =  element_duration if clip_natural_duration is None else  min(element_duration, clip_natural_duration)
            else:
                # REGRA 1: Sem loop, sem 'end' definido (duração padrão)
                final_duration = clip_natural_duration
            
            clip = clip.with_duration(final_duration)
        
        # # Define a duração. Para áudio, isso é importante na composição.
        # duration = element.end - element.start if element.end is not None else (clip.duration or self.project.duration)
        clip = clip.with_start(element.start)

        # Propriedades visuais não se aplicam ao áudio
        if isinstance(clip, BaseVideoClip):
             clip = clip.with_position((element.x, element.y))
             if element.opacity < 1.0:
                 clip = clip.with_opacity(element.opacity)
             if element.rotation != 0:
                 clip = Rotate(element.rotation).apply(clip)
        
        for filt in element.filters:
            filter_func = FILTER_REGISTRY.get(filt.get("type"))
            if filter_func:
                # Passa todos os parâmetros do filtro (ex: duration_in) para a função
                filter_params = {k: v for k, v in filt.items() if k != "type"}
                clip = filter_func(clip, **filter_params)
                        
        return clip

    def _create_image_clip(self, element: ImageElement) -> "ImageClip":
        clip = ImageClip(element.path)        
        if element.width is not None and element.height is not None:
            clip = clip.resized((int(element.width), int(element.height)))        
        elif element.width is not None:
            clip = clip.resized(width=int(element.width))        
        elif element.height is not None:
            clip = clip.resized(height=int(element.height))
        return clip

    def _create_video_clip(self, element: VideoElement) -> "VideoFileClip":
        clip = VideoFileClip(element.path)
        if element.volume != 1.0:
            clip = clip.with_volume_scaled(element.volume)
        if element.width is not None and element.height is not None:
            clip = clip.resized((int(element.width), int(element.height)))
        elif element.width is not None:
            clip = clip.resized(width=int(element.width))
        elif element.height is not None:
            clip = clip.resized(height=int(element.height))
        return clip

    def _create_rectangle_clip(self, element: RectangleElement) -> "ColorClip":
        if element.width is None or element.height is None:
            raise ValueError("RectangleElement deve ter 'width' e 'height' definidos.")
        return ColorClip(size=(int(element.width), int(element.height)), color=element.color)

    def _create_text_clip(self, element: TextElement) -> "TextClip":
        font_details = element.font
        color = font_details.get("color", "white")
        clip_kwargs = {
            "text": element.text,
            "font": font_details.get("path"),
            "font_size": font_details.get("size", 24),
            "color": color,
            "stroke_color": font_details.get("stroke", {}).get("color"),
            "stroke_width": font_details.get("stroke", {}).get("width", 0),
        }
        # Se uma largura foi definida no YAML, ativamos o modo 'caption'
        if element.width is not None:
            clip_kwargs['method'] = 'caption'
            # A altura pode ser None para que o MoviePy a calcule automaticamente
            size_w = int(element.width)
            size_h = int(element.height) if element.height is not None else None
            clip_kwargs['size'] = (size_w, size_h) 
        return TextClip(**clip_kwargs)
    
    def _create_audio_clip(self, element: AudioElement) -> "AudioFileClip":
        """Cria um AudioFileClip a partir de um AudioElement."""
        clip = AudioFileClip(element.path)
        if element.volume != 1.0:
            clip = clip.with_volume_scaled(element.volume)
        return clip
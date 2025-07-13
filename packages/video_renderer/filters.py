import cv2
import numpy as np
from moviepy.video import fx as vfx
from moviepy.audio import fx as afx

def apply_fade(clip, duration_in=0, duration_out=0, **kwargs):
    """
    Aplica efeitos de fade in e/ou fade out a um clipe.
    Funciona tanto para clipes de vídeo quanto de áudio.
    """
    # Aplica fade in se uma duração for fornecida
    if duration_in > 0:
        # A biblioteca diferencia entre fade de áudio e de vídeo
        if hasattr(clip, 'audio') and clip.audio is not None:
            clip.audio = afx.AudioFadeIn(duration_in).apply(clip.audio)
        clip = vfx.FadeIn(duration_in).apply(clip)

    # Aplica fade out se uma duração for fornecida
    if duration_out > 0:
        if hasattr(clip, 'audio') and clip.audio is not None:
            clip.audio = afx.AudioFadeOut(duration_out).apply(clip.audio)
        clip = vfx.FadeOut(duration_out).apply(clip)
            
    return clip

def apply_blur(clip, zsize=1, **kwargs):
    def blur_frame(get_frame, timestamp): 
        frame = get_frame(timestamp).astype("uint8")
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)    
        img = cv2.blur(img, (zsize,zsize), cv2.BORDER_DEFAULT)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)        
    return clip.transform(blur_frame)


# Registro de filtros disponíveis
FILTER_REGISTRY = {
    "fade": apply_fade,
    "blur": apply_blur,
}
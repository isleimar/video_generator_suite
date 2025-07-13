# VERIFIQUE SE KW_ONLY ESTÁ SENDO IMPORTADO AQUI
from dataclasses import dataclass, field, KW_ONLY
from typing import List, Dict, Any, Union

DynamicValue = Union[float, int, str]

@dataclass
class BaseElement:
    # Argumentos que DEVEM ser passados pela posição
    name: str
    start: DynamicValue
    type: str

    # ESTA LINHA É O SEPARADOR E A PARTE MAIS IMPORTANTE DA CORREÇÃO
    _: KW_ONLY

    # Argumentos que DEVEM ser passados pelo nome (ex: end=10)
    end: DynamicValue = None
    x: DynamicValue = 0
    y: DynamicValue = 0
    width: DynamicValue = None
    height: DynamicValue = None
    media_duration: DynamicValue = None
    media_width: DynamicValue = None
    media_height: DynamicValue = None
    opacity: DynamicValue = 1.0
    rotation: DynamicValue = 0
    filters: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ImageElement(BaseElement):
    # 'path' se torna um argumento apenas-nomeado por causa da herança
    path: str
    type: str = field(default="image", init=False)
    
@dataclass
class VideoElement(BaseElement):
    path: str
    type: str = field(default="video", init=False)
    volume: DynamicValue = 1.0
    loop: bool = False

@dataclass
class AudioElement(BaseElement):
    path: str    
    type: str = field(default="audio", init=False)
    volume: DynamicValue = 1.0
    loop: bool = False

@dataclass
class RectangleElement(BaseElement):
    type: str = field(default="rectangle", init=False)    
    color: str = "#FFFFFF"
    corner_radius: int = 0

@dataclass
class TextElement(BaseElement):
    text: str
    type: str = field(default="text", init=False)    
    font: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SubtitleElement(BaseElement):
    path: str    
    type: str = field(default="subtitles", init=False)
    font: Dict[str, Any] = field(default_factory=dict)
    position: str = "bottom"
    margin_v: int = 60
    max_lines: int = 2
    max_words: int = 8
    max_width: int = 100
    line_spacing_factor: float = 1.0
    timing: Dict[str, Any] = field(default_factory=dict)
    word_background: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Project:
    width: DynamicValue
    height: DynamicValue
    duration: DynamicValue
    _: KW_ONLY
    background_color: str = "#000000"
    elements: List[BaseElement] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        ELEMENT_TYPE_MAP = {
            "image": ImageElement, "video": VideoElement, "audio": AudioElement,
            "rectangle": RectangleElement, "text": TextElement, "subtitles": SubtitleElement
        }
        element_objects = []
        for el_data in data.get("elements", []):
            el_type_str = el_data.pop("type", None)
            
            if not el_type_str or el_type_str not in ELEMENT_TYPE_MAP:
                raise ValueError(f"Tipo de elemento desconhecido ou não especificado: {el_type_str}")
            
            ElementClass = ELEMENT_TYPE_MAP[el_type_str]
            element_objects.append(ElementClass(**el_data))
        
        project_data = {k: v for k, v in data.items() if k != "elements"}        
        
        project_data['elements'] = element_objects
        
        return cls(**project_data)
def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converte uma cor em string hexadecimal (ex: '#RRGGBB') para uma tupla RGB."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("A string de cor hexadecimal deve ter 6 caracteres.")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
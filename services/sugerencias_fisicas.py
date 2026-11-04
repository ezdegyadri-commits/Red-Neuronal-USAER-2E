"""OCR privado como borrador; no usa servicios externos ni guarda registros."""
from io import BytesIO


def leer_sugerencia(data: bytes, mime: str) -> str:
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError('Carga una hoja de hasta 8 MB.')
    if mime not in {'image/png', 'image/jpeg', 'image/webp'}:
        raise ValueError('Usa una foto JPG, PNG o WebP.')
    from PIL import Image, ImageOps
    import pytesseract
    image = Image.open(BytesIO(data))
    if image.width * image.height > 24_000_000:
        raise ValueError('La foto es demasiado grande. Usa una copia de menor tamaño.')
    image = ImageOps.exif_transpose(image).convert('RGB')
    image.thumbnail((2400, 2400))
    if image.width < 1400:
        scale = min(2, 1400 / max(1, image.width))
        image = image.resize((int(image.width*scale), int(image.height*scale)))
    data = pytesseract.image_to_data(ImageOps.autocontrast(ImageOps.grayscale(image)), lang='spa', config='--psm 6',
                                    timeout=20, output_type=pytesseract.Output.DICT)
    lines = {}
    reliable = 0
    for i, word in enumerate(data.get('text', [])):
        word = str(word).strip()
        if not word:
            continue
        try:
            confidence = float(data['conf'][i])
        except (ValueError, TypeError, KeyError, IndexError):
            confidence = 0
        if confidence >= 50:
            reliable += 1
        else:
            word = '[ilegible]'
        line = tuple(data.get(key, [0] * len(data['text']))[i] for key in ('block_num', 'par_num', 'line_num'))
        lines.setdefault(line, []).append(word)
    text = '\n'.join(' '.join(words) for words in lines.values())
    if reliable < 2:
        text = ''
    if not text:
        raise RuntimeError('No se pudo leer la hoja. Intenta con una foto más cercana.')
    return text

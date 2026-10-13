# Informes PDF: guardado fuera de la web, texto para la búsqueda y páginas
# como imágenes con marca de agua (el PDF original solo lo descarga quien tiene
# DESCARGAR_INFORME).
import base64
import hashlib
import io
import os
import uuid
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from . import config

CARPETA = os.path.join(config.CARPETA_DATOS, 'informes')
MAX_TEXTO = 1_000_000


def guardar(contenido: bytes):
    """Guarda el PDF con un nombre aleatorio. Devuelve (ruta relativa, sha256, páginas, texto)."""
    try:
        doc = fitz.open(stream=contenido, filetype='pdf')
    except Exception:
        raise ValueError('El archivo no es un PDF válido.')
    if doc.needs_pass:
        raise ValueError('El PDF está protegido con contraseña. Súbalo sin contraseña.')
    paginas = doc.page_count
    texto = '\n'.join(p.get_text() for p in doc)[:MAX_TEXTO]
    doc.close()

    relativa = os.path.join(str(datetime.now().year), f'{uuid.uuid4().hex}.pdf')
    destino = os.path.join(CARPETA, relativa)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, 'xb') as f:
        f.write(contenido)
    return relativa.replace(os.sep, '/'), hashlib.sha256(contenido).hexdigest(), paginas, texto.replace('\x00', '')


def borrar(relativa):
    try:
        os.remove(os.path.join(CARPETA, relativa))
    except OSError:
        pass


def ruta_absoluta(relativa):
    destino = os.path.realpath(os.path.join(CARPETA, relativa))
    if not destino.startswith(os.path.realpath(CARPETA) + os.sep):
        raise ValueError('Ruta de informe no válida.')
    return destino


def _fuente(tamano):
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:  # Pillow antiguo
        return ImageFont.load_default()


def _marca(imagen: Image.Image, texto: str):
    """Marca de agua diagonal repetida sobre toda la página."""
    ancho, alto = imagen.size
    lado = int((ancho ** 2 + alto ** 2) ** 0.5)
    capa = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)
    fuente = _fuente(max(16, ancho // 32))
    paso_y = max(120, alto // 6)
    for y in range(0, lado, paso_y):
        desplazamiento = -(y // paso_y % 2) * (ancho // 4)
        dibujo.text((desplazamiento, y), (texto + '      ') * 4, font=fuente, fill=(31, 95, 168, 46))
    capa = capa.rotate(35, resample=Image.BICUBIC)
    izquierda, arriba = (lado - ancho) // 2, (lado - alto) // 2
    capa = capa.crop((izquierda, arriba, izquierda + ancho, arriba + alto))
    return Image.alpha_composite(imagen.convert('RGBA'), capa).convert('RGB')


def paginas_con_marca(relativa, marca, zoom=1.6):
    """Cada página como data URI JPEG con la marca de agua del usuario."""
    doc = fitz.open(ruta_absoluta(relativa))
    resultado = []
    try:
        for pagina in doc:
            pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            imagen = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            imagen = _marca(imagen, marca)
            salida = io.BytesIO()
            imagen.save(salida, format='JPEG', quality=72, optimize=True)
            resultado.append('data:image/jpeg;base64,' + base64.b64encode(salida.getvalue()).decode())
    finally:
        doc.close()
    return resultado

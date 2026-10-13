# Búsqueda dentro del contenido de los informes: fragmentos con la palabra
# resaltada (resultados de la búsqueda universal) y posición de cada
# coincidencia en las páginas (visor). Ignora mayúsculas y tildes, y acepta
# plurales y variantes cercanas ("contrato" encuentra "contratos").
import re
import unicodedata

# Palabras que no se resaltan por sí solas (también las ignora el índice en español).
VACIAS = {
    'a', 'al', 'ante', 'con', 'contra', 'de', 'del', 'desde', 'el', 'en', 'entre', 'es', 'esta', 'este', 'hacia',
    'la', 'las', 'lo', 'los', 'mas', 'no', 'o', 'or', 'para', 'pero', 'por', 'que', 'se', 'si', 'sin', 'sobre',
    'su', 'sus', 'un', 'una', 'unas', 'unos', 'y',
}
PALABRA = re.compile(r'\w+')
SEPARADOR_PAGINA = '\f'  # informes.guardar() une las páginas con este carácter


def _letra(c):
    n = ''.join(x for x in unicodedata.normalize('NFD', c) if not unicodedata.combining(x)).lower()
    return n if len(n) == 1 else c.lower()


def normalizar(texto):
    """Minúsculas y sin tildes, con la misma longitud (las posiciones siguen valiendo)."""
    return ''.join(_letra(c) for c in texto)


def terminos(q):
    """Palabras de la consulta que se buscan en el contenido."""
    vistos = []
    for t in PALABRA.findall(normalizar(q or '')):
        if t not in VACIAS and (len(t) >= 3 or t.isdigit()) and t not in vistos:
            vistos.append(t)
    return vistos[:10]


def coincide(palabra, lista):
    """palabra (ya normalizada) es una de las buscadas o una variante cercana."""
    for t in lista:
        if palabra.startswith(t):
            return True
        if len(t) >= 5 and t.startswith(palabra) and len(palabra) >= len(t) - 2:
            return True
    return False


def _limpiar(texto):
    return re.sub(r'\s+', ' ', texto)


def fragmentos(texto, q, maximo=3, contexto=90, paginas=None):
    """Hasta `maximo` fragmentos del texto con las coincidencias marcadas.
    Devuelve {total, fragmentos: [{pagina, partes: [{texto, marca}]}]}; la página es None si el
    texto se guardó sin separadores de página (y el informe tiene más de una)."""
    lista = terminos(q)
    if not texto or not lista:
        return {'total': 0, 'fragmentos': []}
    norm = normalizar(texto)
    posiciones = [(m.start(), m.end()) for m in PALABRA.finditer(norm) if coincide(m.group(), lista)]
    con_paginas = SEPARADOR_PAGINA in texto or paginas == 1
    resultado, fin_anterior = [], -1
    for i, (ini, fin) in enumerate(posiciones):
        if len(resultado) >= maximo:
            break
        if ini < fin_anterior:
            continue  # ya está dentro del fragmento anterior
        desde = max(0, ini - contexto)
        hasta = min(len(texto), fin + contexto)
        # No cortar palabras en los bordes (sin pasar de 20 letras: tablas o códigos sin espacios).
        for _ in range(20):
            if desde == 0 or not texto[desde - 1].isalnum():
                break
            desde -= 1
        for _ in range(20):
            if hasta >= len(texto) or not texto[hasta].isalnum():
                break
            hasta += 1
        partes, cursor = [], desde
        for a, b in posiciones[i:]:
            if a >= hasta:
                break
            if a > cursor:
                partes.append({'texto': _limpiar(texto[cursor:a]), 'marca': False})
            partes.append({'texto': texto[a:b], 'marca': True})
            cursor = b
        if cursor < hasta:
            partes.append({'texto': _limpiar(texto[cursor:hasta]), 'marca': False})
        if desde > 0:
            partes[0]['texto'] = '…' + partes[0]['texto'].lstrip()
        if hasta < len(texto):
            partes[-1]['texto'] = partes[-1]['texto'].rstrip() + '…'
        pagina = texto.count(SEPARADOR_PAGINA, 0, ini) + 1 if con_paginas else None
        resultado.append({'pagina': pagina, 'partes': partes})
        fin_anterior = hasta
    return {'total': len(posiciones), 'fragmentos': resultado}


def marcas_en_pagina(pagina, lista):
    """Rectángulos de las coincidencias en una página de PyMuPDF, en fracciones del ancho y alto
    (0 a 1) para dibujarlos sobre la imagen a cualquier zoom."""
    import fitz  # solo el visor lo necesita

    ancho, alto = pagina.rect.width or 1, pagina.rect.height or 1
    giro = pagina.rotation_matrix  # el texto viene sin girar; la imagen, girada
    marcas = []
    for x0, y0, x1, y1, palabra, *_ in pagina.get_text('words'):
        if any(coincide(p, lista) for p in PALABRA.findall(normalizar(palabra))):
            r = fitz.Rect(x0, y0, x1, y1) * giro
            marcas.append([round(r.x0 / ancho, 4), round(r.y0 / alto, 4), round(r.x1 / ancho, 4), round(r.y1 / alto, 4)])
    return marcas

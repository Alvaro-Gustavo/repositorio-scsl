"""Prueba de punta a punta de la API, a traves de Nginx (http://localhost:8080/api).

Recorre el flujo completo: usuarios y activacion, registro, asignacion, conclusion
con PDF, visor y descarga, busqueda, precedentes, prompts, tablero, auditoria,
configuracion, catalogos, importacion del Excel, 2FA, recuperacion y cierre.

DEJA DATOS DE PRUEBA en la base. Lo recomendado es usar el entorno aislado
(docker-compose.prueba.yml), que no toca los datos reales:
    docker compose -p scsl-prueba -f docker-compose.yml -f docker-compose.prueba.yml up -d --build
    pip install openpyxl
    SCSL_PRUEBA=1 python backend/pruebas/prueba_api.py          (PowerShell: $env:SCSL_PRUEBA=1; python ...)
    docker compose -p scsl-prueba -f docker-compose.yml -f docker-compose.prueba.yml down -v
Sin SCSL_PRUEBA usa el sistema principal (http://localhost:8080): solo en desarrollo.
"""
import base64
import hashlib
import hmac
import io
import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

PRUEBA = bool(os.environ.get('SCSL_PRUEBA'))
BASE = 'http://localhost:8081/api' if PRUEBA else 'http://localhost:8080/api'
COMPOSE = (['docker', 'compose', '-p', 'scsl-prueba', '-f', 'docker-compose.yml', '-f', 'docker-compose.prueba.yml']
           if PRUEBA else ['docker', 'compose'])
CLAVE = 'Prueba#Segura2026'
SUFIJO = uuid.uuid4().hex[:6]


def env(clave):
    with open('.env', encoding='utf-8') as f:
        return re.search(rf'^{clave}=(.*)$', f.read(), re.M).group(1).strip()


def pedir(metodo, ruta, token=None, cuerpo=None, archivos=None, campos=None, binario=False):
    cabeceras = {}
    datos = None
    if token:
        cabeceras['Authorization'] = f'Bearer {token}'
    if archivos is not None:
        limite = uuid.uuid4().hex
        partes = []
        for k, v in (campos or {}).items():
            partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (nombre, contenido, tipo) in archivos.items():
            partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"; filename="{nombre}"\r\n'
                          f'Content-Type: {tipo}\r\n\r\n'.encode() + contenido + b'\r\n')
        datos = b''.join(partes) + f'--{limite}--\r\n'.encode()
        cabeceras['Content-Type'] = f'multipart/form-data; boundary={limite}'
    elif cuerpo is not None:
        datos = json.dumps(cuerpo).encode()
        cabeceras['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            contenido = r.read()
            if binario:
                return r.status, contenido
            return r.status, (json.loads(contenido) if contenido else None)
    except urllib.error.HTTPError as e:
        contenido = e.read()
        try:
            return e.code, json.loads(contenido)
        except ValueError:
            return e.code, contenido.decode(errors='replace')


def ok(condicion, mensaje, detalle=None):
    if not condicion:
        print(f'FALLO: {mensaje}\n  -> {detalle}')
        sys.exit(1)
    print(f'ok: {mensaje}')


def esperar(estado_esperado, resultado, mensaje):
    estado, datos = resultado
    ok(estado == estado_esperado, f'{mensaje} ({estado})', datos)
    return datos


def codigo_del_log(correo):
    """Sin SMTP configurado, el backend escribe el codigo en su log."""
    for _ in range(10):
        log = subprocess.run(COMPOSE + ['logs', 'app', '--no-color'], capture_output=True, text=True,
                             encoding='utf-8', errors='replace').stdout
        codigos = re.findall(rf'para {re.escape(correo)}: (\d{{6}})', log)
        if codigos:
            return codigos[-1]
        time.sleep(1)
    raise RuntimeError(f'No se encontro el codigo para {correo} en el log')


def totp(secreto):
    clave = base64.b32decode(secreto)
    mac = hmac.new(clave, struct.pack('>Q', int(time.time() // 30)), hashlib.sha1).digest()
    o = mac[-1] & 15
    return f'{(struct.unpack(">I", mac[o:o + 4])[0] & 0x7fffffff) % 1000000:06d}'


def pdf_de_prueba(texto):
    """PDF minimo de una pagina con texto."""
    flujo = f'BT /F1 18 Tf 72 720 Td ({texto}) Tj ET'.encode()
    objetos = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R '
               b'/Resources << /Font << /F1 5 0 R >> >> >>',
               b'<< /Length %d >>\nstream\n' % len(flujo) + flujo + b'\nendstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    salida, posiciones = b'%PDF-1.4\n', []
    for i, o in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(salida)
    salida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    salida += b''.join(b'%010d 00000 n \n' % p for p in posiciones)
    salida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, xref)
    return salida


def ingresar(correo, clave, **extra):
    datos = esperar(200, pedir('POST', '/auth/ingresar', cuerpo={'correo': correo, 'clave': clave, **extra}),
                    f'ingresa {correo}')
    return datos['token']


def main():
    # ---------- Acceso ----------
    esperar(401, pedir('GET', '/auth/sesion'), 'sin token no hay sesion')
    esperar(401, pedir('POST', '/auth/ingresar', cuerpo={'correo': env('ADMIN_CORREO'), 'clave': 'mala'}),
            'clave incorrecta rechazada')
    admin = ingresar(env('ADMIN_CORREO'), env('ADMIN_CLAVE'))
    yo = esperar(200, pedir('GET', '/auth/sesion', admin), 'sesion del admin')
    ok(yo['rol'] == 'ADMIN' and 'GESTIONAR_USUARIOS' in yo['permisos'], 'admin con sus permisos')

    # ---------- Usuarios ----------
    cuentas = {}
    for rol, nombre in (('JEFE', 'Jefe Prueba'), ('SECRETARIA', 'Secretaria Prueba'), ('ABOGADO', 'Abogada Prueba')):
        correo = f'{rol.lower()}.{SUFIJO}@prueba.gob.bo'
        u = esperar(200, pedir('POST', '/usuarios', admin, {'nombre_completo': f'{nombre} {SUFIJO}', 'correo': correo,
                                                            'cargo': rol.title(), 'rol': rol}), f'crea usuario {rol}')
        esperar(400, pedir('POST', '/auth/activar', cuerpo={'correo': correo, 'codigo': '000000', 'clave': CLAVE}),
                f'codigo incorrecto rechazado ({rol})')
        esperar(204, pedir('POST', '/auth/activar', cuerpo={'correo': correo, 'codigo': codigo_del_log(correo),
                                                             'clave': CLAVE}), f'activa cuenta {rol}')
        cuentas[rol] = {'id': u['id'], 'correo': correo, 'token': ingresar(correo, CLAVE)}
    jefe, sec, abo = (cuentas[r]['token'] for r in ('JEFE', 'SECRETARIA', 'ABOGADO'))
    esperar(403, pedir('GET', '/usuarios', sec), 'secretaria no administra usuarios')
    roles = esperar(200, pedir('GET', '/roles', sec), 'lista de roles')
    ok(len(roles) == 4, 'cuatro roles')

    # ---------- Alta masiva de usuarios ----------
    lote = [f'lote1.{SUFIJO}@prueba.gob.bo', f'lote2.{SUFIJO}@prueba.gob.bo']
    lista_csv = ('\ufeffNombre;Correo electrónico;Cargo;Rol\r\n'
                 f'Ana Lote {SUFIJO};{lote[0].upper()};Abogada;abogada\r\n'
                 f'Beto Lote {SUFIJO};{lote[1]};;Secretaria\r\n'
                 f'Repetido {SUFIJO};{cuentas["JEFE"]["correo"]};;Jefe\r\n'
                 f'Rol Malo {SUFIJO};malo.{SUFIJO}@prueba.gob.bo;;Gerente\r\n'
                 f'Doble {SUFIJO};{lote[1]};;Jefe\r\n'
                 ';;;\r\n').encode('utf-8')
    csv_archivo = {'archivo': ('usuarios.csv', lista_csv, 'text/csv')}
    esperar(403, pedir('POST', '/usuarios/importar', sec, archivos=csv_archivo, campos={'confirmar': 'no'}),
            'sin GESTIONAR_USUARIOS no importa usuarios')
    esperar(422, pedir('POST', '/usuarios/importar', admin, archivos={'archivo': ('x.pdf', b'%PDF-1.4', 'application/pdf')},
                       campos={'confirmar': 'no'}), 'rechaza formatos que no son Excel ni CSV')
    rev = esperar(200, pedir('POST', '/usuarios/importar', admin, archivos=csv_archivo, campos={'confirmar': 'no'}),
                  'revisa la lista')
    errores_lista = {f['fila']: f['error'] for f in rev['filas']}
    ok(rev['validas'] == 2 and rev['con_error'] == 3 and rev['creados'] == 0 and len(rev['filas']) == 5
       and errores_lista[2] is None and 'Ya existe' in errores_lista[4] and 'Rol' in errores_lista[5]
       and 'repetido' in errores_lista[6], 'marca las filas con error y no crea nada', rev)
    ok(not any(x['correo'] in lote for x in esperar(200, pedir('GET', '/usuarios', admin), 'lista tras revisar')),
       'revisar no crea cuentas')
    hecho = esperar(200, pedir('POST', '/usuarios/importar', admin, archivos=csv_archivo, campos={'confirmar': 'si'}),
                    'crea las filas validas')
    ok(hecho['creados'] == 2, 'crea solo las validas', hecho)
    creados = {x['correo']: x for x in esperar(200, pedir('GET', '/usuarios', admin), 'lista tras crear') if x['correo'] in lote}
    ok(creados.get(lote[0], {}).get('rol') == 'ABOGADO' and creados.get(lote[1], {}).get('rol') == 'SECRETARIA'
       and not any(x['correo_verificado'] for x in creados.values()), 'roles reconocidos y cuentas por activar', creados)
    esperar(204, pedir('POST', '/auth/activar', cuerpo={'correo': lote[0], 'codigo': codigo_del_log(lote[0]), 'clave': CLAVE}),
            'activa una cuenta del lote')
    ingresar(lote[0], CLAVE)
    try:
        from openpyxl import Workbook
    except ImportError:
        Workbook = None
        print('aviso: instale openpyxl para probar la lista de usuarios en Excel')
    if Workbook:
        libro = Workbook()
        libro.active.append(['NOMBRES Y APELLIDOS', 'EMAIL', 'ROL'])
        libro.active.append([f'Excel Lote {SUFIJO}', f'excel.{SUFIJO}@prueba.gob.bo', 'JEFE'])
        salida = io.BytesIO()
        libro.save(salida)
        rx = esperar(200, pedir('POST', '/usuarios/importar', admin, campos={'confirmar': 'no'}, archivos={'archivo': (
            'usuarios.xlsx', salida.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}),
            'revisa una lista en Excel')
        ok(rx['validas'] == 1 and rx['filas'][0]['rol'] == 'JEFE', 'lee el Excel con otros titulos', rx)
    esperar(403, pedir('POST', '/usuarios/reenviar-activacion-pendientes', sec), 'sin permiso no reenvia en lote')
    r = esperar(200, pedir('POST', '/usuarios/reenviar-activacion-pendientes', admin), 'reenvia a los pendientes')
    ok(r['enviados'] >= 1, 'hay pendientes a quienes reenviar', r)
    nuevo_codigo = codigo_del_log(lote[1])
    esperar(204, pedir('POST', '/auth/activar', cuerpo={'correo': lote[1], 'codigo': nuevo_codigo, 'clave': CLAVE}),
            'el codigo reenviado activa la cuenta')

    # ---------- Catalogos ----------
    procedencia = esperar(200, pedir('GET', '/catalogos/procedencias', sec), 'procedencias')[0]
    entidad = esperar(200, pedir('POST', '/catalogos/entidades', sec, {'nombre': f'Gobierno Autónomo Prueba {SUFIJO}'}),
                      'secretaria agrega entidad')
    esperar(409, pedir('POST', '/catalogos/entidades', sec, {'nombre': f'GOBIERNO AUTONOMO prueba {SUFIJO}'}),
            'no admite el mismo valor escrito distinto')
    sug = esperar(200, pedir('GET', f'/catalogos/entidades/sugerencias?texto=gobierno%20autonomo%20{SUFIJO}', sec),
                  'sugerencias por parecido')
    ok(any(s['id'] == entidad['id'] for s in sug), 'la sugerencia encuentra la entidad', sug)
    tipo = esperar(200, pedir('POST', '/catalogos/tipos_tramite', sec, {'nombre': f'Consulta legal {SUFIJO}'}),
                   'tipo de tramite')
    esperar(403, pedir('POST', '/catalogos/tipos_documento', sec, {'nombre': 'Informe'}),
            'secretaria no crea tipos de documento')
    tdoc = esperar(200, pedir('POST', '/catalogos/tipos_documento', admin, {'nombre': f'Informe {SUFIJO}'}),
                   'admin crea tipo de documento')
    profesionales = esperar(200, pedir('GET', '/catalogos/profesionales', sec), 'profesionales')
    prof = next(p for p in profesionales if p['usuario_id'] == cuentas['ABOGADO']['id'])
    ok(prof['nombre'].startswith('ABOGADA PRUEBA'), 'al crear el abogado se creo su profesional')

    # ---------- Registro y asignacion ----------
    esperar(422, pedir('POST', '/tramites', sec, {'hoja_ruta': ''}), 'registro incompleto rechazado')
    registro = {'hoja_ruta': f'inf-{SUFIJO}', 'procedencia_id': procedencia['id'], 'entidad_id': entidad['id'],
                'tipo_tramite_id': tipo['id'], 'asunto': f'Ampliación de plazo de contratación {SUFIJO}'}
    t1 = esperar(200, pedir('POST', '/tramites', sec, registro), 'secretaria registra tramite')
    ok(t1['estado_tramite'] == 'RECIBIDO' and t1['hoja_ruta'] == f'INF-{SUFIJO}'.upper(), 'queda RECIBIDO', t1)
    esperar(403, pedir('POST', '/tramites', abo, registro), 'abogado no registra tramites')
    por_asignar = esperar(200, pedir('GET', '/tramites/por-asignar', sec), 'bandeja por asignar')
    ok(any(t['id'] == t1['id'] for t in por_asignar), 'aparece por asignar')
    d = esperar(200, pedir('PATCH', f'/tramites/{t1["id"]}/asignar', sec, {'profesional_id': prof['id']}), 'asigna abogado')
    ok(d['estado_tramite'] == 'EN_ELABORACION' and d['asignado_por']['id'] == cuentas['SECRETARIA']['id'],
       'pasa a EN_ELABORACION', d)
    pend = esperar(200, pedir('GET', '/tramites/pendientes', abo), 'pendientes del abogado')
    ok([t['id'] for t in pend] == [t1['id']] and 'vencido' in pend[0], 'el abogado ve su pendiente', pend)
    notif = esperar(200, pedir('GET', '/notificaciones', abo), 'notificaciones del abogado')
    ok(notif['no_leidas'] == 1 and notif['items'][0]['tramite_id'] == t1['id']
       and notif['items'][0]['tipo'] == 'TRAMITE_ASIGNADO'
       and notif['items'][0]['creado_por']['id'] == cuentas['SECRETARIA']['id'],
       'el abogado recibe la notificacion de la asignacion', notif)
    ok(esperar(200, pedir('GET', '/notificaciones', sec), 'notificaciones de la secretaria')['no_leidas'] == 0,
       'quien asigna no se notifica a si mismo')
    esperar(404, pedir('PATCH', f'/notificaciones/{notif["items"][0]["id"]}/leida', sec), 'nadie marca avisos ajenos')
    esperar(204, pedir('PATCH', f'/notificaciones/{notif["items"][0]["id"]}/leida', abo), 'marca como leida')
    ok(esperar(200, pedir('GET', '/notificaciones', abo), 'vuelve a consultar')['no_leidas'] == 0, 'queda leida')

    # ---------- Conclusion con PDF ----------
    pdf = pdf_de_prueba(f'Informe legal {SUFIJO} sobre ampliacion de plazo')
    campos = {'tipo_documento_id': tdoc['id'], 'numero_documento': f'cge/scsl/c-{SUFIJO}/2026'}
    esperar(403, pedir('POST', f'/tramites/{t1["id"]}/concluir', sec, campos=campos,
                       archivos={'archivo': ('i.pdf', pdf, 'application/pdf')}), 'secretaria no concluye')
    esperar(422, pedir('POST', f'/tramites/{t1["id"]}/concluir', abo, campos=campos,
                       archivos={'archivo': ('i.pdf', b'no es pdf', 'application/pdf')}), 'rechaza archivo no PDF')
    d = esperar(200, pedir('POST', f'/tramites/{t1["id"]}/concluir', abo, campos=campos,
                           archivos={'archivo': ('informe.pdf', pdf, 'application/pdf')}), 'abogado sube el informe')
    ok(d['estado_tramite'] == 'CONCLUIDO' and d['informe']['paginas'] == 1 and d['fecha_salida'],
       'queda CONCLUIDO con informe y fecha de salida', d)
    ok(d['permisos']['descargar'] is False, 'el abogado no descarga el PDF original')

    def avisos_de(token, tipo):
        return [n for n in esperar(200, pedir('GET', '/notificaciones', token), f'avisos {tipo}')['items']
                if n['tramite_id'] == t1['id'] and n['tipo'] == tipo]
    a_jefe, a_sec = avisos_de(jefe, 'TRAMITE_CONCLUIDO'), avisos_de(sec, 'TRAMITE_CONCLUIDO')
    ok(len(a_jefe) == 1 and 'listo para revisar' in a_jefe[0]['titulo'] and a_jefe[0]['creado_por']['id'] == cuentas['ABOGADO']['id'],
       'el jefe recibe el aviso de tramite concluido', a_jefe)
    ok(len(a_sec) == 1, 'la secretaria que registro y asigno recibe el aviso (una sola vez)', a_sec)
    ok(not avisos_de(abo, 'TRAMITE_CONCLUIDO'), 'quien sube el informe no se avisa a si mismo')
    esperar(200, pedir('POST', f'/tramites/{t1["id"]}/concluir', abo, campos=campos,
                       archivos={'archivo': ('informe-v2.pdf', pdf, 'application/pdf')}), 'sube una version corregida')
    ok(len(avisos_de(jefe, 'INFORME_ACTUALIZADO')) == 1, 'la version nueva avisa "informe actualizado"')
    pags = esperar(200, pedir('GET', f'/tramites/{t1["id"]}/informe/paginas', sec), 'visor con marca de agua')
    ok(len(pags['paginas']) == 1 and pags['paginas'][0].startswith('data:image/jpeg;base64,'), 'pagina como imagen')
    esperar(403, pedir('GET', f'/tramites/{t1["id"]}/informe/descargar', abo), 'abogado no descarga')
    estado, archivo = pedir('GET', f'/tramites/{t1["id"]}/informe/descargar', jefe, binario=True)
    ok(estado == 200 and archivo == pdf, 'el jefe descarga el PDF identico al subido')

    # ---------- Busqueda ----------
    r = esperar(200, pedir('GET', '/tramites?q=ampliacion%20plazo', sec), 'busqueda sin tildes')
    ok(any(t['id'] == t1['id'] for t in r['items']), 'encuentra el tramite', r)
    r = esperar(200, pedir('GET', f'/tramites?q=C-{SUFIJO}', sec), 'busqueda por codigo parcial')
    ok(r['total'] >= 1, 'encuentra por numero de documento', r)
    r = esperar(200, pedir('GET', f'/tramites?estado=CONCLUIDO&entidad_id={entidad["id"]}', sec), 'filtros')
    ok(r['total'] == 1, 'filtra por estado y entidad', r)

    # ---------- Busqueda en el contenido de los informes ----------
    r = esperar(200, pedir('GET', f'/tramites?q=legal%20{SUFIJO}&en=contenido', sec), 'busqueda solo en informes')
    item = next((t for t in r['items'] if t['id'] == t1['id']), None)
    ok(item is not None, 'encuentra el tramite por el texto del PDF', r)
    c = (item or {}).get('coincidencias_informe') or {}
    marcadas = [p['texto'] for f in c.get('fragmentos', []) for p in f['partes'] if p['marca']]
    ok(c.get('total', 0) >= 2 and 'legal' in [m.lower() for m in marcadas] and c['fragmentos'][0]['pagina'] == 1,
       'fragmento con la palabra marcada y su pagina', c)
    r = esperar(200, pedir('GET', f'/tramites?q=C-{SUFIJO}&en=contenido', sec), 'codigo que no esta en el PDF')
    ok(all(t['id'] != t1['id'] for t in r['items']), 'solo en informes no busca en los datos del tramite', r)
    m = esperar(200, pedir('GET', f'/tramites/{t1["id"]}/informe/coincidencias?q=AMPLIACI%C3%93N', sec), 'coincidencias en el visor')
    ok(m['total'] == 1 and len(m['paginas']) == 1 and len(m['paginas'][0][0]) == 4
       and all(0 <= v <= 1 for v in m['paginas'][0][0]), 'rectangulo de la palabra en la pagina (sin tildes)', m)
    m = esperar(200, pedir('GET', f'/tramites/{t1["id"]}/informe/coincidencias?q=de', sec), 'palabra vacia')
    ok(m['total'] == 0, 'no resalta palabras vacias', m)

    # ---------- Precedentes y similares ----------
    t2 = esperar(200, pedir('POST', '/tramites', jefe, {**registro, 'hoja_ruta': f'inf-{SUFIJO}-b',
                                                        'asunto': f'Ampliación de plazo de contratación {SUFIJO} segunda',
                                                        'profesional_id': prof['id']}), 'jefe registra y asigna')
    ok(t2['estado_tramite'] == 'EN_ELABORACION', 'registrado ya asignado')
    ok(esperar(200, pedir('GET', '/notificaciones', abo), 'aviso al registrar asignado')['no_leidas'] == 1,
       'registrar con abogado tambien notifica')
    esperar(204, pedir('POST', '/notificaciones/leer-todas', abo), 'marca todas como leidas')
    sim = esperar(200, pedir('GET', f'/tramites/{t2["id"]}/similares', abo), 'similares')
    ok(any(s['tramite']['id'] == t1['id'] for s in sim), 'sugiere el tramite parecido', sim)
    p = esperar(200, pedir('POST', f'/tramites/{t2["id"]}/precedentes', abo,
                           {'tramite_precedente_id': t1['id'], 'criterio_legal': 'Aplica el mismo criterio de plazo',
                            'relevancia': 'ORIENTADOR'}), 'registra precedente')
    esperar(409, pedir('POST', f'/tramites/{t2["id"]}/precedentes', abo,
                       {'tramite_precedente_id': t1['id'], 'criterio_legal': 'x', 'relevancia': 'ORIENTADOR'}),
            'no duplica precedentes')
    d1 = esperar(200, pedir('GET', f'/tramites/{t1["id"]}', sec), 'detalle del tramite')
    ok(d1['citado_por'][0]['tramite']['id'] == t2['id'] and d1['historial'], 'citado_por e historial', d1)
    esperar(204, pedir('DELETE', f'/precedentes/{p["id"]}', abo), 'elimina precedente')

    # ---------- Edicion, archivo y baja ----------
    d = esperar(200, pedir('PUT', f'/tramites/{t1["id"]}', sec, {'observaciones': 'Revisado'}), 'secretaria edita su tramite')
    ok(d['observaciones'] == 'Revisado', 'edicion guardada')
    esperar(403, pedir('PATCH', f'/tramites/{t1["id"]}/archivar', sec), 'secretaria no archiva')
    d = esperar(200, pedir('PATCH', f'/tramites/{t1["id"]}/archivar', jefe), 'jefe archiva')
    ok(d['estado_tramite'] == 'ARCHIVADO', 'queda ARCHIVADO')
    esperar(409, pedir('PATCH', f'/tramites/{t2["id"]}/archivar', jefe), 'no archiva lo que no esta concluido')
    esperar(403, pedir('PATCH', f'/tramites/{t2["id"]}/baja', jefe, {'motivo': 'x'}), 'jefe no da de baja')
    d = esperar(200, pedir('PATCH', f'/tramites/{t2["id"]}/baja', admin, {'motivo': 'Duplicado de prueba'}),
                'admin da de baja')
    ok(d['activo'] is False and d['baja_motivo'] == 'Duplicado de prueba', 'baja logica con motivo')
    esperar(404, pedir('GET', f'/tramites/{t2["id"]}', sec), 'la secretaria ya no lo ve')
    esperar(404, pedir('GET', '/tramites/no-es-un-id', sec), 'id invalido -> 404')

    # ---------- Prompts ----------
    pr = esperar(200, pedir('POST', '/prompts', abo, {'titulo': f'Revisar plazos {SUFIJO}', 'categoria': 'REVISION',
                                                      'texto': 'Revisa los plazos del siguiente documento'}),
                 'abogado propone prompt')
    ok(pr['estado'] == 'BORRADOR', 'queda en borrador')
    esperar(403, pedir('PATCH', f'/prompts/{pr["id"]}/aprobar', abo), 'abogado no aprueba')
    esperar(200, pedir('PATCH', f'/prompts/{pr["id"]}/devolver', jefe, {'observacion': 'Agregue contexto'}), 'jefe devuelve')
    esperar(200, pedir('PUT', f'/prompts/{pr["id"]}', abo, {'texto': 'Revisa los plazos y su base legal'}), 'abogado corrige')
    pr = esperar(200, pedir('PATCH', f'/prompts/{pr["id"]}/aprobar', jefe), 'jefe aprueba')
    ok(pr['estado'] == 'VIGENTE' and pr['aprobado_por']['id'] == cuentas['JEFE']['id'], 'queda VIGENTE')
    esperar(403, pedir('PUT', f'/prompts/{pr["id"]}', abo, {'texto': 'cambio'}), 'abogado no edita un vigente')
    esperar(204, pedir('POST', f'/prompts/{pr["id"]}/uso', sec, {'tramite_id': t1['id']}), 'registra copia')
    vig = esperar(200, pedir('GET', '/prompts?q=plazos', sec), 'catalogo de prompts')
    ok(any(x['id'] == pr['id'] and x['usos'] == 1 for x in vig), 'cuenta el uso', vig)
    esperar(200, pedir('GET', '/prompts/gestion', abo), 'gestion de prompts')

    # ---------- Tablero e inicio ----------
    esperar(403, pedir('GET', '/tablero', abo), 'abogado no ve el tablero')
    tab = esperar(200, pedir('GET', '/tablero', jefe), 'tablero del jefe')
    ok(tab['totales']['total'] >= 1 and len(tab['por_mes']) == 12 and tab['por_abogado'], 'tablero con datos', tab)
    ini = esperar(200, pedir('GET', '/inicio', sec), 'inicio')
    ok(ini['rol'] == 'SECRETARIA' and ini['registrados_por_mi'], 'inicio segun el rol', ini)

    # ---------- Configuracion, fuentes y auditoria ----------
    esperar(422, pedir('PUT', '/configuracion/pdf_max_mb', admin, {'valor': 'mucho'}), 'config valida numeros')
    esperar(200, pedir('PUT', '/configuracion/plazo_dias_tramite', admin, {'valor': '15'}), 'admin fija el plazo')
    esperar(200, pedir('PUT', '/configuracion/plazo_dias_tramite', admin, {'valor': ''}), 'el plazo puede quedar vacio')
    f = esperar(200, pedir('POST', '/fuentes', admin, {'nombre': f'Sitio {SUFIJO}', 'url': 'https://ejemplo.bo',
                                                      'url_busqueda': 'https://ejemplo.bo/buscar?q={q}'}), 'crea sitio legal')
    esperar(200, pedir('PUT', f'/fuentes/{f["id"]}', admin, {'activo': False}), 'desactiva sitio')
    ok(len(esperar(200, pedir('GET', '/fuentes', sec), 'lista sitios')) >= 5, 'sitios iniciales')
    esperar(204, pedir('POST', '/auditoria/eventos', sec, {'accion': 'IMPRIMIR_CONSULTA', 'modulo': 'CONSULTA'}),
            'registra impresion')
    esperar(422, pedir('POST', '/auditoria/eventos', sec, {'accion': 'BORRAR_TODO', 'modulo': 'X'}),
            'no acepta eventos inventados')
    aud = esperar(200, pedir('GET', '/auditoria?accion=SUBIR_INFORME', admin), 'auditoria')
    ok(aud['total'] >= 1, 'la subida quedo auditada', aud)

    # ---------- Unificar catalogo ----------
    dup = esperar(200, pedir('POST', '/catalogos/entidades', admin, {'nombre': f'Gob. Aut. Prueba {SUFIJO}'}), 'duplicado')
    r = esperar(200, pedir('POST', '/catalogos/entidades/unificar', admin, {'conservar': entidad['id'], 'eliminar': dup['id']}),
                'unifica entidades')
    ok(r['movidos'] == 0, 'unificacion hecha', r)
    esperar(403, pedir('POST', '/catalogos/entidades/unificar', sec, {'conservar': 1, 'eliminar': 2}), 'secretaria no unifica')

    # ---------- Importacion del Excel ----------
    try:
        from openpyxl import Workbook
    except ImportError:
        print('aviso: instale openpyxl para probar la importacion (pip install openpyxl)')
    else:
        libro = Workbook()
        hoja = libro.active
        hoja.append(['REGISTRO HISTORICO'])
        hoja.append(['HR', 'RI', 'AÑO', 'PROCEDENCIA', 'ENTIDAD', 'TIPO DE TRAMITE', 'ASUNTO', 'PROFESIONAL',
                     'DOC. SALIDA', 'FECHA SALIDA', 'OBSERVACIONES'])
        hoja.append([f'H-{SUFIJO}-1', 'RI-1', 2024, 'INTERNA', f'Entidad Excel {SUFIJO}', 'Consulta', 'Asunto historico uno',
                     f'DR. HISTORICO {SUFIJO}', 'CGE/SCSL/I-1/2024', '15/03/2024', None])
        hoja.append([f'H-{SUFIJO}-2', None, None, 'INT/EXT', None, None, 'Asunto historico dos', None, None, '31/02/2025', 'dudosa'])
        hoja.append([f'H-{SUFIJO}-1', None, 2023, 'externa', f'Entidad Excel {SUFIJO}', 'Consulta', 'Repite hoja de ruta',
                     None, None, None, None])
        salida = io.BytesIO()
        libro.save(salida)
        xlsx = salida.getvalue()
        tipo_x = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        an = esperar(200, pedir('POST', '/importaciones/analizar', admin, archivos={'archivo': ('historico.xlsx', xlsx, tipo_x)}),
                     'analiza el Excel')
        ok(an['resumen']['filas'] == 3 and an['resumen']['fechas_ilegibles'] == 1
           and an['resumen']['hojas_ruta_repetidas'] == 1, 'detecta filas e incidencias', an)
        sim = esperar(200, pedir('POST', f'/importaciones/{an["id"]}/ejecutar', admin, {'modo': 'SIMULACION'}), 'prueba de migracion')
        ok(sim['simulados'] == 3 and sim['insertados'] == 0, 'la prueba no deja registros', sim)
        dfn = esperar(200, pedir('POST', f'/importaciones/{an["id"]}/ejecutar', admin, {'modo': 'DEFINITIVA'}), 'migracion definitiva')
        ok(dfn['insertados'] == 3 and dfn['rechazados'] == 0, 'migra las filas', dfn)
        an2 = esperar(200, pedir('POST', '/importaciones/analizar', admin, archivos={'archivo': ('historico.xlsx', xlsx, tipo_x)}),
                      'analiza otra vez')
        ok(an2['ya_migrado'] is True, 'avisa que ya se migro')
        esperar(409, pedir('POST', f'/importaciones/{an2["id"]}/ejecutar', admin, {'modo': 'DEFINITIVA'}), 'no migra dos veces')
        hist = esperar(200, pedir('GET', '/importaciones', admin), 'historial de importaciones')
        ok(len(hist) >= 2, 'historial con prueba y definitiva')
        r = esperar(200, pedir('GET', f'/tramites?q=H-{SUFIJO}-1', sec), 'busca migrados')
        ok(r['total'] == 2 and r['items'][0]['origen_registro'] == 'MIGRACION', 'migrados buscables', r)

    # ---------- Perfil, 2FA, recuperacion y cierre ----------
    esperar(200, pedir('PUT', '/perfil', abo, {'nombre_completo': f'Abogada Prueba {SUFIJO}', 'cargo': 'Abogada'}), 'perfil')
    esperar(400, pedir('POST', '/perfil/clave', abo, {'actual': 'mala', 'nueva': 'OtraClave2026'}), 'cambio de clave valida la actual')
    ini2 = esperar(200, pedir('POST', '/perfil/2fa/iniciar', abo), 'inicia 2FA')
    esperar(204, pedir('POST', '/perfil/2fa/confirmar', abo, {'codigo': totp(ini2['secreto'])}), 'confirma 2FA')
    estado, datos = pedir('POST', '/auth/ingresar', cuerpo={'correo': cuentas['ABOGADO']['correo'], 'clave': CLAVE})
    ok(estado == 400 and 'codigo_2fa' in (datos.get('campos') or {}), 'el ingreso pide el segundo factor', datos)
    abo = ingresar(cuentas['ABOGADO']['correo'], CLAVE, codigo_2fa=totp(ini2['secreto']))
    esperar(204, pedir('DELETE', '/perfil/2fa', abo), 'desactiva 2FA')
    correo_sec = cuentas['SECRETARIA']['correo']
    esperar(204, pedir('POST', '/auth/recuperar', cuerpo={'correo': 'nadie@prueba.gob.bo'}), 'recuperar no revela correos')
    esperar(204, pedir('POST', '/auth/recuperar', cuerpo={'correo': correo_sec}), 'pide recuperacion')
    time.sleep(1)
    esperar(204, pedir('POST', '/auth/restablecer', cuerpo={'correo': correo_sec, 'codigo': codigo_del_log(correo_sec),
                                                             'clave': 'NuevaClave#2026'}), 'restablece la clave')
    esperar(401, pedir('GET', '/auth/sesion', sec), 'restablecer cierra las sesiones abiertas')
    sec = ingresar(correo_sec, 'NuevaClave#2026')
    esperar(204, pedir('POST', '/auth/salir', sec), 'cierra sesion')
    esperar(401, pedir('GET', '/auth/sesion', sec), 'el token ya no sirve')

    # ---------- Cambio de correo ----------
    correo_abo, nuevo_abo = cuentas['ABOGADO']['correo'], f'abogada.nueva.{SUFIJO}@prueba.gob.bo'
    otra_sesion_abo = ingresar(correo_abo, CLAVE)
    esperar(400, pedir('POST', '/perfil/correo', abo, {'correo': nuevo_abo, 'clave': 'mala'}), 'cambio de correo pide la clave')
    esperar(422, pedir('POST', '/perfil/correo', abo, {'correo': cuentas['JEFE']['correo'], 'clave': CLAVE}),
            'no toma el correo de otra cuenta')
    esperar(422, pedir('POST', '/perfil/correo', abo, {'correo': 'sin-arroba', 'clave': CLAVE}), 'valida el formato')
    r = esperar(200, pedir('POST', '/perfil/correo', abo, {'correo': nuevo_abo.upper(), 'clave': CLAVE}), 'pide el cambio')
    ok(r['enviado_a'] == nuevo_abo, 'el codigo va a la direccion nueva, en minusculas', r)
    esperar(200, pedir('GET', '/auth/sesion', abo), 'pedirlo no cambia nada todavia')
    esperar(400, pedir('POST', '/perfil/correo/confirmar', abo, {'codigo': '000000'}), 'codigo incorrecto rechazado')
    esperar(400, pedir('POST', '/perfil/correo/confirmar', jefe, {'codigo': codigo_del_log(nuevo_abo)}),
            'el codigo de otra persona no sirve')
    d = esperar(200, pedir('POST', '/perfil/correo/confirmar', abo, {'codigo': codigo_del_log(nuevo_abo)}), 'confirma el cambio')
    ok(d['correo'] == nuevo_abo, 'queda el correo nuevo', d)
    esperar(200, pedir('GET', '/auth/sesion', abo), 'la sesion actual sigue abierta')
    esperar(401, pedir('GET', '/auth/sesion', otra_sesion_abo), 'las otras sesiones se cierran')
    esperar(401, pedir('POST', '/auth/ingresar', cuerpo={'correo': correo_abo, 'clave': CLAVE}), 'el correo anterior ya no ingresa')
    abo = ingresar(nuevo_abo, CLAVE)
    esperar(409, pedir('PUT', f'/usuarios/{yo["id"]}', admin, {'correo': f'otro.{SUFIJO}@prueba.gob.bo'}),
            'el admin cambia su propio correo solo desde su perfil')
    esperar(403, pedir('PUT', f'/usuarios/{cuentas["JEFE"]["id"]}', abo, {'correo': f'x.{SUFIJO}@prueba.gob.bo'}),
            'sin GESTIONAR_USUARIOS no cambia correos ajenos')
    esperar(422, pedir('PUT', f'/usuarios/{cuentas["JEFE"]["id"]}', admin, {'correo': nuevo_abo}), 'admin: correo ya usado')
    nuevo_jefe = f'jefe.nuevo.{SUFIJO}@prueba.gob.bo'
    d = esperar(200, pedir('PUT', f'/usuarios/{cuentas["JEFE"]["id"]}', admin, {'correo': nuevo_jefe}), 'admin cambia el correo')
    ok(d['correo'] == nuevo_jefe and d['correo_verificado'] is False, 'la cuenta queda pendiente de activacion', d)
    esperar(401, pedir('GET', '/auth/sesion', jefe), 'se cierran las sesiones de esa persona')
    esperar(403, pedir('POST', '/auth/ingresar', cuerpo={'correo': nuevo_jefe, 'clave': CLAVE}), 'debe activar antes de ingresar')
    esperar(204, pedir('POST', '/auth/activar', cuerpo={'correo': nuevo_jefe, 'codigo': codigo_del_log(nuevo_jefe),
                                                         'clave': 'JefeNueva#2026'}), 'activa con el correo nuevo')
    jefe = ingresar(nuevo_jefe, 'JefeNueva#2026')
    aud = esperar(200, pedir('GET', '/auditoria?accion=CAMBIAR_CORREO', admin), 'auditoria del cambio')
    ok(aud['total'] >= 2, 'el cambio de correo queda auditado', aud)

    esperar(200, pedir('PATCH', f'/usuarios/{cuentas["SECRETARIA"]["id"]}/activo', admin, {'activo': False}), 'desactiva usuario')
    esperar(401, pedir('POST', '/auth/ingresar', cuerpo={'correo': correo_sec, 'clave': 'NuevaClave#2026'}),
            'usuario desactivado no ingresa')
    print('\n=== TODAS LAS PRUEBAS DE LA API PASARON ===')


if __name__ == '__main__':
    main()

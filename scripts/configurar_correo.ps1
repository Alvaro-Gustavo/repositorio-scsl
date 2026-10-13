# ============================================================
# REPOSITORIO SCSL - Configurar el envío de correos (SMTP) en los 3 proyectos.
#
# Uso (PowerShell, desde cualquier carpeta):
#   powershell -ExecutionPolicy Bypass -File C:\Users\PC\Desktop\repositorio-scsl\scripts\configurar_correo.ps1
#
# Pide el correo y la contraseña de aplicación (sin mostrarla), la escribe en el .env de
# la base, la opción A y la opción B, reinicia sus backends y envía un correo de prueba.
# La clave solo queda en los .env (excluidos de git); nunca se muestra en pantalla.
#
# Gmail: active la verificación en dos pasos y cree una contraseña de aplicación en
# https://myaccount.google.com/apppasswords (la clave normal de Gmail NO funciona).
# Otro servidor (correo institucional): indique su servidor y puerto cuando se pidan.
# ============================================================
$ErrorActionPreference = 'Stop'

function Docker-Silencioso {
    # Docker escribe su progreso en stderr; en PowerShell 5.1 eso no debe cortar el script.
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $salida = & docker @args 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $anterior }
    return ,@($salida)
}

$escritorio = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$proyectos = @(
    @{ Nombre = 'Base';     Carpeta = 'repositorio-scsl';          Prefijo = 'scsl'  },
    @{ Nombre = 'Opcion A'; Carpeta = 'repositorio-scsl-opcion-a'; Prefijo = 'scsla' },
    @{ Nombre = 'Opcion B'; Carpeta = 'repositorio-scsl-opcion-b'; Prefijo = 'scslb' }
) | Where-Object { Test-Path (Join-Path (Join-Path $escritorio $_.Carpeta) '.env') }

if (-not $proyectos) { throw "No se encontró ningún .env de los proyectos en $escritorio" }
Write-Host "Proyectos encontrados: $(($proyectos | ForEach-Object { $_.Nombre }) -join ', ')"

$correo = (Read-Host 'Correo que enviará los mensajes (ej. su_cuenta@gmail.com)').Trim().ToLower()
if ($correo -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') { throw 'El correo no es válido.' }

$servidor = 'smtp.gmail.com'; $puerto = '587'
if ($correo -notmatch '@gmail\.com$') {
    $servidor = (Read-Host 'Servidor SMTP (ej. mail.contraloria.gob.bo)').Trim()
    $p = (Read-Host 'Puerto SMTP [587]').Trim()
    if ($p) { $puerto = $p }
}

$segura = Read-Host 'Contraseña de aplicación (no se mostrará)' -AsSecureString
$puntero = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
try { $clave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($puntero) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($puntero) }
if ($servidor -eq 'smtp.gmail.com') { $clave = $clave -replace '\s', '' }  # Google la muestra en grupos de 4
if (-not $clave) { throw 'La contraseña está vacía.' }
if ($clave -match '[\r\n#"]') { throw 'La contraseña tiene caracteres que el .env no admite (#, comillas o saltos de línea).' }

$valores = [ordered]@{
    SMTP_HOST = $servidor; SMTP_PUERTO = $puerto; SMTP_USUARIO = $correo
    SMTP_CLAVE = $clave; SMTP_REMITENTE = $correo; SMTP_TLS = 'si'
}
$utf8 = New-Object System.Text.UTF8Encoding($false)  # sin BOM: Docker Compose no lo admite

foreach ($p in $proyectos) {
    $raiz = Join-Path $escritorio $p.Carpeta
    $archivo = Join-Path $raiz '.env'
    $lineas = [Collections.Generic.List[string]]([IO.File]::ReadAllLines($archivo, $utf8))
    foreach ($k in $valores.Keys) {
        $i = -1
        for ($j = 0; $j -lt $lineas.Count; $j++) { if ($lineas[$j].StartsWith("$k=")) { $i = $j; break } }
        if ($i -ge 0) { $lineas[$i] = "$k=$($valores[$k])" } else { $lineas.Add("$k=$($valores[$k])") }
    }
    [IO.File]::WriteAllLines($archivo, $lineas, $utf8)
    Write-Host "[$($p.Nombre)] .env actualizado. Reiniciando el backend..."

    Push-Location $raiz
    try {
        $salida = Docker-Silencioso compose up -d
        if ($LASTEXITCODE -ne 0) { $salida | Select-Object -Last 5 | ForEach-Object { Write-Host "    $_" }; throw "No se pudo reiniciar $($p.Nombre)." }
    } finally { Pop-Location }
}

Write-Host 'Esperando que los backends arranquen...'
Start-Sleep -Seconds 15

$prueba = @'
import os
from app import config
from app.correo import enviar
enviar(os.environ['DESTINO'], f"{config.NOMBRE_SISTEMA} ({os.environ['PROYECTO']}): correo de prueba",
       'Si recibe este mensaje, el envio de correos del repositorio funciona.')
print('enviado')
'@
$fallos = 0
foreach ($p in $proyectos) {
    $anterior = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $salida = $prueba | & docker exec -i -e "DESTINO=$correo" -e "PROYECTO=$($p.Nombre)" "$($p.Prefijo)_app" python - 2>&1 | ForEach-Object { "$_" } }
    finally { $ErrorActionPreference = $anterior }
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[$($p.Nombre)] Correo de prueba enviado a $correo" -ForegroundColor Green
    } else {
        $fallos++
        Write-Host "[$($p.Nombre)] No se pudo enviar:" -ForegroundColor Red
        $salida | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" }
    }
}
if ($fallos) {
    Write-Host ''
    Write-Host 'Revise: verificación en dos pasos activa, contraseña de APLICACIÓN (no la normal) y que el contenedor esté corriendo.'
    exit 1
}
Write-Host ''
Write-Host 'Listo. Use "Reenviar activación" en Administración -> Usuarios para los que esperan su código.'

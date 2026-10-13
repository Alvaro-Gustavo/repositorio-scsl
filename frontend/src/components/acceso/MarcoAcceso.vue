<script setup>
// Marco de pantalla completa para ingreso, activacion y recuperacion de cuenta.
// <MarcoAcceso titulo="Bienvenido" subtitulo="...">formulario<template #pie>enlaces</template></MarcoAcceso>
//
// Imagen institucional en public/marca/ (ver LEAME.txt):
//   emblema-blanco.png -> emblema de la CGE sobre la foto
//   emblema.png        -> emblema en el azul oficial, dentro de la tarjeta
//   fondo-acceso.jpg   -> foto del edificio
// Si falta un archivo se usa el escudo del sistema o el fondo azul compuesto.
// Al reemplazar una imagen, suba ?v= aqui y en el estilo: el navegador la pide de nuevo aunque tenga la anterior en cache.
import { ref } from 'vue'
import { ShieldCheck, Lock } from '@lucide/vue'

defineProps({ titulo: { type: String, required: true }, subtitulo: { type: String, default: '' } })

const RESPALDO = '/escudo.svg'
const VERSION = '2026-10-13'
const emblemaClaro = ref(`/marca/emblema-blanco.png?v=${VERSION}`)
const emblemaTarjeta = ref(`/marca/emblema.png?v=${VERSION}`)
</script>

<template>
  <div class="acceso">
    <div class="fondo" aria-hidden="true">
      <div class="fondo-foto" />
      <div class="fondo-velo" />
      <div class="fondo-franjas"><span /><span /><span /></div>
      <svg class="fondo-onda" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path class="onda-luz" d="M0 170 C 320 110 620 120 900 190 C 1120 245 1300 250 1440 220 L1440 320 L0 320 Z" />
        <path class="onda-media" d="M0 215 C 300 160 640 175 920 235 C 1140 280 1310 285 1440 262 L1440 320 L0 320 Z" />
        <path class="onda-tinta" d="M0 250 C 320 205 660 220 940 270 C 1150 305 1320 308 1440 292 L1440 320 L0 320 Z" />
      </svg>
    </div>

    <section class="marca" aria-label="Contraloría General del Estado">
      <div class="marca-sello">
        <img :src="emblemaClaro" alt="" class="marca-logo" @error="emblemaClaro = RESPALDO" />
        <div class="marca-nombre">
          <p class="marca-linea-1">Contraloría</p>
          <p class="marca-linea-2">General del Estado</p>
          <p class="marca-linea-3">Estado Plurinacional de Bolivia</p>
        </div>
      </div>
      <div class="marca-sistema">
        <p class="marca-sistema-nombre">Repositorio SCSL</p>
        <p class="marca-sistema-unidad">Subcontraloría de Servicios Legales</p>
        <p class="marca-sistema-texto">Registro, consulta y precedentes de los trámites legales, en un solo lugar.</p>
      </div>
      <p class="marca-lema"><span class="marca-lema-raya" />Transparencia, control <br />y buen gobierno</p>
    </section>

    <main class="panel-acceso">
      <div class="tarjeta">
        <div class="tarjeta-marca">
          <img :src="emblemaTarjeta" alt="" class="tarjeta-logo" @error="emblemaTarjeta = RESPALDO" />
          <div>
            <p class="tarjeta-linea-1">Contraloría</p>
            <p class="tarjeta-linea-2">General del Estado</p>
            <p class="tarjeta-linea-3">Estado Plurinacional de Bolivia</p>
          </div>
        </div>

        <header class="tarjeta-cabecera">
          <h1>{{ titulo }}</h1>
          <p v-if="subtitulo">{{ subtitulo }}</p>
        </header>

        <slot />

        <div v-if="$slots.pie" class="tarjeta-enlaces"><slot name="pie" /></div>

        <footer class="tarjeta-pie">
          <p><ShieldCheck aria-hidden="true" /> Repositorio SCSL · Sistema de gestión institucional</p>
          <p class="tarjeta-pie-nota"><Lock aria-hidden="true" /> Acceso solo desde la red interna de la institución</p>
        </footer>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Colores propios de esta pantalla: derivados de la tinta y el sello institucional. */
.acceso {
  --acceso-cielo: color-mix(in srgb, var(--sello) 35%, var(--texto-inverso));
  --acceso-vidrio: rgba(255, 255, 255, 0.9);
  position: relative; isolation: isolate; min-height: 100vh; overflow: hidden;
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(380px, 470px);
  gap: var(--e-10); align-items: center;
  padding: var(--e-10) clamp(var(--e-6), 5vw, 88px);
  background: var(--cge-oscuro); color: var(--texto-inverso);
}

/* ---------- Fondo ---------- */
.fondo { position: absolute; inset: 0; z-index: -1; }
.fondo-foto {
  position: absolute; inset: 0;
  background:
    url('/marca/fondo-acceso.jpg?v=2026-10-13') 42% 40% / cover no-repeat,
    radial-gradient(120% 90% at 20% 0%, var(--acceso-cielo) 0%, var(--sello) 38%, var(--tinta-2) 70%, var(--tinta) 100%);
}
/* Velo azul: garantiza que el texto se lea con cualquier foto. */
.fondo-velo {
  position: absolute; inset: 0;
  background:
    linear-gradient(100deg, color-mix(in srgb, var(--cge-oscuro) 86%, transparent) 0%,
                            color-mix(in srgb, var(--cge-oscuro) 62%, transparent) 38%,
                            color-mix(in srgb, var(--cge) 22%, transparent) 72%,
                            color-mix(in srgb, var(--cge) 8%, transparent) 100%),
    linear-gradient(180deg, transparent 55%, color-mix(in srgb, var(--tinta) 45%, transparent) 100%);
}
.fondo-franjas { position: absolute; inset: 0; overflow: hidden; }
.fondo-franjas span {
  position: absolute; top: -20%; height: 140%; transform: skewX(-24deg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.02));
}
.fondo-franjas span:nth-child(1) { right: 6%; width: 120px; }
.fondo-franjas span:nth-child(2) { right: 18%; width: 48px; opacity: 0.7; }
.fondo-franjas span:nth-child(3) { right: -4%; width: 220px; opacity: 0.5; }
.fondo-onda { position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: 34vh; min-height: 200px; }
.onda-luz { fill: rgba(255, 255, 255, 0.14); }
.onda-media { fill: color-mix(in srgb, var(--cge) 70%, transparent); }
.onda-tinta { fill: var(--cge-oscuro); }

/* ---------- Marca (izquierda) ---------- */
.marca { text-shadow: 0 1px 12px rgba(4, 18, 36, 0.45); align-self: stretch; display: flex; flex-direction: column; justify-content: space-between; gap: var(--e-10); min-width: 0; }
.marca-sello { display: flex; align-items: center; gap: var(--e-6); }
.marca-logo { width: clamp(96px, 10vw, 140px); height: auto; flex: none; filter: drop-shadow(0 6px 18px rgba(0, 0, 0, 0.25)); }
.marca-nombre { text-transform: uppercase; line-height: 1.05; }
.marca-linea-1 { font-size: clamp(2rem, 4.4vw, 3.6rem); font-weight: 800; letter-spacing: 0.01em; }
.marca-linea-2 { font-size: clamp(1.15rem, 2.5vw, 2.05rem); font-weight: 700; letter-spacing: 0.02em; padding-bottom: var(--e-3); border-bottom: 3px solid var(--texto-inverso); }
.marca-linea-3 { margin-top: var(--e-3); font-size: clamp(0.8rem, 1.25vw, 1.05rem); font-weight: 600; letter-spacing: 0.06em; color: color-mix(in srgb, var(--texto-inverso) 88%, transparent); }
.marca-sistema { max-width: 40ch; padding-left: var(--e-5); border-left: 3px solid color-mix(in srgb, var(--texto-inverso) 55%, transparent); }
.marca-sistema-nombre { font-family: var(--fuente-titulo); font-size: var(--t-2xl); font-weight: 600; }
.marca-sistema-unidad { font-size: var(--t-md); font-weight: 600; color: color-mix(in srgb, var(--texto-inverso) 85%, transparent); }
.marca-sistema-texto { margin-top: var(--e-3); font-size: var(--t-md); line-height: 1.5; color: color-mix(in srgb, var(--texto-inverso) 85%, transparent); }
.marca-lema { display: flex; align-items: flex-start; gap: var(--e-4); font-size: clamp(1.1rem, 1.8vw, 1.5rem); font-style: italic; font-weight: 500; line-height: 1.3; }
.marca-lema-raya { width: 48px; height: 3px; margin-top: 0.7em; flex: none; border-radius: 2px; background: var(--acceso-cielo); }

/* ---------- Tarjeta (derecha) ---------- */
.panel-acceso { display: flex; justify-content: center; }
.tarjeta {
  width: 100%; padding: var(--e-10) var(--e-10) var(--e-6);
  background: var(--acceso-vidrio); color: var(--texto);
  border: 1px solid rgba(255, 255, 255, 0.7); border-radius: 18px;
  box-shadow: 0 30px 60px rgba(8, 22, 45, 0.35), 0 2px 6px rgba(8, 22, 45, 0.12);
  backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%);
  animation: entrar 420ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.tarjeta-marca { display: flex; align-items: center; justify-content: center; gap: var(--e-3); color: var(--cge); text-transform: uppercase; line-height: 1.1; }
.tarjeta-logo { width: 54px; height: auto; flex: none; }
.tarjeta-linea-1 { font-size: 1.35rem; font-weight: 800; }
.tarjeta-linea-2 { font-size: 0.9rem; font-weight: 700; padding-bottom: 3px; border-bottom: 2px solid var(--cge); }
.tarjeta-linea-3 { margin-top: 3px; font-size: 0.62rem; font-weight: 600; letter-spacing: 0.04em; color: var(--texto-2); }

.tarjeta-cabecera { margin: var(--e-8) 0 var(--e-6); }
.tarjeta-cabecera h1 { font-family: var(--fuente-texto); font-size: var(--t-3xl); font-weight: 750; color: var(--cge-oscuro); letter-spacing: -0.01em; }
.tarjeta-cabecera p { margin-top: var(--e-1); color: var(--texto-2); }

.tarjeta-enlaces { margin-top: var(--e-5); font-size: var(--t-sm); }
.tarjeta-pie { margin-top: var(--e-6); padding-top: var(--e-4); border-top: 1px solid var(--linea); text-align: center; font-size: var(--t-xs); color: var(--texto-2); }
.tarjeta-pie p { display: flex; align-items: center; justify-content: center; gap: 6px; }
.tarjeta-pie svg { width: 16px; height: 16px; flex: none; color: var(--sello); }
.tarjeta-pie-nota { margin-top: 4px; color: var(--texto-3); }
.tarjeta-pie-nota svg { width: 13px; height: 13px; color: var(--texto-3); }

/* Controles un poco mas amplios dentro de la tarjeta */
.tarjeta :deep(.entrada) { min-height: 48px; border-radius: 10px; background: var(--superficie); }
.tarjeta :deep(.boton-primario) { min-height: 50px; border-radius: 10px; background: var(--cge); border-color: var(--cge); font-size: var(--t-lg); font-weight: 650; }
.tarjeta :deep(.boton-primario:hover:not(:disabled)) { background: var(--cge-oscuro); border-color: var(--cge-oscuro); }
.tarjeta :deep(.entrada:focus) { border-color: var(--cge); }

@keyframes entrar { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .tarjeta { animation: none; } }

/* ---------- Pantallas medianas y celulares ---------- */
@media (max-width: 1020px) {
  .acceso { grid-template-columns: 1fr; justify-items: center; gap: var(--e-6); padding: var(--e-8) var(--e-4) var(--e-10); }
  .marca { align-self: auto; width: 100%; max-width: 470px; gap: 0; }
  .marca-sello { justify-content: center; gap: var(--e-4); }
  .marca-logo { width: 64px; }
  .marca-linea-1 { font-size: 1.6rem; }
  .marca-linea-2 { font-size: 0.95rem; border-bottom-width: 2px; padding-bottom: 4px; }
  .marca-linea-3 { font-size: 0.68rem; margin-top: 4px; }
  .marca-sistema, .marca-lema { display: none; }
  .panel-acceso { width: 100%; max-width: 470px; }
  .tarjeta-marca { display: none; }
  .tarjeta-cabecera { margin-top: 0; }
}
@media (max-width: 480px) {
  .tarjeta { padding: var(--e-6) var(--e-5) var(--e-5); border-radius: 14px; }
  .tarjeta-cabecera h1 { font-size: var(--t-2xl); }
}
</style>

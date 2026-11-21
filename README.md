# Horror Karting

Karting de terror para la consola **Toxinator**. Ocho monstruos, un cementerio,
pantalla dividida para 2–4 celulares y volante físico: se dobla girando el
teléfono como un volante.

```text
horror-karting/
├── src/horror_karting/
│   ├── __init__.py          create_game()
│   ├── manifest.toml
│   ├── game.py              estados, cámaras, HUD, menús
│   ├── sim.py               física 2.5D, IA, ítems, vueltas
│   ├── track.py             spline del circuito y consultas
│   ├── scenery.py           cielo, pista, cementerio, puente, túnel
│   ├── karts.py             modelos de kart y personajes
│   ├── effects.py           cajas, aceite, proyectiles y partículas
│   ├── controls.py          volante físico, stick y botones
│   ├── view.py              pantalla dividida y cámaras
│   ├── hud.py               HUD por jugador y minimapa
│   ├── screens.py           título, selección, pausa y podio
│   ├── audio.py             música, motor y efectos procedurales
│   └── characters.py        plantel y estadísticas
└── tests/                   tests puros de pista, simulación y controles
```

## Jugar

Desde el repo de la consola:

```bash
cd /home/ska/Projects/toxinator
uv run toxinator play horror-karting
uv run toxinator play horror-karting --demo
uv run toxinator play horror-karting --demo --offscreen \
  --screenshot /tmp/horror-karting.png --screenshot-after 3 --seconds 6
```

El juego ya vive en `~/Projects/toxinator-games/horror-karting`, así que el
launcher lo descubre al iniciar. Si se mueve, `toxinator install .`.

## Controles

| Botón | Carrera | Menú |
|---|---|---|
| Girar el teléfono | Volante (si hay sensores) | — |
| Stick izquierdo | Volante de respaldo | Navegar |
| × | Acelerar | Sumarse / elegir / confirmar |
| □ | Frenar / derrapar | Pista espejada (podio) |
| △ | Usar ítem | Al azar (selección) |
| R1 | Cambiar cámara | — |
| L1 | Mirar atrás | — |
| options | Pausa | Largar / reanudar / volver |

En el título: **×** suma un jugador, **options** larga, **△** inicia un
contrarreloj y el stick izquierdo/derecho cambia la dificultad. Cada humano
necesita su celular (slots 0–3); el teclado simula un jugador más (slot 4).
**○** es de la plataforma: vuelve al launcher y no se usa en el juego.

El teléfono va en **horizontal**. Al empezar la cuenta atrás se toma la pose
actual como volante recto; en la pausa están *Sensibilidad*, *Invertir* y
*Centrar volantes*. Sin sensores (HTTP) el stick funciona sin avisos.

Referencia visual de orientaciones, movimientos y sensores:
[`docs/controles-celular.html`](docs/controles-celular.html).

## Carrera

- **Cementerio del Pueblo**: circuito de ~1,6 km con panteón, chicane de
  lápidas, puente de niebla, túnel de mausoleo, bosque, salto sobre la fosa y
  recta de calabazas. Tres vueltas.
- **1–4 jugadores** en pantalla dividida (1: pantalla completa; 2: arriba/abajo;
  3–4: cuadrantes) y la IA completa la grilla de 8.
- **8 personajes**: Drácula, Frankenstein, La Momia, Hombre Lobo, Fantasma de la
  Ópera, La Llorona, Javier Milei «El Gatito Mimoso» y Kuchisake-onna.
- **Ítems**: nitro, aceite, bomba calabaza, escudo ataúd, telaraña y la
  motosierra exclusiva de Milei. La posición en carrera sesga la ruleta.
- **Cámaras**: cerca, lejos, capó y cenital, con mirar atrás y transiciones
  suaves.
- **Contrarreloj**: tres vueltas sin rivales, mejor vuelta y récord de sesión.
- **Pista espejada**: después del podio, con □, se corre el circuito al revés.
- **Pausa**: sensibilidad e inversión del volante, centrado, mute, reinicio y
  vuelta al título. La pausa congela a todos y reanuda con cuenta atrás.

La carrera termina cuando terminan todos los humanos (o 30 s después del
primero). En el podio, los que no llegaron muestran un tiempo estimado con `~`.

## Tests

Los tests no necesitan ventana ni GPU (solo el paquete `toxinator.api` del
runtime de la consola):

```bash
cd /home/ska/Projects/toxinator
PYTHONPATH=/home/ska/Projects/toxinator-games/horror-karting/src \
  uv run pytest /home/ska/Projects/toxinator-games/horror-karting/tests -q
```

## Notas de desarrollo

- Todo el arte es geometría procedural y todo el audio se sintetiza a WAV al
  iniciar. No hay assets externos.
- La pista se recorre en coordenadas `(s, t)`: la simulación no depende de
  Bullet y es determinista con semilla.
- `HK_DEV_STATE=race|race2|race3|race4|select|podium|pause|countdown|trial_results|mirror`
  arranca directo en ese estado para sacar screenshots con `--offscreen`.
- La simulación, la pista y los controles son módulos puros; la vista y el HUD
  son la única capa que toca Panda3D.

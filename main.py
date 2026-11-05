import math
import os
import random
import string
import sys
from functools import lru_cache

import pygame

try:
    import pyttsx3
except ImportError:   # en Android (o sin instalar) el juego usa solo los audios pregrabados
    pyttsx3 = None

# ============================
# Inicialización
# ============================
pygame.init()
engine = pyttsx3.init() if pyttsx3 else None   # voz de respaldo cuando no hay audio pregrabado

BASE = os.path.dirname(__file__)
ruta_sonidos = os.path.join(BASE, "assets", "sonidos")
ruta_audios = os.path.join(BASE, "assets", "audios")      # voces pregrabadas (gTTS)
ruta_img = os.path.join(BASE, "assets", "imagenes")
RUTA_FUENTE = os.path.join(BASE, "assets", "fuentes", "Baloo2.ttf")

# ---- Estado global del juego ----
palabra_mostrada = ""       # la palabra se muestra solo cuando se acierta
modo_libre = False          # sin vidas y con todos los niveles abiertos (práctica sin presión)
audio_activado = True       # interruptor maestro: música, efectos y voz
vidas, indice, datos_nivel = 5, 0, []   # nivel en curso (los lee mostrar_pantalla)

# ---- Audio ----
VOLUMEN_MUSICA, VOLUMEN_EFECTOS = 0.05, 0.7
ruta_musica = os.path.join(ruta_sonidos, "musica_fondo.mp3")
if os.path.exists(ruta_musica):
    pygame.mixer.music.load(ruta_musica)
    pygame.mixer.music.play(-1)  # -1 = repetir infinitamente
sonido_correcto = pygame.mixer.Sound(os.path.join(ruta_sonidos, "correcto.wav"))
sonido_error = pygame.mixer.Sound(os.path.join(ruta_sonidos, "error.wav"))
canal_efectos = pygame.mixer.Channel(1)
canal_voz = pygame.mixer.Channel(0)   # la voz va en su propio canal: así no corta la música de fondo
_cache_voces = {}                     # ruta -> Sound ya cargado (cada mp3 se lee una sola vez)


def aplicar_estado_audio():
    """Silencia o restaura música y efectos según 'audio_activado' (la voz se controla en reproducir_audio)."""
    factor = 1 if audio_activado else 0
    pygame.mixer.music.set_volume(VOLUMEN_MUSICA * factor)
    for efecto in (sonido_correcto, sonido_error):
        efecto.set_volume(VOLUMEN_EFECTOS * factor)


aplicar_estado_audio()

# ---- Pantalla completa ----
reloj = pygame.time.Clock()  # limita los FPS para no gastar CPU de más
info = pygame.display.Info()
ANCHO, ALTO = info.current_w, info.current_h
pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.FULLSCREEN)
pygame.display.set_caption("Juego del Abecedario")

# ============================
# Paleta de colores unificada (tonos pastel que combinan con el fondo)
# ============================
PALETA = {
    "verde_activo":         (108, 189, 134),   # estados activados, niveles desbloqueados
    "verde_activo_hover":   (128, 206, 153),
    "azul_principal":       (94, 158, 214),    # botón Jugar, interruptor de sonido
    "azul_principal_hover": (118, 178, 230),
    "rosa_suave":           (224, 122, 122),   # botón Salir
    "rosa_suave_hover":     (235, 146, 146),
    "gris_bloqueado":       (176, 176, 176),   # niveles bloqueados, estados inactivos
    "dorado_completado":    (232, 192, 90),    # borde de nivel completado
    "texto_oscuro":         (60, 60, 70),
    "texto_claro":          (255, 255, 255),
    "texto_bloqueado":      (90, 90, 90),
    "azul_aviso":           (0, 102, 204),     # avisos e infinito del modo libre
}

# Colores pastel para las letras grandes
COLORES_LETRAS = [
    (224, 122, 122),   # rojo
    (108, 189, 134),   # verde
    (94, 158, 214),    # azul
    (232, 160, 96),    # naranja
    (170, 128, 196),   # morado
    (232, 192, 90),    # amarillo
]


# ============================
# Utilidades generales
# ============================
@lru_cache(maxsize=None)
def cargar_fuente(tamaño, bold=True):
    """
    Fuente propia del juego (Baloo2, incluida en assets/fuentes para que se vea igual en
    Windows, Mac y Linux). Si falta el archivo usa Comic Sans del sistema. Cada tamaño
    se crea una sola vez (lru_cache), así que se puede llamar en cada fotograma.
    """
    if os.path.exists(RUTA_FUENTE):
        fuente = pygame.font.Font(RUTA_FUENTE, tamaño)
        fuente.set_bold(bold)
        return fuente
    return pygame.font.SysFont("Comic Sans MS", tamaño, bold=bold)


def salir():
    pygame.quit()
    sys.exit()


def eventos():
    """Entrega los eventos pendientes y cierra el juego si se cierra la ventana."""
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            salir()
        yield evento


def pausa_activa(ms):
    """Espera sin congelar la ventana: atiende el cierre y descarta los clics acumulados."""
    espera, restante = pygame.time.Clock(), ms
    while restante > 0:
        for _ in eventos():
            pass
        restante -= espera.tick(60)


def reproducir_audio(ruta, esperar=True):
    """
    Reproduce un mp3 pregrabado (respetando el interruptor de sonido). Con esperar=True
    no regresa hasta que termina, sin congelar la ventana.
    Devuelve True si el archivo existe, False si no (el llamador usa entonces la voz de respaldo).
    """
    if not os.path.exists(ruta):
        return False
    if not audio_activado:
        return True
    if ruta not in _cache_voces:
        _cache_voces[ruta] = pygame.mixer.Sound(ruta)
    canal_voz.play(_cache_voces[ruta])
    espera = pygame.time.Clock()
    while esperar and canal_voz.get_busy():
        for _ in eventos():
            pass
        espera.tick(30)
    return True


def _nombre_audio(texto):
    """Nombre del mp3 pregrabado que corresponde a la frase, o None si no hay."""
    bajo = texto.lower()
    if texto.startswith("¿Cuál imagen empieza con la letra "):
        return f"pregunta_{texto.split('letra ')[1].replace('?', '')}.mp3"
    if texto.startswith("¡Correcto!"):
        partes = texto.replace("¡Correcto! ", "").split(" de ")
        return f"correcto_{partes[0].strip()}_{partes[1].strip()}.mp3" if len(partes) == 2 else None
    if bajo == "intenta otra vez":
        return "intenta_otra_vez.mp3"
    if "se acabaron tus vidas" in bajo:
        return "vidas_terminadas.mp3"
    if "felicidades" in bajo:
        return "felicidades.mp3"
    if texto.strip().isalnum():  # palabra suelta
        return texto.strip() + ".mp3"
    return None


def hablar(texto):
    """Dice la frase con su mp3 pregrabado; si no existe, con la voz del sistema (pyttsx3)."""
    if not audio_activado:
        return
    try:
        nombre = _nombre_audio(texto)
        if nombre and reproducir_audio(os.path.join(ruta_audios, nombre)):
            return
    except Exception as e:
        print(f"Error al reproducir voz: {e}")
    if engine:
        engine.say(texto)
        engine.runAndWait()


def blit_en(superficie, **ancla):
    """Dibuja una superficie anclada por su centro, midtop, etc.: blit_en(txt, center=(x, y))."""
    pantalla.blit(superficie, superficie.get_rect(**ancla))


def dibujar_boton(rect, texto, color, fuente, color_texto=PALETA["texto_claro"], radio=25,
                  borde=0, color_borde=(0, 0, 0)):
    """Botón redondeado con el texto centrado (y borde opcional)."""
    pygame.draw.rect(pantalla, color, rect, border_radius=radio)
    if borde:
        pygame.draw.rect(pantalla, color_borde, rect, borde, border_radius=radio)
    if texto:
        blit_en(fuente.render(texto, True, color_texto), center=rect.center)


def color_hover(nombre, rect):
    """Color de la paleta, en su versión 'hover' si el mouse está sobre el botón."""
    return PALETA[nombre + "_hover"] if rect.collidepoint(pygame.mouse.get_pos()) else PALETA[nombre]


def dibujar_interruptor(rect, texto, color, icono, **kw_icono):
    """Botón de encendido/apagado: ícono + texto centrados juntos dentro del botón."""
    dibujar_boton(rect, "", color, None, borde=3)
    render = cargar_fuente(32).render(texto, True, PALETA["texto_claro"])
    x0 = rect.centerx - (34 + 14 + render.get_width()) // 2   # 34 = ancho del ícono, 14 = espacio
    icono(pantalla, x0 + 17, rect.centery, color=PALETA["texto_claro"], **kw_icono)
    pantalla.blit(render, (x0 + 48, rect.centery - render.get_height() // 2))


# Imágenes
def cargar_img(nombre, tam):
    return pygame.transform.smoothscale(pygame.image.load(os.path.join(ruta_img, nombre)).convert_alpha(), tam)


fondo = pygame.transform.scale(pygame.image.load(os.path.join(ruta_img, "Fondo.png")).convert(), (ANCHO, ALTO))
palomita_img = cargar_img("palomita.png", (250, 250))
tachita_img = cargar_img("tachita.png", (250, 250))
corazon_img = cargar_img("corazon.png", (40, 40))

TAM_AVATAR = (250, 250)


def escalar_imagen_con_proporcion(imagen, max_ancho, max_alto):
    ancho, alto = imagen.get_size()
    proporcion = min(max_ancho / ancho, max_alto / alto)
    return pygame.transform.smoothscale(imagen, (int(ancho * proporcion), int(alto * proporcion)))


def cargar_avatar(nombre):
    """Avatar escalado y centrado en un lienzo fijo (None si el archivo no existe)."""
    ruta = os.path.join(ruta_img, nombre)
    if not os.path.exists(ruta):
        return None
    imagen = escalar_imagen_con_proporcion(pygame.image.load(ruta).convert_alpha(), *TAM_AVATAR)
    lienzo = pygame.Surface(TAM_AVATAR, pygame.SRCALPHA)
    lienzo.blit(imagen, imagen.get_rect(center=(TAM_AVATAR[0] // 2, TAM_AVATAR[1] // 2)))
    return lienzo


AVATARES = {estado: cargar_avatar(f"avatar_{estado}.png") for estado in ("feliz", "triste", "animo")}

_cache_imagenes = {}  # (nombre, tamaño) -


def cargar_imagen(nombre, tamaño=(300, 300)):
    """Imagen de una opción dentro de un círculo blanco. Se procesa una sola vez (caché)."""
    clave = (nombre, tamaño)
    if clave in _cache_imagenes:
        return _cache_imagenes[clave]
    ruta = os.path.join(ruta_img, nombre)
    try:
        imagen = escalar_imagen_con_proporcion(pygame.image.load(ruta).convert_alpha(), tamaño[0] - 50, tamaño[1] - 50)
        centro, radio = (tamaño[0] // 2, tamaño[1] // 2), tamaño[0] // 2
        redonda = pygame.Surface(tamaño, pygame.SRCALPHA)
        pygame.draw.circle(redonda, (255, 255, 255, 255), centro, radio)
        redonda.blit(imagen, imagen.get_rect(center=centro))
        mascara = pygame.Surface(tamaño, pygame.SRCALPHA)       # recorta lo que sobresale del círculo
        pygame.draw.circle(mascara, (255, 255, 255, 255), centro, radio)
        redonda.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _cache_imagenes[clave] = redonda
        return redonda
    except Exception as e:
        print(f"Error cargando imagen {ruta}: {e}")
        return None

_TABLA_LETRAS = """
Aa | A_abeja.png=abeja, A_avion.png=avión, A_arbol.png=árbol
Bb | B_ballena.png=ballena, B_bicicleta.png=bicicleta, B_botas.png=botas
Cc | C_conejo.png=conejo, C_casa.png=casa, C_carro.png=carro
Dd | D_delfin.png=delfín, D_dado.png=dado, D_dona.png=dona
Ee | E_escalera.png=escalera, E_elefante.png=elefante, E_estrella.png=estrella
Ff | F_foca.png=foca, F_foco.png=foco, F_fresa.png=fresa
Gg | G_gato.png=gato, G_globo.png=globo, G_guitarra.png=guitarra
Hh | H_hilo.png=hilo, H_huevo.png=huevo, H_hoja.png=hoja
Ii | I_iguana.png=iguana, I_isla.png=isla, I_iman.png=imán
Jj | J_jirafa.png=jirafa, J_jaula.png=jaula, J_jarron.png=jarrón
Kk | K_kiosco.png=kiosco, K_koala.png=koala, K_kiwi.png=kiwi
Ll | L_leon.png=león, L_lapiz.png=lápiz, L_lampara.png=lámpara
Mm | M_mesa.png=mesa, M_mariposa.png=mariposa, M_manzana.png=manzana
Nn | N_nube.png=nube, N_nido.png=nido, N_naranja.png=naranja
Ññ | Ñ_ñu.png=ñu, Ñ_ñame.png=ñame, Ñ_ñandu.png=ñandú
Oo | O_oveja.png=oveja, O_ojo.png=ojo, O_olla.png=olla
Pp | P_perro.png=perro, P_pera.png=pera, P_peine.png=peine
Qq | Q_querubin.png=querubín, Q_queso.png=queso, Q_quirofano.png=quirófano
Rr | R_rosa.png=rosa, R_raton.png=ratón, R_reloj.png=reloj
Ss | S_sol.png=sol, S_serpiente.png=serpiente, S_silla.png=silla
Tt | T_taco.png=taco, T_tigre.png=tigre, T_tambor.png=tambor
Uu | U_uña.png=uña, U_universo.png=universo, U_uva.png=uva
Vv | V_vaca.png=vaca, V_vela.png=vela, V_ventana.png=ventana
Ww | W_wifi.png=wifi, W_waffle.png=waffle
Xx | X_xilofono.png=xilófono
Yy | Y_yoyo.png=yoyo, Y_yegua.png=yegua, Y_yema.png=yema
Zz | Z_zapato.png=zapato, Z_zorro.png=zorro, Z_zanahoria.png=zanahoria
"""

datos = [
    {"letra": letra.strip(),
     "correctas": [{"imagen": i, "palabra": p} for i, p in (par.strip().split("=") for par in resto.split(","))]}
    for letra, resto in (linea.split("|") for linea in _TABLA_LETRAS.strip().splitlines())
]

# Imágenes que se usan como distractores: las que NO empiezan con "X_" ni son de la interfaz
_NO_DISTRACTORES = {"Fondo.png", "palomita.png", "tachita.png", "Logo.png", "corazon.png",
                    "avatar_feliz.png", "avatar_triste.png", "avatar_animo.png"}
_prefijos = tuple(f"{c}_" for c in string.ascii_uppercase)
IMAGENES_DISTRACCION = [f for f in os.listdir(ruta_img)
                        if f.endswith(".png") and not f.startswith(_prefijos) and f not in _NO_DISTRACTORES]

# Iconos simples dibujados con formas básicas
def dibujar_candado(superficie, x, y, tamaño=28, color=(255, 255, 255), abierto=False):
    """Candado cerrado (o abierto), centrado en (x, y)."""
    cuerpo = pygame.Rect(0, 0, tamaño, int(tamaño * 0.75))
    cuerpo.center = (x, y + int(tamaño * 0.28))
    pygame.draw.rect(superficie, color, cuerpo, border_radius=5)

    radio_arco, grosor = int(tamaño * 0.32), max(3, tamaño // 7)
    rect_arco = pygame.Rect(0, 0, radio_arco * 2, int(radio_arco * 2.2))
    if abierto:
        rect_arco.center = (x + int(tamaño * 0.22), cuerpo.top - int(radio_arco * 0.15))
        pygame.draw.arc(superficie, color, rect_arco, 0.9, 4.0, width=grosor)
    else:
        rect_arco.center = (x, cuerpo.top + 2)
        pygame.draw.arc(superficie, color, rect_arco, 0, math.pi, width=grosor)
    pygame.draw.circle(superficie, (90, 90, 90), cuerpo.center, max(2, tamaño // 9))


def dibujar_estrella(superficie, x, y, radio=18, color=(255, 255, 255)):
    """Estrella de 5 puntas, centrada en (x, y)."""
    puntos = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * 0.45
        ang = math.pi / 2 + i * math.pi / 5
        puntos.append((x + r * math.cos(ang), y - r * math.sin(ang)))
    pygame.draw.polygon(superficie, color, puntos)


def dibujar_altavoz(superficie, x, y, tamaño=28, color=(255, 255, 255), activo=True):
    """Altavoz con ondas (activo) o con una X (silenciado)."""
    rect = pygame.Rect(0, 0, tamaño * 0.32, tamaño * 0.5)
    rect.center = (x - tamaño * 0.32, y)
    pygame.draw.rect(superficie, color, rect, border_radius=2)
    pygame.draw.polygon(superficie, color, [
        (rect.right - 2, rect.top),
        (rect.right + tamaño * 0.3, rect.top - tamaño * 0.22),
        (rect.right + tamaño * 0.3, rect.bottom + tamaño * 0.22),
        (rect.right - 2, rect.bottom),
    ])
    if activo:
        for i in (1, 2):
            radio = tamaño * 0.22 * i + tamaño * 0.18
            rect_onda = pygame.Rect(0, 0, radio * 2, radio * 2)
            rect_onda.center = (int(rect.right + tamaño * 0.28), y)
            pygame.draw.arc(superficie, color, rect_onda, -0.6, 0.6, width=3)
    else:
        cx, s = x + tamaño * 0.45, tamaño * 0.2
        pygame.draw.line(superficie, color, (cx - s, y - s), (cx + s, y + s), 4)
        pygame.draw.line(superficie, color, (cx - s, y + s), (cx + s, y - s), 4)


def dibujar_burbuja(texto, x, y):
    """Burbuja de diálogo con la punta hacia abajo."""
    render = cargar_fuente(40).render(texto, True, (0, 0, 0))
    padding = 20
    burbuja = pygame.Rect(x, y, render.get_width() + padding * 2, render.get_height() + padding * 2)
    punta = [(x + 30, burbuja.bottom), (x + 50, burbuja.bottom + 20), (x + 70, burbuja.bottom)]
    for relleno, grosor in ((True, 0), (False, 3)):
        color = (255, 255, 255) if relleno else (0, 0, 0)
        pygame.draw.rect(pantalla, color, burbuja, grosor, border_radius=15)
        pygame.draw.polygon(pantalla, color, punta, grosor)
    pantalla.blit(render, (x + padding, y + padding))

# Pantallas de menú
def pantalla_inicio():
    global modo_libre, audio_activado
    fuente = cargar_fuente(60)
    boton_jugar = pygame.Rect(ANCHO // 2 - 150, ALTO // 2 + 120, 300, 80)
    boton_salir = pygame.Rect(ANCHO // 2 - 150, ALTO // 2 + 230, 300, 80)
    boton_modo_libre = pygame.Rect(ANCHO - 420, 40, 380, 70)    # interruptores arriba a la derecha
    boton_audio = pygame.Rect(ANCHO - 420, 130, 380, 70)

    ruta_logo = os.path.join(ruta_img, "Logo.png")
    logo = pygame.transform.scale(pygame.image.load(ruta_logo).convert_alpha(), (500, 350)) if os.path.exists(ruta_logo) else None
    subtitulo = fuente.render("Aprende el abecedario", True, (0, 0, 0))
    y_subtitulo = 10 + logo.get_height() + 5 if logo else 380

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))
        if logo:
            blit_en(logo, midtop=(ANCHO // 2, 50))
        blit_en(subtitulo, midtop=(ANCHO // 2, y_subtitulo))

        dibujar_interruptor(boton_modo_libre, f"Modo libre: {'SÍ' if modo_libre else 'NO'}",
                            PALETA["verde_activo" if modo_libre else "gris_bloqueado"],
                            dibujar_candado, tamaño=26, abierto=modo_libre)
        dibujar_interruptor(boton_audio, f"Sonido: {'SÍ' if audio_activado else 'NO'}",
                            PALETA["azul_principal" if audio_activado else "gris_bloqueado"],
                            dibujar_altavoz, tamaño=28, activo=audio_activado)
        dibujar_boton(boton_jugar, "Jugar", PALETA["azul_principal"], fuente)
        dibujar_boton(boton_salir, "Salir", PALETA["rosa_suave"], fuente)
        pygame.display.flip()

        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN:
                if boton_jugar.collidepoint(e.pos):
                    return
                if boton_salir.collidepoint(e.pos):
                    salir()
                if boton_modo_libre.collidepoint(e.pos):
                    modo_libre = not modo_libre
                if boton_audio.collidepoint(e.pos):
                    audio_activado = not audio_activado
                    aplicar_estado_audio()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                salir()


def wrap_text(texto, fuente, max_ancho):
    """Divide el texto en líneas que caben en el ancho dado."""
    lineas, actual = [], ""
    for palabra in texto.split(" "):
        prueba = (actual + " " + palabra).strip()
        if fuente.size(prueba)[0] <= max_ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def pantalla_instrucciones():
    fuente_texto = cargar_fuente(40, bold=False)
    panel_ancho, panel_alto = int(ANCHO * 0.78), int(ALTO * 0.55)
    panel_rect = pygame.Rect((ANCHO - panel_ancho) // 2, (ALTO - panel_alto) // 2 + 40, panel_ancho, panel_alto)
    boton = pygame.Rect(ANCHO // 2 - 210, panel_rect.bottom + 20, 420, 100)
    instrucciones = [
        "1. Mira la letra que aparece arriba.",
        "2. Haz clic en la imagen que EMPIECE con esa letra.",
        "3. Si aciertas, escucharás la palabra y sigues avanzando.",
        "4. Si fallas, perderás un corazón (en Modo libre no pasa nada).",
        "¡Diviértete aprendiendo!",
    ]

    # Título y panel no cambian entre fotogramas: se dibujan una sola vez
    titulo = cargar_fuente(100).render("Instrucciones", True, (0, 0, 0))
    panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (255, 255, 255, 240), panel.get_rect(), border_radius=30)
    pygame.draw.rect(panel, (0, 0, 0), panel.get_rect(), 4, border_radius=30)
    y = 24
    for linea in instrucciones:
        for sublinea in wrap_text(linea, fuente_texto, panel_rect.width - 48):
            render = fuente_texto.render(sublinea, True, (0, 0, 0))
            panel.blit(render, (24, y))
            y += render.get_height() + 8

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))
        blit_en(titulo, midtop=(ANCHO // 2, panel_rect.top - titulo.get_height() - 20))
        pantalla.blit(panel, panel_rect)
        dibujar_boton(boton, "¡Iniciar!", color_hover("azul_principal", boton), cargar_fuente(60))
        pygame.display.flip()

        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN and boton.collidepoint(e.pos):
                return
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                return


def pantalla_fin_juego(titulo="¡Se acabaron tus vidas!", color_titulo=(200, 0, 0)):
    """Se muestra al perder todas las vidas. Devuelve "reintentar" o "menu"."""
    fuente_titulo, fuente_boton = cargar_fuente(90), cargar_fuente(55)
    avatar = AVATARES["triste"]
    x = ANCHO // 2 - 210
    botones = [  # (rect, texto, color de la paleta, acción)
        (pygame.Rect(x, ALTO // 2 + 40, 420, 100), "Reintentar", "verde_activo", "reintentar"),
        (pygame.Rect(x, ALTO // 2 + 170, 420, 100), "Menú principal", "azul_principal", "menu"),
    ]

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))
        y_titulo = 40
        if avatar:
            pantalla.blit(avatar, (ANCHO // 2 - avatar.get_width() // 2, 40))
            y_titulo += avatar.get_height() + 20
        blit_en(fuente_titulo.render(titulo, True, color_titulo), midtop=(ANCHO // 2, y_titulo))
        for rect, texto, color, _ in botones:
            dibujar_boton(rect, texto, color_hover(color, rect), fuente_boton)
        pygame.display.flip()

        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN:
                for rect, _, _, accion in botones:
                    if rect.collidepoint(e.pos):
                        return accion
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "menu"
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "reintentar"

# Minijuegos
def minijuego_arrastrar_letra_opciones(letras_aprendidas, imagen_correcta, palabra):
    """Repaso: arrastrar la imagen hasta la letra con la que empieza."""
    inicial = imagen_correcta[0].upper()   # "A_abeja.png" -> "A"
    # La opción correcta es la letra del nivel que corresponde a la imagen (ej. "Aa")
    correcta = next((l for l in letras_aprendidas if l[0].upper() == inicial), inicial)
    opciones = random.sample(letras_aprendidas, min(3, len(letras_aprendidas)))
    if correcta not in opciones:
        opciones[random.randrange(len(opciones))] = correcta

    imagen = cargar_imagen(imagen_correcta, tamaño=(200, 200))
    if not imagen:
        return
    rect_imagen = imagen.get_rect(topleft=(100, ALTO // 2))
    posiciones = [(ANCHO // 2 + 100, ALTO // 2 - 150), (ANCHO // 2 + 300, ALTO // 2), (ANCHO // 2 + 500, ALTO // 2 + 150)]
    random.shuffle(posiciones)
    fuente = cargar_fuente(180)
    letras = []  # (texto de la letra, superficie, rect)
    for letra, pos in zip(opciones, posiciones):
        texto = fuente.render(letra, True, (0, 0, 0))
        letras.append((letra, texto, texto.get_rect(center=pos)))

    def dibujar():
        pantalla.blit(fondo, (0, 0))
        for _, texto, rect in letras:
            caja = rect.inflate(30, 30)
            pygame.draw.rect(pantalla, (255, 255, 255), caja)
            pygame.draw.rect(pantalla, (0, 0, 0), caja, 4)
            pantalla.blit(texto, rect)
        pantalla.blit(imagen, rect_imagen)
        pygame.display.flip()

    dibujar()
    pausa_activa(500)
    if not reproducir_audio(os.path.join(ruta_audios, f"minijuego_{inicial}_{palabra}.mp3")):
        hablar(f"¿A qué letra corresponde {palabra}? Arrástrala")

    arrastrando = terminado = False
    while not terminado:
        reloj.tick(60)
        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN and rect_imagen.collidepoint(e.pos):
                arrastrando = True
            elif e.type == pygame.MOUSEBUTTONUP:
                arrastrando = False
                for letra, _, rect in letras:
                    if rect_imagen.colliderect(rect):
                        if letra == correcta:
                            if not reproducir_audio(os.path.join(ruta_audios, "muy_bien.mp3")):
                                hablar("¡Muy bien!")
                            terminado = True
                        else:
                            hablar("Intenta otra vez")
            elif e.type == pygame.MOUSEMOTION and arrastrando:
                rect_imagen.center = e.pos
        dibujar()


def minijuego_rompecabezas_letra(info_letra):
    """
    Rompecabezas: la letra se parte en 2 piezas (arriba y abajo) que el jugador arrastra
    hasta armarla. Sin vidas ni tiempo límite: es forma y motricidad, no hay cómo "perder".
    """
    letra = info_letra["letra"]
    objeto = random.choice(info_letra["correctas"])
    ancho, alto = 260, 150   # tamaño de cada pieza; la letra completa mide ancho x (2 * alto)

    # La letra se dibuja en una superficie aparte para poder partirla en dos
    completa = pygame.Surface((ancho, alto * 2), pygame.SRCALPHA)
    render = cargar_fuente(180).render(letra, True, random.choice(COLORES_LETRAS))
    completa.blit(render, render.get_rect(center=(ancho // 2, alto)))

    x0, y0 = ANCHO // 2 - ancho // 2, ALTO // 2 - alto                    # posición final, al centro
    origenes = [(150, ALTO - 300), (ANCHO - 150 - ancho, 150)]            # piezas revueltas a los lados
    piezas = [{"surf": completa.subsurface(pygame.Rect(0, k * alto, ancho, alto)).copy(),
               "rect": pygame.Rect(origenes[k], (ancho, alto)),
               "objetivo": pygame.Rect(x0, y0 + k * alto, ancho, alto),
               "colocada": False} for k in (0, 1)]
    imagen_apoyo = cargar_imagen(objeto["imagen"], tamaño=(160, 160))
    instruccion = cargar_fuente(40).render("Arrastra las piezas para armar la letra", True, (0, 0, 0))

    def dibujar():
        pantalla.blit(fondo, (0, 0))
        blit_en(instruccion, midtop=(ANCHO // 2, 60))
        if imagen_apoyo:
            pantalla.blit(imagen_apoyo, (40, ALTO // 2 - 80))
        for pieza in piezas:
            pygame.draw.rect(pantalla, (255, 255, 255), pieza["objetivo"], 4, border_radius=10)
        for pieza in piezas:
            pantalla.blit(pieza["surf"], pieza["rect"])
        pygame.display.flip()

    dibujar()
    pausa_activa(400)
    hablar(f"Arma la letra {letra} uniendo las dos piezas")

    en_mano = None
    while not all(p["colocada"] for p in piezas):
        reloj.tick(60)
        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN:
                en_mano = next((p for p in piezas if not p["colocada"] and p["rect"].collidepoint(e.pos)), None)
            elif e.type == pygame.MOUSEBUTTONUP and en_mano:
                if en_mano["rect"].colliderect(en_mano["objetivo"].inflate(60, 60)):   # tolerancia de 60 px
                    en_mano["rect"].topleft = en_mano["objetivo"].topleft
                    en_mano["colocada"] = True
                    canal_efectos.play(sonido_correcto)
                en_mano = None
            elif e.type == pygame.MOUSEMOTION and en_mano:
                en_mano["rect"].center = e.pos
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
        dibujar()

    if not reproducir_audio(os.path.join(ruta_audios, "muy_bien.mp3")):
        hablar(f"¡Excelente! Armaste la letra {letra}")
    pausa_activa(1200)



# Pantalla de juego
RONDA_VACIA = {"opciones": [], "imagen": "", "color": (0, 0, 0), "posiciones": []}
FRASES_ANIMO = [("¡Vamos, tú puedes!", "animo_tu_puedes.mp3"),
                ("No te rindas", "animo_no_te_rindas.mp3"),
                ("Inténtalo otra vez", "animo_intentalo_otra_vez.mp3")]


def mostrar_pantalla(letra, ronda=None, marca=None, estado_avatar="normal"):
    """
    Dibuja la pantalla de una ronda y devuelve sus botones [(rect, es_correcta)].
    - ronda: dict creado por juego_letra (None = pantalla sin opciones, como la del final)
    - marca: (imagen, rect) para poner la palomita o la tachita sobre una opción
    - estado_avatar: "feliz", "triste", "animo" o "normal" (sin avatar)
    """
    ronda = ronda or RONDA_VACIA
    pantalla.blit(fondo, (0, 0))

    fuente = cargar_fuente(200)
    pantalla.blit(fuente.render(letra, True, (0, 0, 0)), (55, 55))             # sombra
    pantalla.blit(fuente.render(letra, True, ronda["color"]), (50, 50))

    # Progreso dentro del nivel: verde = superada, azul = actual, gris = falta
    if letra and datos_nivel:
        total = len(datos_nivel)
        x0 = ANCHO // 2 - (total - 1) * 38 // 2
        for i in range(total):
            color = PALETA["verde_activo" if i < indice else "azul_principal" if i == indice else "gris_bloqueado"]
            centro = (x0 + i * 38, 36)
            pygame.draw.circle(pantalla, color, centro, 14)
            if i == indice:
                pygame.draw.circle(pantalla, PALETA["texto_oscuro"], centro, 14, 3)

    if palabra_mostrada:
        fuente_palabra = cargar_fuente(90)
        texto = fuente_palabra.render(palabra_mostrada, True, random.choice(COLORES_LETRAS))
        x = ANCHO // 2 - texto.get_width() // 2
        pantalla.blit(fuente_palabra.render(palabra_mostrada, True, (0, 0, 0)), (x + 3, 253))
        pantalla.blit(texto, (x, 250))

    botones = []
    for nombre, pos in zip(ronda["opciones"], ronda["posiciones"]):
        imagen = cargar_imagen(nombre)
        if imagen:
            pantalla.blit(imagen, pos)
            botones.append((imagen.get_rect(topleft=pos), nombre == ronda["imagen"]))
    if marca:
        blit_en(marca[0], center=marca[1].center)

    avatar = AVATARES.get(estado_avatar)
    if avatar:
        x_avatar = ANCHO // 2 - avatar.get_width() // 2
        pantalla.blit(avatar, (x_avatar, 20))
        if estado_avatar == "animo":   # burbuja con frase y su audio (sin esperar a que termine)
            frase, audio = random.choice(FRASES_ANIMO)
            reproducir_audio(os.path.join(ruta_audios, audio), esperar=False)
            dibujar_burbuja(frase, x_avatar + avatar.get_width() + 10, 100)

    if modo_libre:   # infinito en vez de corazones
        infinito = cargar_fuente(50).render("∞", True, PALETA["azul_aviso"])
        pantalla.blit(infinito, (ANCHO - infinito.get_width() - 30, 15))
    else:
        for i in range(vidas):
            centro = (ANCHO - (i + 1) * 70 + 30, 50)
            pygame.draw.circle(pantalla, (255, 255, 255), centro, 30)
            blit_en(corazon_img, center=centro)

    pygame.display.flip()
    return botones


def juego_letra(info):
    """Prepara una ronda (imagen correcta + 2 distractores) y devuelve su dict 'ronda'."""
    global palabra_mostrada
    palabra_mostrada = ""
    correcta = random.choice(info["correctas"])
    inicial = info["letra"][0].lower()   # los distractores no deben empezar con la misma letra
    disponibles = [i for i in IMAGENES_DISTRACCION if i != correcta["imagen"] and not i.lower().startswith(inicial)]
    opciones = random.sample(disponibles, min(2, len(disponibles))) + [correcta["imagen"]]
    random.shuffle(opciones)

    y = ALTO // 2 + 30
    posiciones = [(ANCHO // 4 - 150, y), (ANCHO // 2 - 150, y), (3 * ANCHO // 4 - 150, y)]
    random.shuffle(posiciones)

    ronda = {"opciones": opciones, "imagen": correcta["imagen"], "palabra": correcta["palabra"],
             "color": random.choice(COLORES_LETRAS), "posiciones": posiciones}
    ronda["botones"] = mostrar_pantalla(info["letra"], ronda)
    hablar(f"¿Cuál imagen empieza con la letra {info['letra']}?")
    return ronda

# Niveles
# Niveles 1-6: las 27 letras por grupos (cada nivel se desbloquea al completar el anterior).
# Niveles 7-8: rompecabezas con 6 letras cada uno (siempre disponibles).
_GRUPOS_LETRAS = [("A - E", 0, 5), ("F - J", 5, 10), ("K - Ñ", 10, 15), ("O - S", 15, 20), ("T - W", 20, 24), ("X - Z", 24, 27)]
_LETRAS_ROMPECABEZAS = [(0, 5, 10, 15, 20, 24), (2, 7, 12, 17, 22, 25)]   # posiciones dentro de 'datos'

NIVELES = [{"nombre": f"Nivel {n}: {rango}", "datos": datos[a:b]} for n, (rango, a, b) in enumerate(_GRUPOS_LETRAS, 1)]
NIVELES += [{"nombre": f"Nivel {7 + k}: Rompecabezas {k + 1}", "tipo": "rompecabezas", "datos": [datos[i] for i in letras]}
            for k, letras in enumerate(_LETRAS_ROMPECABEZAS)]

niveles_completados = set()  # niveles terminados en esta sesión


def nivel_desbloqueado(i):
    """Rompecabezas y Modo libre: siempre abiertos. Letras: el primero, y cada uno al completar el anterior."""
    return modo_libre or NIVELES[i].get("tipo") == "rompecabezas" or i == 0 or (i - 1) in niveles_completados


def pantalla_seleccion_niveles():
    """Cuadrícula de niveles. Devuelve el índice del nivel elegido."""
    fuente_nivel, fuente_chica, fuente_estado = cargar_fuente(40), cargar_fuente(28), cargar_fuente(26)
    columnas, ancho, alto, espacio = 3, 380, 140, 50
    x0 = ANCHO // 2 - (columnas * ancho + (columnas - 1) * espacio) // 2
    rects = [pygame.Rect(x0 + (i % columnas) * (ancho + espacio), ALTO // 2 - 160 + (i // columnas) * (alto + espacio), ancho, alto)
             for i in range(len(NIVELES))]
    titulo = cargar_fuente(90).render("Elige un nivel", True, (0, 0, 0))
    aviso = cargar_fuente(34).render("Modo libre activado: sin vidas, todos los niveles disponibles", True, PALETA["azul_aviso"])

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))
        blit_en(titulo, midtop=(ANCHO // 2, 60))
        if modo_libre:
            blit_en(aviso, midtop=(ANCHO // 2, 70 + titulo.get_height()))

        for i, rect in enumerate(rects):
            abierto, completado = nivel_desbloqueado(i), i in niveles_completados
            dibujar_boton(rect, "", color_hover("verde_activo", rect) if abierto else PALETA["gris_bloqueado"], None, radio=20,
                          borde=6 if completado else 3, color_borde=PALETA["dorado_completado"] if completado else (0, 0, 0))
            tinta = PALETA["texto_claro" if abierto else "texto_bloqueado"]
            nombre = fuente_nivel.render(NIVELES[i]["nombre"], True, tinta)
            if nombre.get_width() > rect.width - 20:   # nombres largos: letra más chica
                nombre = fuente_chica.render(NIVELES[i]["nombre"], True, tinta)
            blit_en(nombre, center=(rect.centerx, rect.centery - 15))

            estado = "" if abierto and not completado else "Bloqueado" if not abierto else "¡Completado!"
            if estado:
                blit_en(fuente_estado.render(estado, True, tinta), midtop=(rect.centerx, rect.centery + 25))
            # Un ícono refuerza el estado además del color y el texto
            if not abierto:
                dibujar_candado(pantalla, rect.right - 28, rect.top + 26, tamaño=26)
            elif completado:
                dibujar_estrella(pantalla, rect.right - 28, rect.top + 26, radio=16, color=PALETA["dorado_completado"])
        pygame.display.flip()

        for e in eventos():
            if e.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(rects):
                    if nivel_desbloqueado(i) and rect.collidepoint(e.pos):
                        return i
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                salir()


def terminar_nivel(nivel_idx):
    """Marca el nivel como completado y lo celebra (con mensaje especial al completar todos)."""
    niveles_completados.add(nivel_idx)
    if len(niveles_completados) == len(NIVELES):
        hablar("¡Felicidades! Has terminado el abecedario.")
        mostrar_pantalla("", estado_avatar="feliz")
        pausa_activa(2500)
    else:
        hablar("¡Nivel completado!")


def jugar_nivel(nivel_idx):
    """Juega un nivel de letras. Devuelve True si el jugador eligió 'Reintentar' al quedarse sin vidas."""
    global vidas, indice, datos_nivel, palabra_mostrada
    datos_nivel = NIVELES[nivel_idx]["datos"]
    vidas, indice = 5, 0
    ronda = juego_letra(datos_nivel[0])

    while True:
        reloj.tick(60)
        for e in eventos():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return False
            if e.type != pygame.MOUSEBUTTONDOWN:
                continue
            clic = next(((r, ok) for r, ok in ronda["botones"] if r.collidepoint(e.pos)), None)
            if not clic:
                continue
            rect, es_correcta = clic
            letra = datos_nivel[indice]["letra"]

            if es_correcta:
                canal_efectos.play(sonido_correcto)
                hablar(f"¡Correcto! {letra} de {ronda['palabra']}")
                palabra_mostrada = ronda["palabra"]
                mostrar_pantalla(letra, ronda, marca=(palomita_img, rect), estado_avatar="feliz")
                pausa_activa(3000)
                indice += 1
                if indice < len(datos_nivel):
                    ronda = juego_letra(datos_nivel[indice])
                    continue
                # Última letra: minijuego de repaso con una imagen del nivel y se termina
                objeto = random.choice(random.choice(datos_nivel)["correctas"])
                minijuego_arrastrar_letra_opciones([d["letra"] for d in datos_nivel], objeto["imagen"], objeto["palabra"])
                terminar_nivel(nivel_idx)
                return False

            canal_efectos.play(sonido_error)
            hablar("Intenta otra vez")
            if not modo_libre:
                vidas -= 1
                if vidas <= 0:
                    hablar("¡Se acabaron tus vidas!")
                    mostrar_pantalla(letra, ronda, estado_avatar="triste")
                    pausa_activa(1500)
                    return pantalla_fin_juego() == "reintentar"
            mostrar_pantalla(letra, ronda, marca=(tachita_img, rect), estado_avatar="triste")
            pausa_activa(2000)
            mostrar_pantalla(letra, ronda, estado_avatar="animo")
            pausa_activa(1500)


# ============================
# Bucle principal
# ============================
def main():
    reintentar = None   # si el jugador eligió "Reintentar", índice del nivel a repetir sin pasar por los menús
    while True:
        if reintentar is None:
            pantalla_inicio()
            pantalla_instrucciones()
            nivel_idx = pantalla_seleccion_niveles()
        else:
            nivel_idx, reintentar = reintentar, None

        if NIVELES[nivel_idx].get("tipo") == "rompecabezas":
            for info_letra in NIVELES[nivel_idx]["datos"]:
                minijuego_rompecabezas_letra(info_letra)
            terminar_nivel(nivel_idx)
        elif jugar_nivel(nivel_idx):
            reintentar = nivel_idx


if __name__ == "__main__":
    main()
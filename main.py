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

# Variable global para mostrar la palabra correcta solo cuando aciertas
palabra_mostrada = ""

# Modo libre: cuando está activo, no se pierden vidas ni se bloquean
# niveles. Pensado para practicar sin presión de fallar.
modo_libre = False

# Audio activado: interruptor maestro de silencio (música, efectos y voz)
audio_activado = True

# Se incluye el archivo .ttf dentro del proyecto para que el juego se
# vea igual en Windows, Mac o Linux, en vez de depender de que el
# sistema operativo tenga "Comic Sans MS" instalada.
RUTA_FUENTE = os.path.join(os.path.dirname(__file__), "assets", "fuentes", "Baloo2.ttf")


def cargar_fuente(tamaño, bold=True):
    """
    Carga la fuente propia del juego (Baloo2) en el tamaño pedido.
    Si por alguna razón el archivo no está disponible, usa Comic Sans
    MS del sistema como respaldo, para que el juego no deje de abrir.
    """
    if os.path.exists(RUTA_FUENTE):
        fuente = pygame.font.Font(RUTA_FUENTE, tamaño)
        fuente.set_bold(bold)
        return fuente
    return pygame.font.SysFont("Comic Sans MS", tamaño, bold=bold)


# Fuentes
fuente_texto = cargar_fuente(60, bold=True)

# Fuentes reutilizadas en pantallas que se redibujan muy seguido
# (crearlas una sola vez aquí evita recrear el objeto de fuente en cada fotograma)
FUENTES = {
    "letra_grande": cargar_fuente(200, bold=True),
    "palabra": cargar_fuente(90, bold=True),
    "burbuja": cargar_fuente(40, bold=True),
    "infinito": cargar_fuente(50, bold=True),
    "minijuego_letra": cargar_fuente(180, bold=True),
}


def pausa_activa(ms):
    """
    Espera 'ms' milisegundos SIN congelar la ventana: sigue atendiendo
    el botón de cerrar (para que el sistema operativo no marque la
    ventana como 'no responde') y descarta los clics que hayan llegado
    durante la espera, para que no se acumulen y se apliquen de golpe
    al terminar.
    """
    reloj_local = pygame.time.Clock()
    restante = ms
    while restante > 0:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        restante -= reloj_local.tick(60)


def reproducir_audio_bloqueante(ruta_audio):
    """
    Carga y reproduce un mp3, esperando a que termine antes de continuar.
    Devuelve True si encontró y reprodujo el archivo, False si no existía.
    Centraliza un patrón que antes estaba repetido en varios lugares.
    """
    if not os.path.exists(ruta_audio):
        return False
    pygame.mixer.music.load(ruta_audio)
    pygame.mixer.music.play()
    reloj_local = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        reloj_local.tick(30)
    return True

# Ruta imágenes y fondo
ruta_img = os.path.join(os.path.dirname(__file__), "assets", "imagenes")
ruta_fondo = os.path.join(ruta_img, "Fondo.png")
fondo = pygame.image.load(ruta_fondo).convert()
fondo = pygame.transform.scale(fondo, (ANCHO, ALTO))

# Palomita y tachita
ruta_palomita = os.path.join(ruta_img, "palomita.png")
palomita_img = pygame.image.load(ruta_palomita).convert_alpha()

ruta_tachita = os.path.join(ruta_img, "tachita.png")
tachita_img = pygame.image.load(ruta_tachita).convert_alpha()

# Corazón
ruta_corazon = os.path.join(ruta_img, "corazon.png")
corazon_img = pygame.image.load(ruta_corazon).convert_alpha()
corazon_img = pygame.transform.scale(corazon_img, (50, 50))  # Tamaño del corazón

# Tamaño base para todos los avatares
TAM_AVATAR = (250, 250)

# Primero define la función de escalar
def escalar_imagen_con_proporcion(imagen, max_ancho, max_alto):
    ancho_original, alto_original = imagen.get_size()
    proporcion = min(max_ancho / ancho_original, max_alto / alto_original)
    nuevo_ancho = int(ancho_original * proporcion)
    nuevo_alto = int(alto_original * proporcion)
    return pygame.transform.smoothscale(imagen, (nuevo_ancho, nuevo_alto))

# Función para cargar avatar con centrado automático
def cargar_avatar(ruta):
    if os.path.exists(ruta):
        img = pygame.image.load(ruta).convert_alpha()
        img_escalada = escalar_imagen_con_proporcion(img, TAM_AVATAR[0], TAM_AVATAR[1])

        # Crear lienzo fijo del tamaño base
        lienzo = pygame.Surface(TAM_AVATAR, pygame.SRCALPHA)

        # Centrar imagen escalada dentro del lienzo
        rect = img_escalada.get_rect(center=(TAM_AVATAR[0]//2, TAM_AVATAR[1]//2))
        lienzo.blit(img_escalada, rect)

        return lienzo
    return None

# Avatar / Mascota
ruta_avatar_feliz = os.path.join(ruta_img, "avatar_feliz.png")
ruta_avatar_triste = os.path.join(ruta_img, "avatar_triste.png")
ruta_avatar_animo = os.path.join(ruta_img, "avatar_animo.png")

avatar_feliz = cargar_avatar(ruta_avatar_feliz)
avatar_triste = cargar_avatar(ruta_avatar_triste)
avatar_animo = cargar_avatar(ruta_avatar_animo)


def pantalla_inicio():
    global modo_libre, audio_activado

    fuente_titulo = cargar_fuente(120, bold=True)
    fuente_subtitulo = cargar_fuente(60, bold=True)
    fuente_boton = cargar_fuente(60, bold=True)
    fuente_modo = cargar_fuente(32, bold=True)

    # Colores de botones
    color_jugar = PALETA["azul_principal"]
    color_salir = PALETA["rosa_suave"]

    # Rectángulos botones
    boton_jugar = pygame.Rect(ANCHO // 2 - 150, ALTO // 2 + 120, 300, 80)
    boton_salir = pygame.Rect(ANCHO // 2 - 150, ALTO // 2 + 230, 300, 80)

    # Interruptores, arriba a la derecha (uno debajo del otro)
    boton_modo_libre = pygame.Rect(ANCHO - 420, 40, 380, 70)
    boton_audio = pygame.Rect(ANCHO - 420, 130, 380, 70)

    # Logo
    ruta_logo = os.path.join(ruta_img, "Logo.png")
    if os.path.exists(ruta_logo):
        logo_img = pygame.image.load(ruta_logo).convert_alpha()
        logo_img = pygame.transform.scale(logo_img, (500, 350))
    else:
        logo_img = None

    while True:
        reloj.tick(60)
        # ⬇️ Dibuja tu fondo.png como fondo de pantalla
        pantalla.blit(fondo, (0, 0))

        # Logo ARRIBA
        if logo_img:
            pantalla.blit(logo_img, (ANCHO // 2 - logo_img.get_width() // 2, 50))

        # Subtítulo DEBAJO del logo
        subtitulo = fuente_subtitulo.render("Aprende el abecedario", True, (0, 0, 0))
        pantalla.blit(subtitulo, (
            ANCHO // 2 - subtitulo.get_width() // 2,
            10 + logo_img.get_height() + 5 if logo_img else 380
        ))

        # Interruptor de Modo libre
        color_modo = PALETA["verde_activo"] if modo_libre else PALETA["gris_bloqueado"]
        pygame.draw.rect(pantalla, color_modo, boton_modo_libre, border_radius=25)
        pygame.draw.rect(pantalla, (0, 0, 0), boton_modo_libre, 3, border_radius=25)
        texto_modo = "Modo libre: SÍ" if modo_libre else "Modo libre: NO"
        render_modo = fuente_modo.render(texto_modo, True, (255, 255, 255))
        icono_ancho, espacio_icono = 34, 14
        ancho_contenido = icono_ancho + espacio_icono + render_modo.get_width()
        x_contenido = boton_modo_libre.centerx - ancho_contenido // 2
        dibujar_candado(
            pantalla, x_contenido + icono_ancho // 2, boton_modo_libre.centery,
            tamaño=26, color=PALETA["texto_claro"], abierto=modo_libre
        )
        pantalla.blit(render_modo, (
            x_contenido + icono_ancho + espacio_icono,
            boton_modo_libre.centery - render_modo.get_height() // 2
        ))

        # Interruptor de Sonido (música, efectos y voz)
        color_audio = PALETA["azul_principal"] if audio_activado else PALETA["gris_bloqueado"]
        pygame.draw.rect(pantalla, color_audio, boton_audio, border_radius=25)
        pygame.draw.rect(pantalla, (0, 0, 0), boton_audio, 3, border_radius=25)
        texto_audio = "Sonido: SÍ" if audio_activado else "Sonido: NO"
        render_audio = fuente_modo.render(texto_audio, True, (255, 255, 255))
        icono_ancho_a, espacio_icono_a = 34, 14
        ancho_contenido_a = icono_ancho_a + espacio_icono_a + render_audio.get_width()
        x_contenido_a = boton_audio.centerx - ancho_contenido_a // 2
        dibujar_altavoz(
            pantalla, x_contenido_a + icono_ancho_a // 2, boton_audio.centery,
            tamaño=28, color=PALETA["texto_claro"], activo=audio_activado
        )
        pantalla.blit(render_audio, (
            x_contenido_a + icono_ancho_a + espacio_icono_a,
            boton_audio.centery - render_audio.get_height() // 2
        ))

        # Botón Jugar - Azul y redondeado
        pygame.draw.rect(pantalla, color_jugar, boton_jugar, border_radius=25)
        texto_jugar = fuente_boton.render("Jugar", True, PALETA["texto_claro"])
        pantalla.blit(texto_jugar, (
            boton_jugar.centerx - texto_jugar.get_width() // 2,
            boton_jugar.centery - texto_jugar.get_height() // 2
        ))

        # Botón Salir - Rojo y redondeado
        pygame.draw.rect(pantalla, color_salir, boton_salir, border_radius=25)
        texto_salir = fuente_boton.render("Salir", True, PALETA["texto_claro"])
        pantalla.blit(texto_salir, (
            boton_salir.centerx - texto_salir.get_width() // 2,
            boton_salir.centery - texto_salir.get_height() // 2
        ))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if boton_jugar.collidepoint(evento.pos):
                    return  # Empieza juego
                elif boton_salir.collidepoint(evento.pos):
                    pygame.quit()
                    sys.exit()
                elif boton_modo_libre.collidepoint(evento.pos):
                    modo_libre = not modo_libre
                elif boton_audio.collidepoint(evento.pos):
                    audio_activado = not audio_activado
                    aplicar_estado_audio()
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

datos = [
    {
        "letra": "Aa",
        "correctas": [
            {"imagen": "A_abeja.png", "palabra": "abeja"},
            {"imagen": "A_avion.png", "palabra": "avión"},
            {"imagen": "A_arbol.png", "palabra": "árbol"}
        ],
        "otras": []
    },
    {
        "letra": "Bb",
        "correctas": [
            {"imagen": "B_ballena.png", "palabra": "ballena"},
            {"imagen": "B_bicicleta.png", "palabra": "bicicleta"},
            {"imagen": "B_botas.png", "palabra": "botas"}
        ],
        "otras": []
    },
    {
        "letra": "Cc",
        "correctas": [
            {"imagen": "C_conejo.png", "palabra": "conejo"},
            {"imagen": "C_casa.png", "palabra": "casa"},
            {"imagen": "C_carro.png", "palabra": "carro"}
        ],
        "otras": []
    },
    {
        "letra": "Dd",
        "correctas": [
            {"imagen": "D_delfin.png", "palabra": "delfín"},
            {"imagen": "D_dado.png", "palabra": "dado"},
            {"imagen": "D_dona.png", "palabra": "dona"}
        ],
        "otras": []
    },
    {
        "letra": "Ee",
        "correctas": [
            {"imagen": "E_escalera.png", "palabra": "escalera"},
            {"imagen": "E_elefante.png", "palabra": "elefante"},
            {"imagen": "E_estrella.png", "palabra": "estrella"}
        ],
        "otras": []
    },
    {
        "letra": "Ff",
        "correctas": [
            {"imagen": "F_foca.png", "palabra": "foca"},
            {"imagen": "F_foco.png", "palabra": "foco"},
            {"imagen": "F_fresa.png", "palabra": "fresa"}
        ],
        "otras": []
    },
    {
        "letra": "Gg",
        "correctas": [
            {"imagen": "G_gato.png", "palabra": "gato"},
            {"imagen": "G_globo.png", "palabra": "globo"},
            {"imagen": "G_guitarra.png", "palabra": "guitarra"}
        ],
        "otras": []
    },
    {
        "letra": "Hh",
        "correctas": [
            {"imagen": "H_hilo.png", "palabra": "hilo"},
            {"imagen": "H_huevo.png", "palabra": "huevo"},
            {"imagen": "H_hoja.png", "palabra": "hoja"}
        ],
        "otras": []
    },
    {
        "letra": "Ii",
        "correctas": [
            {"imagen": "I_iguana.png", "palabra": "iguana"},
            {"imagen": "I_isla.png", "palabra": "isla"},
            {"imagen": "I_iman.png", "palabra": "imán"}
        ],
        "otras": []
    },
    {
        "letra": "Jj",
        "correctas": [
            {"imagen": "J_jirafa.png", "palabra": "jirafa"},
            {"imagen": "J_jaula.png", "palabra": "jaula"},
            {"imagen": "J_jarron.png", "palabra": "jarrón"}
        ],
        "otras": []
    },
    {
        "letra": "Kk",
        "correctas": [
            {"imagen": "K_kiosco.png", "palabra": "kiosco"},
            {"imagen": "K_koala.png", "palabra": "koala"},
            {"imagen": "K_kiwi.png", "palabra": "kiwi"}
        ],
        "otras": []
    },
    {
        "letra": "Ll",
        "correctas": [
            {"imagen": "L_leon.png", "palabra": "león"},
            {"imagen": "L_lapiz.png", "palabra": "lápiz"},
            {"imagen": "L_lampara.png", "palabra": "lámpara"}
        ],
        "otras": []
    },
    {
        "letra": "Mm",
        "correctas": [
            {"imagen": "M_mesa.png", "palabra": "mesa"},
            {"imagen": "M_mariposa.png", "palabra": "mariposa"},
            {"imagen": "M_manzana.png", "palabra": "manzana"}
        ],
        "otras": []
    },
    {
        "letra": "Nn",
        "correctas": [
            {"imagen": "N_nube.png", "palabra": "nube"},
            {"imagen": "N_nido.png", "palabra": "nido"},
            {"imagen": "N_naranja.png", "palabra": "naranja"}
        ],
        "otras": []
    },
    {
        "letra": "Ññ",
        "correctas": [
            {"imagen": "Ñ_ñu.png", "palabra": "ñu"},
            {"imagen": "Ñ_ñame.png", "palabra": "ñame"},
            {"imagen": "Ñ_ñandu.png", "palabra": "ñandú"}
        ],
        "otras": []
    },
    {
        "letra": "Oo",
        "correctas": [
            {"imagen": "O_oveja.png", "palabra": "oveja"},
            {"imagen": "O_ojo.png", "palabra": "ojo"},
            {"imagen": "O_olla.png", "palabra": "olla"}
        ],
        "otras": []
    },
    {
        "letra": "Pp",
        "correctas": [
            {"imagen": "P_perro.png", "palabra": "perro"},
            {"imagen": "P_pera.png", "palabra": "pera"},
            {"imagen": "P_peine.png", "palabra": "peine"}
        ],
        "otras": []
    },
    {
        "letra": "Qq",
        "correctas": [
            {"imagen": "Q_querubin.png", "palabra": "querubín"},
            {"imagen": "Q_queso.png", "palabra": "queso"},
            {"imagen": "Q_quirofano.png", "palabra": "quirófano"}
        ],
        "otras": []
    },
    {
        "letra": "Rr",
        "correctas": [
            {"imagen": "R_rosa.png", "palabra": "rosa"},
            {"imagen": "R_raton.png", "palabra": "ratón"},
            {"imagen": "R_reloj.png", "palabra": "reloj"}
        ],
        "otras": []
    },
    {
        "letra": "Ss",
        "correctas": [
            {"imagen": "S_sol.png", "palabra": "sol"},
            {"imagen": "S_serpiente.png", "palabra": "serpiente"},
            {"imagen": "S_silla.png", "palabra": "silla"}
        ],
        "otras": []
    },
    {
        "letra": "Tt",
        "correctas": [
            {"imagen": "T_taco.png", "palabra": "taco"},
            {"imagen": "T_tigre.png", "palabra": "tigre"},
            {"imagen": "T_tambor.png", "palabra": "tambor"}
        ],
        "otras": []
    },
    {
        "letra": "Uu",
        "correctas": [
            {"imagen": "U_uña.png", "palabra": "uña"},
            {"imagen": "U_universo.png", "palabra": "universo"},
            {"imagen": "U_uva.png", "palabra": "uva"}
        ],
        "otras": []
    },
    {
        "letra": "Vv",
        "correctas": [
            {"imagen": "V_vaca.png", "palabra": "vaca"},
            {"imagen": "V_vela.png", "palabra": "vela"},
            {"imagen": "V_ventana.png", "palabra": "ventana"}
        ],
        "otras": []
    },
    {
        "letra": "Ww",
        "correctas": [
            {"imagen": "W_wifi.png", "palabra": "wifi"},
            {"imagen": "W_waffle.png", "palabra": "waffle"}
        ],
        "otras": []
    },
    {
        "letra": "Xx",
        "correctas": [
            {"imagen": "X_xilofono.png", "palabra": "xilófono"}
        ],
        "otras": []
    },
    {
        "letra": "Yy",
        "correctas": [
            {"imagen": "Y_yoyo.png", "palabra": "yoyo"},
            {"imagen": "Y_yegua.png", "palabra": "yegua"},
            {"imagen": "Y_yema.png", "palabra": "yema"}
        ],
        "otras": []
    },
    {
        "letra": "Zz",
        "correctas": [
            {"imagen": "Z_zapato.png", "palabra": "zapato"},
            {"imagen": "Z_zorro.png", "palabra": "zorro"},
            {"imagen": "Z_zanahoria.png", "palabra": "zanahoria"}
        ],
        "otras": []
    }
 
]

# Distractores automáticos: NO empiezan con prefijo y excluyen imágenes de sistema
prefijos = tuple(f"{chr(i)}_" for i in range(ord("A"), ord("Z")+1))
EXCLUIR_IMAGENES = ["Fondo.png", "palomita.png", "tachita.png", "Logo.png", "corazon.png", "avatar_feliz.png", "avatar_triste.png", "avatar_animo.png"]

todas_imagenes = os.listdir(ruta_img)
IMAGENES_DISTRACCION = [
    img for img in todas_imagenes
    if not img.startswith(prefijos)
    and img.endswith(".png")
    and img not in EXCLUIR_IMAGENES
]
def wrap_text(texto, fuente, max_ancho):
    """Devuelve una lista de líneas ajustadas al ancho dado."""
    palabras = texto.split(" ")
    lineas = []
    linea_actual = ""

    for palabra in palabras:
        prueba = (linea_actual + " " + palabra).strip()
        if fuente.size(prueba)[0] <= max_ancho:
            linea_actual = prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)
    return lineas

def dibujar_panel_con_texto(pantalla, rect, lineas, fuente, color_texto=(0,0,0),
                            color_fondo=(255,255,255,235), color_borde=(0,0,0),
                            grosor_borde=4, radio=25, padding=24, interlineado=10):
    """
    Dibuja un panel semitransparente y el texto dentro con padding y borde.
    - rect: pygame.Rect con posición y tamaño del panel
    - lineas: lista de cadenas ya envueltas (sin saltos '\n')
    """
    # Panel con alpha
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, color_fondo, panel.get_rect(), border_radius=radio)
    pygame.draw.rect(panel, color_borde, panel.get_rect(), grosor_borde, border_radius=radio)

    # Renderizar texto dentro del panel
    x_texto = padding
    y_texto = padding
    max_ancho_texto = rect.width - 2*padding

    for linea in lineas:
        # Si alguna línea ya viene muy larga, se vuelve a ajustar
        for sublinea in wrap_text(linea, fuente, max_ancho_texto):
            superficie = fuente.render(sublinea, True, color_texto)
            panel.blit(superficie, (x_texto, y_texto))
            y_texto += superficie.get_height() + interlineado

    # Blit del panel a pantalla
    pantalla.blit(panel, (rect.x, rect.y))


def pantalla_instrucciones():
    # Fuentes
    fuente_titulo = cargar_fuente(100, bold=True)
    fuente_texto  = cargar_fuente(40, bold=False)   # 🔹 más pequeña
    fuente_boton  = cargar_fuente(60, bold=True)

    # Dimensiones del panel
    panel_ancho = int(ANCHO * 0.78)
    panel_alto  = int(ALTO * 0.55)
    panel_rect  = pygame.Rect(
        (ANCHO - panel_ancho)//2,
        (ALTO - panel_alto)//2 + 40,
        panel_ancho,
        panel_alto
    )

    # Botón azul debajo del panel
    boton_ancho = 420
    boton_alto  = 100
    boton_rect = pygame.Rect(
        ANCHO // 2 - boton_ancho // 2,
        panel_rect.bottom + 20,   # 🔹 justo debajo del panel
        boton_ancho,
        boton_alto
    )

    # Texto de instrucciones (los 5 pasos completos)
    instrucciones = [
        "1. Mira la letra que aparece arriba.",
        "2. Haz clic en la imagen que EMPIECE con esa letra.",
        "3. Si aciertas, escucharás la palabra y sigues avanzando.",
        "4. Si fallas, perderás un corazón.",
        "¡Diviértete aprendiendo!"
    ]

    padding_panel = 24
    max_ancho_texto = panel_rect.width - 2*padding_panel
    lineas_envueltas = []
    for linea in instrucciones:
        lineas_envueltas.extend(wrap_text(linea, fuente_texto, max_ancho_texto))

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))

        # Título arriba
        titulo = fuente_titulo.render("Instrucciones", True, (0, 0, 0))
        pantalla.blit(titulo, (ANCHO//2 - titulo.get_width() // 2,
                               panel_rect.top - titulo.get_height() - 20))

        # Panel con texto
        dibujar_panel_con_texto(
            pantalla, panel_rect, lineas_envueltas, fuente_texto,
            color_texto=(0, 0, 0),
            color_fondo=(255, 255, 255, 240),
            color_borde=(0, 0, 0),
            grosor_borde=4,
            radio=30,
            padding=padding_panel,
            interlineado=8
        )

        # Botón azul (con hover)
        mouse_pos = pygame.mouse.get_pos()
        azul = (0, 102, 204)
        azul_hover = (30, 140, 255)
        color_boton = azul_hover if boton_rect.collidepoint(mouse_pos) else azul

        pygame.draw.rect(pantalla, color_boton, boton_rect, border_radius=25)
        texto_boton = fuente_boton.render("¡Iniciar!", True, (0, 0, 0))
        pantalla.blit(texto_boton, (
            boton_rect.centerx - texto_boton.get_width() // 2,
            boton_rect.centery - texto_boton.get_height() // 2
        ))

        pygame.display.flip()

        # Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if boton_rect.collidepoint(evento.pos):
                    return
            elif evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return

def pantalla_fin_juego(titulo="¡Se acabaron tus vidas!", color_titulo=(200, 0, 0)):
    """
    Pantalla que se muestra cuando el jugador pierde todas sus vidas.
    Muestra dos botones: 'Reintentar' y 'Menú principal'.
    Devuelve "reintentar" o "menu" según lo que elija el jugador.
    """
    fuente_titulo = cargar_fuente(90, bold=True)
    fuente_boton = cargar_fuente(55, bold=True)

    boton_ancho, boton_alto = 420, 100
    boton_reintentar = pygame.Rect(
        ANCHO // 2 - boton_ancho // 2,
        ALTO // 2 + 40,
        boton_ancho, boton_alto
    )
    boton_menu = pygame.Rect(
        ANCHO // 2 - boton_ancho // 2,
        ALTO // 2 + 40 + boton_alto + 30,
        boton_ancho, boton_alto
    )

    color_reintentar, color_reintentar_hover = PALETA["verde_activo"], PALETA["verde_activo_hover"]
    color_menu, color_menu_hover = PALETA["azul_principal"], PALETA["azul_principal_hover"]

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))

        y_avatar = 40
        if avatar_triste:
            x_avatar = ANCHO // 2 - avatar_triste.get_width() // 2
            pantalla.blit(avatar_triste, (x_avatar, y_avatar))
            y_titulo = y_avatar + avatar_triste.get_height() + 20
        else:
            y_titulo = y_avatar

        texto_titulo = fuente_titulo.render(titulo, True, color_titulo)
        pantalla.blit(texto_titulo, (ANCHO // 2 - texto_titulo.get_width() // 2, y_titulo))

        mouse_pos = pygame.mouse.get_pos()

        color_actual = color_reintentar_hover if boton_reintentar.collidepoint(mouse_pos) else color_reintentar
        pygame.draw.rect(pantalla, color_actual, boton_reintentar, border_radius=25)
        texto_reintentar = fuente_boton.render("Reintentar", True, (255, 255, 255))
        pantalla.blit(texto_reintentar, (
            boton_reintentar.centerx - texto_reintentar.get_width() // 2,
            boton_reintentar.centery - texto_reintentar.get_height() // 2
        ))

        color_actual = color_menu_hover if boton_menu.collidepoint(mouse_pos) else color_menu
        pygame.draw.rect(pantalla, color_actual, boton_menu, border_radius=25)
        texto_menu = fuente_boton.render("Menú principal", True, (255, 255, 255))
        pantalla.blit(texto_menu, (
            boton_menu.centerx - texto_menu.get_width() // 2,
            boton_menu.centery - texto_menu.get_height() // 2
        ))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if boton_reintentar.collidepoint(evento.pos):
                    return "reintentar"
                elif boton_menu.collidepoint(evento.pos):
                    return "menu"
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return "menu"
                elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "reintentar"

# Voz
def hablar(texto):
    if not audio_activado:
        return
    try:
        nombre_audio = None

        # Buscar audios por patrones comunes
        if texto.startswith("¿Cuál imagen empieza con la letra "):
            letra = texto.split("letra ")[1].replace("?", "")
            nombre_audio = f"pregunta_{letra}.mp3"

        elif texto.startswith("¡Correcto!"):
            partes = texto.replace("¡Correcto! ", "").split(" de ")
            if len(partes) == 2:
                letra = partes[0].strip()
                palabra = partes[1].strip()
                nombre_audio = f"correcto_{letra}_{palabra}.mp3"

        elif texto.lower() == "intenta otra vez":
            nombre_audio = "intenta_otra_vez.mp3"

        elif "se acabaron tus vidas" in texto.lower():
            nombre_audio = "vidas_terminadas.mp3"

        elif "felicidades" in texto.lower():
            nombre_audio = "felicidades.mp3"

        elif texto.strip().isalnum():  # solo palabra suelta
            nombre_audio = texto.strip() + ".mp3"

        if nombre_audio:
            ruta = os.path.join(ruta_audios, nombre_audio)
            if reproducir_audio_bloqueante(ruta):
                return  # termina si usó el audio

        # Si no se encuentra audio, usar pyttsx3 como respaldo
        engine.say(texto)
        engine.runAndWait()

    except Exception as e:
        print(f"Error al reproducir voz: {e}")
        engine.say(texto)
        engine.runAndWait()

# Imagen con marco circular grande y fondo blanco
_cache_imagenes = {}  # (nombre, tamaño) -> Surface ya procesada, para no reprocesar del disco cada vez

def cargar_imagen(nombre, tamaño=(300, 300)):
    clave = (nombre, tamaño)
    if clave in _cache_imagenes:
        return _cache_imagenes[clave]

    ruta = os.path.join(ruta_img, nombre)
    try:
        imagen = pygame.image.load(ruta).convert_alpha()

        # Escalar proporcionalmente
        imagen = escalar_imagen_con_proporcion(imagen, tamaño[0] - 50, tamaño[1] - 50)

        # Crear superficie circular
        imagen_redonda = pygame.Surface(tamaño, pygame.SRCALPHA)
        centro = (tamaño[0] // 2, tamaño[1] // 2)
        radio = tamaño[0] // 2
        pygame.draw.circle(imagen_redonda, (255, 255, 255, 255), centro, radio)

        # Centrar imagen escalada dentro del círculo
        rect_imagen = imagen.get_rect(center=centro)
        imagen_redonda.blit(imagen, rect_imagen)

        # Aplicar máscara circular
        mascara = pygame.Surface(tamaño, pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), centro, radio)
        imagen_redonda.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        _cache_imagenes[clave] = imagen_redonda
        return imagen_redonda

    except Exception as e:
        print(f"Error cargando imagen {ruta}: {e}")
        return None

def dibujar_candado(superficie, x, y, tamaño=28, color=(255, 255, 255), abierto=False):
    """Dibuja un candado simple (cerrado o abierto), centrado en (x, y)."""
    ancho_cuerpo = tamaño
    alto_cuerpo = int(tamaño * 0.75)
    cuerpo = pygame.Rect(0, 0, ancho_cuerpo, alto_cuerpo)
    cuerpo.center = (x, y + int(tamaño * 0.28))
    pygame.draw.rect(superficie, color, cuerpo, border_radius=5)

    radio_arco = int(tamaño * 0.32)
    grosor = max(3, tamaño // 7)
    rect_arco = pygame.Rect(0, 0, radio_arco * 2, int(radio_arco * 2.2))
    if abierto:
        rect_arco.center = (x + int(tamaño * 0.22), cuerpo.top - int(radio_arco * 0.15))
        pygame.draw.arc(superficie, color, rect_arco, 0.9, 4.0, width=grosor)
    else:
        rect_arco.center = (x, cuerpo.top + 2)
        pygame.draw.arc(superficie, color, rect_arco, 0, 3.1416, width=grosor)

    pygame.draw.circle(superficie, (90, 90, 90), cuerpo.center, max(2, tamaño // 9))


def dibujar_estrella(superficie, x, y, radio=18, color=(255, 255, 255)):
    """Dibuja una estrella de 5 puntas, centrada en (x, y)."""
    puntos = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        r = radio if i % 2 == 0 else radio * 0.45
        puntos.append((x + r * math.cos(ang), y - r * math.sin(ang)))
    pygame.draw.polygon(superficie, color, puntos)


def dibujar_altavoz(superficie, x, y, tamaño=28, color=(255, 255, 255), activo=True):
    """Dibuja un ícono de altavoz (con ondas si está activo, con X si está silenciado)."""
    ancho_r, alto_r = tamaño * 0.32, tamaño * 0.5
    rect = pygame.Rect(0, 0, ancho_r, alto_r)
    rect.center = (x - tamaño * 0.32, y)
    pygame.draw.rect(superficie, color, rect, border_radius=2)
    triangulo = [
        (rect.right - 2, rect.top),
        (rect.right + tamaño * 0.3, rect.top - tamaño * 0.22),
        (rect.right + tamaño * 0.3, rect.bottom + tamaño * 0.22),
        (rect.right - 2, rect.bottom),
    ]
    pygame.draw.polygon(superficie, color, triangulo)
    if activo:
        for i in range(1, 3):
            radio = tamaño * 0.22 * i + tamaño * 0.18
            rect_onda = pygame.Rect(0, 0, radio * 2, radio * 2)
            rect_onda.center = (int(rect.right + tamaño * 0.28), y)
            pygame.draw.arc(superficie, color, rect_onda, -0.6, 0.6, width=3)
    else:
        cx, cy = x + tamaño * 0.45, y
        s = tamaño * 0.2
        pygame.draw.line(superficie, color, (cx - s, cy - s), (cx + s, cy + s), 4)
        pygame.draw.line(superficie, color, (cx - s, cy + s), (cx + s, cy - s), 4)


def dibujar_burbuja(texto, x, y, ancho_max=300):
    fuente = FUENTES["burbuja"]
    texto_render = fuente.render(texto, True, (0, 0, 0))
    
    padding = 20
    ancho = texto_render.get_width() + padding * 2
    alto = texto_render.get_height() + padding * 2

    burbuja_rect = pygame.Rect(x, y, ancho, alto)
    
    # Dibuja fondo blanco con borde negro
    pygame.draw.rect(pantalla, (255, 255, 255), burbuja_rect, border_radius=15)
    pygame.draw.rect(pantalla, (0, 0, 0), burbuja_rect, 3, border_radius=15)
    
    # Dibuja triangulito (punta de burbuja)
    punta = [
        (x + 30, y + alto),  # vértice inferior
        (x + 50, y + alto + 20),
        (x + 70, y + alto)
    ]
    pygame.draw.polygon(pantalla, (255, 255, 255), punta)
    pygame.draw.polygon(pantalla, (0, 0, 0), punta, 3)

    # Dibuja texto encima
    pantalla.blit(texto_render, (x + padding, y + padding))

def minijuego_arrastrar_letra_opciones(letras_aprendidas, imagen_correcta, palabra):
    letra_objetivo = imagen_correcta.split("_")[0]  # Por ejemplo: A_abeja.png → "A"

    # Si hay menos de 3 letras aprendidas, usa todas
    if len(letras_aprendidas) < 3:
        letras_disponibles = letras_aprendidas.copy()
    else:
        letras_disponibles = random.sample(letras_aprendidas, k=3)

    # Asegurar que la letra correcta esté en las opciones
    if letra_objetivo not in letras_disponibles:
        letras_disponibles[random.randint(0, len(letras_disponibles)-1)] = letra_objetivo
    if letra_objetivo not in letras_disponibles:
        letras_disponibles[random.randint(0, 2)] = letra_objetivo  # asegurar que esté

    letras_disponibles.sort()  # opcional: ordenadas

    # Cargar imagen
    imagen = cargar_imagen(imagen_correcta, tamaño=(200, 200))
    if not imagen:
        return

    rect_imagen = imagen.get_rect(topleft=(100, ALTO // 2))
    arrastrando = False

# Posiciones letras
# Posiciones posibles centradas a la derecha
    posiciones_letras = [
        (ANCHO // 2 + 100, ALTO // 2 - 150),
        (ANCHO // 2 + 300, ALTO // 2),
        (ANCHO // 2 + 500, ALTO // 2 + 150)
    ]
    random.shuffle(posiciones_letras)

    # Barajar las letras también
    random.shuffle(letras_disponibles)

    # Renderizar letras y asociarlas a su posición
    rects_letras = []
    fuente = FUENTES["minijuego_letra"]

    for letra, (x, y) in zip(letras_disponibles, posiciones_letras):
        texto = fuente.render(letra, True, (0, 0, 0))
        rect = texto.get_rect(center=(x, y))
        rects_letras.append((letra, texto, rect))

    # Mostrar fondo y letras ANTES de hablar
    pantalla.blit(fondo, (0, 0))
    pantalla.blit(imagen, rect_imagen)

    for _, texto, rect in rects_letras:
        pygame.draw.rect(pantalla, (255, 255, 255), rect.inflate(30, 30))  # fondo blanco
        pygame.draw.rect(pantalla, (0, 0, 0), rect.inflate(30, 30), 4)
        pantalla.blit(texto, rect)

    pygame.display.flip()

    # Espera medio segundo antes de hablar
    pausa_activa(500)

    nombre_audio = f"minijuego_{imagen_correcta.split('_')[0]}_{palabra}.mp3"
    ruta_audio = os.path.join(ruta_audios, nombre_audio)
    if not reproducir_audio_bloqueante(ruta_audio):
        hablar(f"¿A qué letra corresponde {palabra}? Arrástrala")

    terminado = False
    while not terminado:
        reloj.tick(60)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if rect_imagen.collidepoint(evento.pos):
                    arrastrando = True
            elif evento.type == pygame.MOUSEBUTTONUP:
                arrastrando = False
                for letra, texto, rect in rects_letras:
                    if rect_imagen.colliderect(rect):
                        if letra == letra_objetivo:
                            ruta_muy_bien = os.path.join(ruta_audios, "muy_bien.mp3")
                            if not reproducir_audio_bloqueante(ruta_muy_bien):
                                hablar("¡Muy bien!")
                            terminado = True
                        else:
                            hablar("Intenta otra vez")
            elif evento.type == pygame.MOUSEMOTION and arrastrando:
                rect_imagen.center = evento.pos

        pantalla.blit(fondo, (0, 0))
        
        for _, texto, rect in rects_letras:
            pygame.draw.rect(pantalla, (255, 255, 255), rect.inflate(30, 30))  # fondo blanco
            pygame.draw.rect(pantalla, (0, 0, 0), rect.inflate(30, 30), 4)
            pantalla.blit(texto, rect)

        pantalla.blit(imagen, rect_imagen)
        pygame.display.flip()


def minijuego_rompecabezas_letra(info_letra):
    """
    Rompecabezas simple: la letra se parte en 2 piezas (arriba y abajo)
    y el jugador las arrastra hasta armar la letra completa. Sin vidas,
    sin límite de tiempo: es un ejercicio de forma/motricidad, no de
    memoria, así que no hay forma de "perder".
    """
    letra = info_letra["letra"]
    objeto = random.choice(info_letra["correctas"])
    color_letra = random.choice(COLORES_LETRAS)

    # --- Armar la letra grande en una superficie aparte, para poder partirla ---
    TAM_PIEZA_ANCHO = 260
    TAM_PIEZA_ALTO = 150  # cada pieza mide la mitad del alto de la letra completa
    ALTO_LETRA = TAM_PIEZA_ALTO * 2

    superficie_letra = pygame.Surface((TAM_PIEZA_ANCHO, ALTO_LETRA), pygame.SRCALPHA)
    fuente_grande = FUENTES["minijuego_letra"]
    render_letra = fuente_grande.render(letra, True, color_letra)
    rect_centrado = render_letra.get_rect(center=(TAM_PIEZA_ANCHO // 2, ALTO_LETRA // 2))
    superficie_letra.blit(render_letra, rect_centrado)

    pieza_arriba = superficie_letra.subsurface(pygame.Rect(0, 0, TAM_PIEZA_ANCHO, TAM_PIEZA_ALTO)).copy()
    pieza_abajo = superficie_letra.subsurface(pygame.Rect(0, TAM_PIEZA_ALTO, TAM_PIEZA_ANCHO, TAM_PIEZA_ALTO)).copy()

    # --- Posición final (objetivo) en el centro de la pantalla ---
    objetivo_x = ANCHO // 2 - TAM_PIEZA_ANCHO // 2
    objetivo_y = ALTO // 2 - ALTO_LETRA // 2
    objetivo_arriba = pygame.Rect(objetivo_x, objetivo_y, TAM_PIEZA_ANCHO, TAM_PIEZA_ALTO)
    objetivo_abajo = pygame.Rect(objetivo_x, objetivo_y + TAM_PIEZA_ALTO, TAM_PIEZA_ANCHO, TAM_PIEZA_ALTO)

    # --- Posiciones iniciales revueltas (una a cada lado de la pantalla) ---
    rect_arriba = pieza_arriba.get_rect(topleft=(150, ALTO - 300))
    rect_abajo = pieza_abajo.get_rect(topleft=(ANCHO - 150 - TAM_PIEZA_ANCHO, 150))

    piezas = [
        {"surf": pieza_arriba, "rect": rect_arriba, "objetivo": objetivo_arriba, "colocada": False},
        {"surf": pieza_abajo, "rect": rect_abajo, "objetivo": objetivo_abajo, "colocada": False},
    ]

    TOLERANCIA = 60  # qué tan cerca del objetivo debe soltarse para que "encaje"
    pieza_arrastrando = None

    # Imagen y palabra de apoyo, como contexto (opcional pero motivador)
    imagen_apoyo = cargar_imagen(objeto["imagen"], tamaño=(160, 160))

    fuente_instruccion = FUENTES["burbuja"]

    pantalla.blit(fondo, (0, 0))
    pygame.draw.rect(pantalla, (255, 255, 255), objetivo_arriba, 4, border_radius=10)
    pygame.draw.rect(pantalla, (255, 255, 255), objetivo_abajo, 4, border_radius=10)
    for pieza in piezas:
        pantalla.blit(pieza["surf"], pieza["rect"])
    pygame.display.flip()

    pausa_activa(400)
    hablar(f"Arma la letra {letra} uniendo las dos piezas")

    terminado = False
    while not terminado:
        reloj.tick(60)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                for pieza in piezas:
                    if not pieza["colocada"] and pieza["rect"].collidepoint(evento.pos):
                        pieza_arrastrando = pieza
                        break
            elif evento.type == pygame.MOUSEBUTTONUP:
                if pieza_arrastrando:
                    if pieza_arrastrando["rect"].colliderect(pieza_arrastrando["objetivo"].inflate(TOLERANCIA, TOLERANCIA)):
                        pieza_arrastrando["rect"].topleft = pieza_arrastrando["objetivo"].topleft
                        pieza_arrastrando["colocada"] = True
                        canal_efectos.play(sonido_correcto)
                    pieza_arrastrando = None
            elif evento.type == pygame.MOUSEMOTION and pieza_arrastrando:
                pieza_arrastrando["rect"].center = evento.pos
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                return

        pantalla.blit(fondo, (0, 0))

        instruccion = fuente_instruccion.render("Arrastra las piezas para armar la letra", True, (0, 0, 0))
        pantalla.blit(instruccion, (ANCHO // 2 - instruccion.get_width() // 2, 60))

        if imagen_apoyo:
            pantalla.blit(imagen_apoyo, (40, ALTO // 2 - 80))

        pygame.draw.rect(pantalla, (255, 255, 255), objetivo_arriba, 4, border_radius=10)
        pygame.draw.rect(pantalla, (255, 255, 255), objetivo_abajo, 4, border_radius=10)

        for pieza in piezas:
            pantalla.blit(pieza["surf"], pieza["rect"])

        pygame.display.flip()

        if all(p["colocada"] for p in piezas):
            terminado = True

    ruta_muy_bien = os.path.join(ruta_audios, "muy_bien.mp3")
    if not reproducir_audio_bloqueante(ruta_muy_bien):
        hablar(f"¡Excelente! Armaste la letra {letra}")
    pausa_activa(1200)



# Mostrar pantalla con palomita o tachita
def mostrar_pantalla(
    letra, opciones, imagen_correcta, color_letra, posiciones,
    mostrar_palomita=False, rect_palomita=None,
    mostrar_tachita=False, rect_tachita=None,
    estado_avatar="normal"  # nuevo parámetro
):
    global vidas

    pantalla.blit(fondo, (0, 0))

    fuente_letra = FUENTES["letra_grande"]
    fuente_palabra = FUENTES["palabra"]

    sombra = fuente_letra.render(letra, True, (0, 0, 0))
    pantalla.blit(sombra, (55, 55))

    texto = fuente_letra.render(letra, True, color_letra)
    pantalla.blit(texto, (50, 50))

    # Indicador de progreso dentro del nivel: una fila de puntos arriba,
    # al centro. Verde = ya superada, azul con borde = la actual,
    # gris = todavía faltan. Ayuda a saber cuánto falta sin tener que
    # preguntar o adivinar (reduce la incertidumbre/ansiedad).
    datos_nivel_actual = globals().get("datos_nivel")
    indice_actual = globals().get("indice")
    if letra != "" and datos_nivel_actual and indice_actual is not None:
        total_letras = len(datos_nivel_actual)
        radio_punto = 14
        espacio_punto = 38
        ancho_fila = (total_letras - 1) * espacio_punto
        x_inicio = ANCHO // 2 - ancho_fila // 2
        y_puntos = 36

        for i in range(total_letras):
            cx = x_inicio + i * espacio_punto
            if i < indice_actual:
                color_punto = PALETA["verde_activo"]
            elif i == indice_actual:
                color_punto = PALETA["azul_principal"]
            else:
                color_punto = PALETA["gris_bloqueado"]
            pygame.draw.circle(pantalla, color_punto, (cx, y_puntos), radio_punto)
            if i == indice_actual:
                pygame.draw.circle(pantalla, PALETA["texto_oscuro"], (cx, y_puntos), radio_punto, 3)

    if palabra_mostrada != "":
        color_palabra = random.choice(COLORES_LETRAS)
        texto_palabra = fuente_palabra.render(palabra_mostrada, True, color_palabra)
        sombra_palabra = fuente_palabra.render(palabra_mostrada, True, (0, 0, 0))

        x_palabra = (ANCHO // 2) - (texto_palabra.get_width() // 2)
        y_palabra = 250

        pantalla.blit(sombra_palabra, (x_palabra + 3, y_palabra + 3))
        pantalla.blit(texto_palabra, (x_palabra, y_palabra))

    botones = []
    rect_correcto = None

    for img_nombre, pos in zip(opciones, posiciones):
        imagen = cargar_imagen(img_nombre)
        if imagen:
            rect = imagen.get_rect(topleft=pos)
            pantalla.blit(imagen, pos)
            es_correcta = (img_nombre == imagen_correcta)
            botones.append((rect, es_correcta))
            if es_correcta:
                rect_correcto = rect

    if mostrar_palomita and rect_palomita:
        palomita_escalada = pygame.transform.smoothscale(palomita_img, (250, 250))
        palomita_rect = palomita_escalada.get_rect(center=rect_palomita.center)
        pantalla.blit(palomita_escalada, palomita_rect)

    if mostrar_tachita and rect_tachita:
        tachita_escalada = pygame.transform.smoothscale(tachita_img, (250, 250))
        tachita_rect = tachita_escalada.get_rect(center=rect_tachita.center)
        pantalla.blit(tachita_escalada, tachita_rect)

    # Mostrar avatar centrado arriba del texto de la palabra (si hay)
    avatar_a_usar = None
    if estado_avatar == "feliz":
        avatar_a_usar = avatar_feliz
    elif estado_avatar == "triste":
        avatar_a_usar = avatar_triste
    elif estado_avatar == "animo":
        avatar_a_usar = avatar_animo

    if avatar_a_usar:
        x_avatar = ANCHO // 2 - avatar_a_usar.get_width() // 2
        y_avatar = 20
        pantalla.blit(avatar_a_usar, (x_avatar, y_avatar))

    # Si es un avatar de ánimo, muestra burbuja Y reproduce el audio correspondiente
    if estado_avatar == "animo":
        frases_y_audios = [
            ("¡Vamos, tú puedes!", "animo_tu_puedes.mp3"),
            ("No te rindas", "animo_no_te_rindas.mp3"),
            ("Inténtalo otra vez", "animo_intentalo_otra_vez.mp3")
        ]
        frase, audio_file = random.choice(frases_y_audios)

        # Reproducir audio si existe (no bloqueante: sigue dibujando mientras suena)
        ruta_audio = os.path.join(ruta_audios, audio_file)
        if os.path.exists(ruta_audio):
            pygame.mixer.music.load(ruta_audio)
            pygame.mixer.music.play()

        # Dibuja la burbuja de texto
        burbuja_x = x_avatar + avatar_a_usar.get_width() + 10
        burbuja_y = y_avatar + 80
        dibujar_burbuja(frase, burbuja_x, burbuja_y)

    # Corazones (o símbolo de infinito si el modo libre está activo)
    if modo_libre:
        texto_infinito = FUENTES["infinito"].render("∞", True, (0, 102, 204))
        pantalla.blit(texto_infinito, (ANCHO - texto_infinito.get_width() - 30, 15))
    else:
        radio_marco = 30
        tamaño_corazon = 40
        corazon_escalado = pygame.transform.smoothscale(corazon_img, (tamaño_corazon, tamaño_corazon))

        for i in range(vidas):
            x = ANCHO - (i + 1) * (2 * radio_marco + 10)
            y = 20
            centro_x = x + radio_marco
            centro_y = y + radio_marco

            pygame.draw.circle(pantalla, (255, 255, 255), (centro_x, centro_y), radio_marco)
            corazon_rect = corazon_escalado.get_rect(center=(centro_x, centro_y))
            pantalla.blit(corazon_escalado, corazon_rect)

    pygame.display.flip()
    return botones, rect_correcto

def juego_letra(info):
    global palabra_mostrada
    palabra_mostrada = ""

    correcta = random.choice(info["correctas"])
    imagen_correcta = correcta["imagen"]
    palabra_correcta = correcta["palabra"]

    num_distractores = 2
    distraccion = info["otras"].copy()

    # Evitar distractores que empiecen con la misma letra
    letra_actual = info["letra"].lower()
    disponibles = [
        img for img in IMAGENES_DISTRACCION
        if img not in distraccion
        and img != imagen_correcta
        and not img.lower().startswith(letra_actual)
    ]
    random.shuffle(disponibles)
    distraccion += disponibles[:num_distractores - len(distraccion)]

    opciones = distraccion + [imagen_correcta]
    random.shuffle(opciones)

    color_letra = random.choice(COLORES_LETRAS)

    desplazamiento_vertical = 180
    posiciones = [
        (ANCHO // 4 - 150, ALTO // 2 - 150 + desplazamiento_vertical),
        (ANCHO // 2 - 150, ALTO // 2 - 150 + desplazamiento_vertical),
        (3 * ANCHO // 4 - 150, ALTO // 2 - 150 + desplazamiento_vertical)
    ]
    random.shuffle(posiciones)

    botones, rect_correcto = mostrar_pantalla(info["letra"], opciones, imagen_correcta, color_letra, posiciones)
    hablar(f"¿Cuál imagen empieza con la letra {info['letra']}?")
    return botones, palabra_correcta, imagen_correcta, color_letra, opciones, posiciones

# ============================
# Definición de niveles
# ============================
# Se agrupan las 27 letras en 6 niveles. Completar un nivel desbloquea
# el siguiente. El progreso se guarda solo durante esta partida (se
# reinicia al cerrar el juego).
NIVELES = [
    {"nombre": "Nivel 1: A - E", "datos": datos[0:5]},
    {"nombre": "Nivel 2: F - J", "datos": datos[5:10]},
    {"nombre": "Nivel 3: K - Ñ", "datos": datos[10:15]},
    {"nombre": "Nivel 4: O - S", "datos": datos[15:20]},
    {"nombre": "Nivel 5: T - W", "datos": datos[20:24]},
    {"nombre": "Nivel 6: X - Z", "datos": datos[24:27]},
    {
        "nombre": "Nivel 7: Rompecabezas 1",
        "tipo": "rompecabezas",
        # Una letra representativa de cada uno de los 6 niveles anteriores
        "datos": [datos[0], datos[5], datos[10], datos[15], datos[20], datos[24]],
    },
    {
        "nombre": "Nivel 8: Rompecabezas 2",
        "tipo": "rompecabezas",
        # Otro grupo de 6 letras, distinto al del Nivel 7
        "datos": [datos[2], datos[7], datos[12], datos[17], datos[22], datos[25]],
    },
]

niveles_completados = set()  # índices de niveles ya terminados en esta sesión


def nivel_desbloqueado(i):
    """
    Regla de desbloqueo de niveles:
    - Los niveles de rompecabezas SIEMPRE están disponibles, sin
      importar qué tanto se haya avanzado en los niveles de letras.
      Son una vía libre de entrada, no un premio por completar lo demás.
    - Los niveles de letras siguen el orden de siempre: el primero
      siempre abierto, los demás se desbloquean al completar el anterior.
    - En Modo libre, todo está disponible.
    """
    if modo_libre:
        return True
    if NIVELES[i].get("tipo", "letras") == "rompecabezas":
        return True
    return (i == 0) or ((i - 1) in niveles_completados)


def pantalla_seleccion_niveles():
    """
    Muestra los niveles disponibles en una cuadrícula de botones.
    Los niveles de letras se desbloquean en orden; los niveles de
    rompecabezas están siempre disponibles (ver nivel_desbloqueado).
    Devuelve el índice del nivel elegido.
    """
    fuente_titulo = cargar_fuente(90, bold=True)
    fuente_boton = cargar_fuente(40, bold=True)
    fuente_estado = cargar_fuente(26, bold=True)

    columnas = 3
    boton_ancho, boton_alto = 380, 140
    espacio_x, espacio_y = 50, 50

    total_ancho = columnas * boton_ancho + (columnas - 1) * espacio_x
    x_inicial = ANCHO // 2 - total_ancho // 2
    y_inicial = ALTO // 2 - 160

    rects_niveles = []
    for i in range(len(NIVELES)):
        fila = i // columnas
        col = i % columnas
        x = x_inicial + col * (boton_ancho + espacio_x)
        y = y_inicial + fila * (boton_alto + espacio_y)
        rects_niveles.append(pygame.Rect(x, y, boton_ancho, boton_alto))

    color_desbloqueado = PALETA["verde_activo"]
    color_desbloqueado_hover = PALETA["verde_activo_hover"]
    color_bloqueado = PALETA["gris_bloqueado"]
    color_borde_completado = PALETA["dorado_completado"]

    while True:
        reloj.tick(60)
        pantalla.blit(fondo, (0, 0))

        titulo = fuente_titulo.render("Elige un nivel", True, (0, 0, 0))
        pantalla.blit(titulo, (ANCHO // 2 - titulo.get_width() // 2, 60))

        if modo_libre:
            fuente_aviso = cargar_fuente(34, bold=True)
            aviso = fuente_aviso.render("Modo libre activado: sin vidas, todos los niveles disponibles", True, (0, 102, 204))
            pantalla.blit(aviso, (ANCHO // 2 - aviso.get_width() // 2, 60 + titulo.get_height() + 10))

        mouse_pos = pygame.mouse.get_pos()

        for i, rect in enumerate(rects_niveles):
            desbloqueado = nivel_desbloqueado(i)
            completado = i in niveles_completados

            if not desbloqueado:
                color = color_bloqueado
            elif rect.collidepoint(mouse_pos):
                color = color_desbloqueado_hover
            else:
                color = color_desbloqueado

            pygame.draw.rect(pantalla, color, rect, border_radius=20)
            grosor_borde = 6 if completado else 3
            color_borde = color_borde_completado if completado else (0, 0, 0)
            pygame.draw.rect(pantalla, color_borde, rect, grosor_borde, border_radius=20)

            texto_nombre = fuente_boton.render(NIVELES[i]["nombre"], True, (255, 255, 255) if desbloqueado else (90, 90, 90))
            if texto_nombre.get_width() > rect.width - 20:
                fuente_boton_chica = cargar_fuente(28, bold=True)
                texto_nombre = fuente_boton_chica.render(NIVELES[i]["nombre"], True, (255, 255, 255) if desbloqueado else (90, 90, 90))
            pantalla.blit(texto_nombre, (
                rect.centerx - texto_nombre.get_width() // 2,
                rect.centery - texto_nombre.get_height() // 2 - 15
            ))

            if not desbloqueado:
                texto_estado = "Bloqueado"
            elif completado:
                texto_estado = "¡Completado!"
            else:
                texto_estado = ""

            if texto_estado:
                render_estado = fuente_estado.render(texto_estado, True, (255, 255, 255) if desbloqueado else (90, 90, 90))
                pantalla.blit(render_estado, (
                    rect.centerx - render_estado.get_width() // 2,
                    rect.centery + 25
                ))

            # Icono: candado si está bloqueado, estrella si está completado
            # (el color y el texto ya lo indican, pero el icono lo refuerza
            # de forma visual para quien prefiera no depender de leer texto)
            if not desbloqueado:
                dibujar_candado(pantalla, rect.right - 28, rect.top + 26, tamaño=26, color=(255, 255, 255))
            elif completado:
                dibujar_estrella(pantalla, rect.right - 28, rect.top + 26, radio=16, color=PALETA["dorado_completado"])

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(rects_niveles):
                    desbloqueado = nivel_desbloqueado(i)
                    if desbloqueado and rect.collidepoint(evento.pos):
                        return i
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


# Bucle principal
saltar_menu = False   # Si es True (viene de "Reintentar"), no se repiten intro/instrucciones
nivel_forzado = None  # Si viene de "Reintentar", repite el mismo nivel sin pasar por el menú de niveles

while True:
    if not saltar_menu:
        pantalla_inicio()
        pantalla_instrucciones()   # ← ahora aparece la ventanita legible
    saltar_menu = False

    if nivel_forzado is not None:
        nivel_idx = nivel_forzado
        nivel_forzado = None
    else:
        nivel_idx = pantalla_seleccion_niveles()

    tipo_nivel = NIVELES[nivel_idx].get("tipo", "letras")

    if tipo_nivel == "rompecabezas":
        for info_letra in NIVELES[nivel_idx]["datos"]:
            minijuego_rompecabezas_letra(info_letra)

        niveles_completados.add(nivel_idx)

        if len(niveles_completados) == len(NIVELES):
            hablar("¡Felicidades! Has terminado el abecedario.")
            mostrar_pantalla(
                letra="",
                opciones=[],
                imagen_correcta="",
                color_letra=(0, 0, 0),
                posiciones=[],
                estado_avatar="feliz"
            )
            pausa_activa(2500)
        else:
            hablar("¡Nivel completado!")

        continue  # vuelve al menú / selección de niveles

    datos_nivel = NIVELES[nivel_idx]["datos"]

    vidas = 5
    indice = 0
    botones, palabra_actual, imagen_correcta, color_letra, opciones_actuales, posiciones_actuales = juego_letra(datos_nivel[indice])

    corriendo = True
    while corriendo:
        reloj.tick(60)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif evento.type == pygame.MOUSEBUTTONDOWN:
                for rect, es_correcta in botones:
                    if rect.collidepoint(evento.pos):
                        if es_correcta:
                            canal_efectos.play(sonido_correcto)
                            hablar(f"¡Correcto! {datos_nivel[indice]['letra']} de {palabra_actual}")
                            palabra_mostrada = palabra_actual

                            botones, rect_correcto = mostrar_pantalla(
                                datos_nivel[indice]['letra'],
                                opciones_actuales,
                                imagen_correcta,
                                color_letra,
                                posiciones_actuales,
                                mostrar_palomita=True,
                                rect_palomita=rect,
                                estado_avatar="feliz"
                            )
                            pausa_activa(3000)

                            indice += 1

                            if indice < len(datos_nivel):
                                botones, palabra_actual, imagen_correcta, color_letra, opciones_actuales, posiciones_actuales = juego_letra(datos_nivel[indice])
                            else:
                                # Se terminaron las letras de este nivel: minijuego de repaso
                                letras_del_nivel = [d["letra"] for d in datos_nivel]
                                info_repaso = random.choice(datos_nivel)
                                objeto_repaso = random.choice(info_repaso["correctas"])

                                minijuego_arrastrar_letra_opciones(
                                    letras_del_nivel,
                                    objeto_repaso["imagen"],
                                    objeto_repaso["palabra"]
                                )

                                niveles_completados.add(nivel_idx)

                                if len(niveles_completados) == len(NIVELES):
                                    hablar("¡Felicidades! Has terminado el abecedario.")
                                    mostrar_pantalla(
                                        letra="",
                                        opciones=[],
                                        imagen_correcta="",
                                        color_letra=(0, 0, 0),
                                        posiciones=[],
                                        estado_avatar="feliz"
                                    )
                                    pausa_activa(2500)
                                else:
                                    hablar("¡Nivel completado!")

                                corriendo = False

                        else:
                            canal_efectos.play(sonido_error)
                            hablar("Intenta otra vez")

                            if not modo_libre:
                                vidas -= 1
                                if vidas <= 0:
                                    hablar("¡Se acabaron tus vidas!")
                                    mostrar_pantalla(
                                        letra=datos_nivel[indice]['letra'],
                                        opciones=opciones_actuales,
                                        imagen_correcta=imagen_correcta,
                                        color_letra=color_letra,
                                        posiciones=posiciones_actuales,
                                        estado_avatar="triste"
                                    )
                                    pausa_activa(1500)

                                    accion = pantalla_fin_juego("¡Se acabaron tus vidas!")
                                    if accion == "reintentar":
                                        saltar_menu = True     # No repetir intro/instrucciones
                                        nivel_forzado = nivel_idx  # Repetir el mismo nivel

                                    corriendo = False
                                    break

                            botones, _ = mostrar_pantalla(
                                datos_nivel[indice]['letra'],
                                opciones_actuales,
                                imagen_correcta,
                                color_letra,
                                posiciones_actuales,
                                mostrar_tachita=True,
                                rect_tachita=rect,
                                estado_avatar="triste"
                            )
                            pausa_activa(2000)

                            botones, _ = mostrar_pantalla(
                                datos_nivel[indice]['letra'],
                                opciones_actuales,
                                imagen_correcta,
                                color_letra,
                                posiciones_actuales,
                                estado_avatar="animo"
                            )
                            pausa_activa(1500)

            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    corriendo = False


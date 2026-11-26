"""aplicar_voz.py: conecta el micrófono con main.py.

Uso (con la terminal en la carpeta del proyecto, donde está main.py):

    python aplicar_voz.py

Qué hace:
  1. Guarda una copia de seguridad en main.py.bak
  2. Agrega a main.py el botón de micrófono y la lógica para responder hablando
  2b. Corrige el nombre de los audios de la pregunta y del '¡Correcto!' (ver cambio e y f)
  3. Si algo no coincide con tu main.py, NO cambia nada y te dice qué falló

Para deshacerlo:  git checkout main.py   (o copiar main.py.bak sobre main.py)
Para apagar la voz sin deshacer: en main.py pon VOZ_HABILITADA = False
"""
import shutil
import sys

ARCHIVO = "main.py"

# ---------------------------------------------------------------- 1) imports
# Los import de voz van dentro del bloque que se inserta antes de mostrar_pantalla,
# así no se toca la cabecera del archivo.

# ------------------------------------------- 2) bloque nuevo (funciones de voz)
BLOQUE_VOZ = '''# ============================
# Voz del niño (micrófono)
# ============================
# Agregado por aplicar_voz.py. El niño puede tocar la imagen o pulsar el botón del
# micrófono (o la barra espaciadora) y decir el nombre de la imagen.
VOZ_HABILITADA = True    # False = el juego funciona como antes, sin micrófono
VOZ_SIMULADA = False     # True = sin micrófono: F1 simula acierto, F2 error y F3 "no se entendió"

try:
    import voz
    from respuestas import evaluar as evaluar_voz
    VOZ_DISPONIBLE = True
except Exception as _error_voz:
    VOZ_DISPONIBLE = False
    print("Voz desactivada (falta una librería o un archivo):", _error_voz)

voz_activa = False
estado_voz = "reposo"          # "reposo" o "escuchando"
_volumen_antes_de_escuchar = None
RADIO_MICROFONO = 55
CENTRO_MICROFONO = (95, ALTO - 110)
AREA_MICROFONO = pygame.Rect(10, ALTO - 215, 175, 205)
_fuente_microfono = None


def iniciar_voz():
    global voz_activa
    if not (VOZ_HABILITADA and VOZ_DISPONIBLE):
        return
    try:
        voz.iniciar(simulado=VOZ_SIMULADA)
        voz_activa = True
    except Exception as error:
        print("Voz desactivada:", error)


def voz_utilizable():
    """True si hay que mostrar y atender el botón del micrófono."""
    return voz_activa and not voz.error_inicio()


def dibujar_boton_microfono(actualizar=False):
    global _fuente_microfono
    if not voz_utilizable():
        return
    if _fuente_microfono is None:
        _fuente_microfono = cargar_fuente(26, bold=True)
    pantalla.blit(fondo, AREA_MICROFONO.topleft, AREA_MICROFONO)   # borra lo dibujado antes
    escuchando = (estado_voz == "escuchando")
    cx, cy = CENTRO_MICROFONO
    color = (220, 60, 60) if escuchando else PALETA["azul_principal"]
    blanco = (255, 255, 255)
    pygame.draw.circle(pantalla, (0, 0, 0), (cx + 3, cy + 4), RADIO_MICROFONO)
    pygame.draw.circle(pantalla, color, (cx, cy), RADIO_MICROFONO)
    pygame.draw.circle(pantalla, blanco, (cx, cy), RADIO_MICROFONO, 4)
    pygame.draw.rect(pantalla, blanco, (cx - 11, cy - 30, 22, 38), border_radius=11)
    pygame.draw.arc(pantalla, blanco, (cx - 22, cy - 22, 44, 44), math.pi, 2 * math.pi, 4)
    pygame.draw.line(pantalla, blanco, (cx, cy + 22), (cx, cy + 32), 4)
    pygame.draw.line(pantalla, blanco, (cx - 12, cy + 32), (cx + 12, cy + 32), 4)
    texto = "Escuchando..." if escuchando else "Habla"
    sombra = _fuente_microfono.render(texto, True, (0, 0, 0))
    render = _fuente_microfono.render(texto, True, blanco)
    x = cx - render.get_width() // 2
    y = cy + RADIO_MICROFONO + 8
    pantalla.blit(sombra, (x + 2, y + 2))
    pantalla.blit(render, (x, y))
    if actualizar:
        pygame.display.update(AREA_MICROFONO)


def boton_microfono_tocado(pos):
    if not voz_utilizable():
        return False
    dx, dy = pos[0] - CENTRO_MICROFONO[0], pos[1] - CENTRO_MICROFONO[1]
    return dx * dx + dy * dy <= (RADIO_MICROFONO + 10) ** 2


def palabra_de_imagen(nombre):
    """'A_abeja.png' -> 'abeja'; 'barco.png' -> 'barco'."""
    base = nombre.rsplit(".", 1)[0]
    return base.split("_", 1)[1] if "_" in base else base


def rect_de_opcion(i):
    imagen = cargar_imagen(opciones_actuales[i])
    return imagen.get_rect(topleft=posiciones_actuales[i]) if imagen else None


def redibujar_nivel():
    global botones
    botones, _ = mostrar_pantalla(
        datos_nivel[indice]["letra"], opciones_actuales, imagen_correcta,
        color_letra, posiciones_actuales
    )


def activar_escucha():
    """El niño pulsó el micrófono: empieza a escuchar sin congelar el juego."""
    global estado_voz, _volumen_antes_de_escuchar
    if VOZ_SIMULADA or not voz_utilizable() or not voz.listo() or voz.escuchando():
        return
    voz.empezar_a_escuchar()
    estado_voz = "escuchando"
    try:
        _volumen_antes_de_escuchar = pygame.mixer.music.get_volume()
        pygame.mixer.music.set_volume(0.0)      # que la música no entre al micrófono
    except pygame.error:
        _volumen_antes_de_escuchar = None
    dibujar_boton_microfono(actualizar=True)


def terminar_escucha():
    global estado_voz, _volumen_antes_de_escuchar
    estado_voz = "reposo"
    if _volumen_antes_de_escuchar is not None:
        try:
            pygame.mixer.music.set_volume(_volumen_antes_de_escuchar)
        except pygame.error:
            pass
        _volumen_antes_de_escuchar = None
    dibujar_boton_microfono(actualizar=True)


def descartar_voz_pendiente():
    """Si el niño toca una imagen con el mouse, se ignora lo que el micrófono esté escuchando."""
    if voz_activa:
        voz.detener()
        terminar_escucha()


def avisar_no_se_entendio():
    dibujar_burbuja("¡No te entendí!", ANCHO // 2 + 40, 110)
    pygame.display.flip()
    hablar("Intenta otra vez")          # no quita vidas
    redibujar_nivel()


def avisar_problema_voz(estado):
    global voz_activa
    if estado == "sin_microfono":
        voz_activa = False
        texto = "No encuentro el micrófono"
    else:
        texto = "Sin internet: usa el mouse"
    dibujar_burbuja(texto, ANCHO // 2 - 150, 110)
    pygame.display.flip()
    pausa_activa(2500)
    redibujar_nivel()


def simular_respuesta(tipo):
    """Solo con VOZ_SIMULADA: F1 = dice la imagen correcta, F2 = una incorrecta, F3 = algo confuso."""
    if not (VOZ_SIMULADA and voz_utilizable()):
        return
    if tipo == 1:
        dicho = palabra_de_imagen(imagen_correcta)
    elif tipo == 2:
        dicho = next(palabra_de_imagen(o) for o in opciones_actuales if o != imagen_correcta)
    else:
        dicho = "xyz"
    voz.empezar_a_escuchar()
    voz.simular(dicho)


def revisar_voz():
    """Se llama en cada vuelta del bucle: si ya hay respuesta hablada, la procesa."""
    r = voz.resultado()
    if r is None:
        return
    terminar_escucha()
    if r.estado == "texto":
        palabras = [palabra_de_imagen(n) for n in opciones_actuales]
        v = evaluar_voz(r.texto, palabra_de_imagen(imagen_correcta), palabras)
        if v.estado == "no_claro":
            avisar_no_se_entendio()
            return
        rect = rect_de_opcion(palabras.index(v.opcion))
        if rect is not None:
            # Se manda como si el niño hubiera tocado esa imagen: así valen los mismos
            # puntos, vidas, sonidos y animaciones que con el mouse.
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))
    elif r.estado == "no_entendio":
        avisar_no_se_entendio()
    elif r.estado in ("sin_internet", "sin_microfono"):
        avisar_problema_voz(r.estado)
    # "silencio": nadie habló, no se hace nada


iniciar_voz()


'''

# ------------------------------------------------ 3) cambios en lugares existentes
CAMBIOS = [
    (   # a) el bloque de voz va justo antes de mostrar_pantalla
        "def mostrar_pantalla(\n",
        BLOQUE_VOZ + "def mostrar_pantalla(\n",
    ),
    (   # b) el botón se dibuja en cada pantalla de nivel
        "    pygame.display.flip()\n    return botones, rect_correcto\n",
        "    if opciones:\n        dibujar_boton_microfono()\n"
        "    pygame.display.flip()\n    return botones, rect_correcto\n",
    ),
    (   # c) clic en el micrófono, barra espaciadora y teclas de simulación
        "            elif evento.type == pygame.MOUSEBUTTONDOWN:\n"
        "                for rect, es_correcta in botones:\n",
        "            elif evento.type == pygame.MOUSEBUTTONDOWN and boton_microfono_tocado(evento.pos):\n"
        "                activar_escucha()\n\n"
        "            elif evento.type == pygame.KEYDOWN and voz_activa and evento.key == pygame.K_SPACE:\n"
        "                activar_escucha()\n\n"
        "            elif evento.type == pygame.KEYDOWN and VOZ_SIMULADA and evento.key in (pygame.K_F1, pygame.K_F2, pygame.K_F3):\n"
        "                simular_respuesta({pygame.K_F1: 1, pygame.K_F2: 2, pygame.K_F3: 3}[evento.key])\n\n"
        "            elif evento.type == pygame.MOUSEBUTTONDOWN:\n"
        "                descartar_voz_pendiente()\n"
        "                for rect, es_correcta in botones:\n",
    ),
    (   # d) en cada vuelta del bucle se revisa si ya hay respuesta hablada
        "            elif evento.type == pygame.KEYDOWN:\n"
        "                if evento.key == pygame.K_ESCAPE:\n"
        "                    corriendo = False",
        "            elif evento.type == pygame.KEYDOWN:\n"
        "                if evento.key == pygame.K_ESCAPE:\n"
        "                    corriendo = False\n\n"
        "        if voz_activa:\n"
        "            revisar_voz()",
    ),
    (   # e) CORRECCIÓN DE AUDIOS: el juego busca 'pregunta_Aa.mp3' pero el archivo se llama 'pregunta_A.mp3'
        '            letra = texto.split("letra ")[1].replace("?", "")\n',
        '            letra = texto.split("letra ")[1].replace("?", "").strip()[:1].upper()  # "Aa" -> "A"\n',
    ),
    (   # f) lo mismo para el audio de "¡Correcto! Aa de abeja" (archivo correcto_A_abeja.mp3)
        '                letra = partes[0].strip()\n',
        '                letra = partes[0].strip()[:1].upper()  # "Aa" -> "A"\n',
    ),
]


def main():
    try:
        with open(ARCHIVO, "rb") as f:
            crudo = f.read()
    except FileNotFoundError:
        print(f"No encuentro {ARCHIVO}. Ejecuta este programa en la carpeta del juego.")
        sys.exit(1)

    usa_crlf = b"\r\n" in crudo
    texto = crudo.decode("utf-8").replace("\r\n", "\n")

    if "VOZ_HABILITADA" in texto:
        print("main.py ya tiene la voz aplicada. No se cambió nada.")
        return

    nuevo = texto
    for n, (antes, despues) in enumerate(CAMBIOS, 1):
        veces = nuevo.count(antes)
        if veces != 1:
            print(f"No se aplicó NINGÚN cambio: el punto {n} se encontró {veces} veces (debía ser 1).")
            print("Tu main.py es distinto al que revisé. Pásame el mensaje y lo ajusto.")
            print("Fragmento buscado:\n" + antes)
            sys.exit(1)
        nuevo = nuevo.replace(antes, despues)

    try:
        compile(nuevo, ARCHIVO, "exec")
    except SyntaxError as error:
        print("El resultado tendría un error de sintaxis; no se cambió nada:", error)
        sys.exit(1)

    shutil.copyfile(ARCHIVO, ARCHIVO + ".bak")
    if usa_crlf:
        nuevo = nuevo.replace("\n", "\r\n")
    with open(ARCHIVO, "wb") as f:
        f.write(nuevo.encode("utf-8"))
    print("Listo. Se guardó la copia de seguridad en main.py.bak")
    print("Abre el juego con:  python main.py")


if __name__ == "__main__":
    main()
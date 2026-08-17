# consola.py - Interfaz de consola con menu interactivo por flechas
# Mantiene toda la logica original; solo cambia la presentacion y la interaccion.
# Navegacion: flechas arriba/abajo, Enter para seleccionar, ESC para volver/salir.

import os
import time
import msvcrt

from modelos import Imperio, Diplomacia, otro_imperio
from mapa import (
    crear_mapa, asignar_provincias_iniciales, buscar_provincia,
    mostrar_mapa, mostrar_mapa_por_dueño, mostrar_estado_imperios,
)
from economia import calcular_actividad_comercial
from poblacion import poblacion_total
from unidades import reclutar_soldados, construir_torre_vigilancia, recalcular_unidades_totales
from diplomacia import mostrar_relaciones
from constantes import C_PA_SAQUEO, DURACION_SAQUEO
from combat import ordenar_movimiento, fortificar_provincia, saquear, C_PA_MOVIMIENTO
from lef import LEF
from turno import cierre_de_turno
from ia import IA_CPU


ANCHO = 58


# ═══════════════════════════════════════════════════════════════════════
#  UTILIDADES DE CONSOLA
# ═══════════════════════════════════════════════════════════════════════

def limpiar():
    """Limpia la pantalla de la consola."""
    os.system('cls' if os.name == 'nt' else 'clear')


def leer_tecla():
    """Lee una tecla del teclado y retorna un identificador.
    Flechas -> 'arriba'/'abajo', Enter -> 'enter', Escape -> 'escape'."""
    t = msvcrt.getch()
    if t in (b'\x00', b'\xe0'):
        t2 = msvcrt.getch()
        return {b'H': 'arriba', b'P': 'abajo'}.get(t2, '')
    if t == b'\r':
        return 'enter'
    if t == b'\x1b':
        return 'escape'
    try:
        return t.decode('utf-8')
    except Exception:
        return ''


def elegir(opciones, titulo, subtitulo="", lineas_extra=None):
    """Muestra un menu navegable con flechas. Retorna el indice seleccionado
    o -1 si se presiono ESC."""
    sel = 0
    while True:
        limpiar()
        borde = "=" * ANCHO
        linea = "-" * ANCHO
        print()
        print(f"  {borde}")
        print(f"  {titulo}")
        print(f"  {borde}")
        if subtitulo:
            print(f"  {subtitulo}")
        if lineas_extra:
            for l in lineas_extra:
                print(f"  {l}")
        print()
        for i, op in enumerate(opciones):
            if i == sel:
                print(f"    >>> {op}")
            else:
                print(f"        {op}")
        print()
        print(f"  {linea}")
        print("  Flechas: navegar  |  ENTER: seleccionar  |  ESC: volver")
        print(f"  {borde}")

        k = leer_tecla()
        if k == 'arriba':
            sel = (sel - 1) % len(opciones)
        elif k == 'abajo':
            sel = (sel + 1) % len(opciones)
        elif k == 'enter':
            return sel
        elif k == 'escape':
            return -1


def mostrar_mensaje(texto, tipo="info"):
    """Muestra un mensaje con pausa. Error: 1.5s, exito/info: 1s."""
    limpiar()
    borde = "=" * ANCHO
    print()
    print(f"  {borde}")
    if tipo == "error":
        print(f"  [X] {texto}")
    elif tipo == "exito":
        print(f"  [OK] {texto}")
    else:
        print(f"  {texto}")
    print(f"  {borde}")
    time.sleep(1.0 if tipo == "error" else 1.0)


def leer_numero(prompt):
    """Limpia la pantalla, muestra un prompt y lee un entero.
    Retorna el entero o None si la entrada es invalida."""
    limpiar()
    print()
    print(f"  {'=' * ANCHO}")
    print(f"  {prompt}")
    print(f"  {'-' * ANCHO}")
    try:
        return int(input("  > "))
    except (ValueError, EOFError):
        return None


def mapa_lineas(mapa, imperio_jugador):
    """Genera lineas compactas del mapa por duenio para el menu principal."""
    lineas = ["  Mapa por duenio:"]
    for fila in mapa:
        partes = []
        for prov in fila:
            if prov.dueño is imperio_jugador:
                partes.append(f"[{prov.id:02d}J]")
            elif prov.dueño:
                partes.append(f"[{prov.id:02d}I]")
            else:
                partes.append(f"[{prov.id:02d} ]")
        lineas.append("    " + " ".join(partes))
    return lineas


# ═══════════════════════════════════════════════════════════════════════
#  SELECCION DE PROVINCIAS (listas navegables con flechas)
# ═══════════════════════════════════════════════════════════════════════

def formato_prov(prov):
    """Devuelve una linea descriptiva para una provincia en una lista."""
    duenio = prov.dueño.nombre if prov.dueño else "Libre"
    return (
        f"P{prov.id:02d} ({duenio:>6})  "
        f"Pob:{prov.poblacion:>8,.0f}  "
        f"Fel:{prov.felicidad:>5.1f}  "
        f"Sold:{prov.u_prov:>4}"
    )


def elegir_provincia_jugador(mapa, imperio, titulo):
    """Lista las provincias del jugador para seleccionar con flechas.
    Retorna la provincia elegida o None si ESC."""
    provs = [p for fila in mapa for p in fila if p.dueño is imperio]
    if not provs:
        mostrar_mensaje("No tienes provincias disponibles", "error")
        return None
    idx = elegir([formato_prov(p) for p in provs], titulo)
    return provs[idx] if idx >= 0 else None


def elegir_provincia_mapa(mapa, titulo):
    """Lista todas las provincias del mapa para seleccionar con flechas.
    Retorna la provincia elegida o None si ESC."""
    provs = [p for fila in mapa for p in fila]
    idx = elegir([formato_prov(p) for p in provs], titulo)
    return provs[idx] if idx >= 0 else None



#  ACCIONES DEL JUEGO 

def accion_reclutar(mapa, imperio_jugador):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "RECLUTAR SOLDADOS - Seleccionar provincia")
    if prov is None:
        return
    cant = leer_numero(
        f"RECLUTAR en P{prov.id:02d}\n"
        f"  Pob: {prov.poblacion:,.0f}  Fel: {prov.felicidad:.1f}  Sold: {prov.u_prov}\n"
        f"\n  Cantidad de soldados a reclutar:")
    if cant is None or cant <= 0:
        mostrar_mensaje("Cantidad invalida", "error")
        return
    res = reclutar_soldados(imperio_jugador, prov, cant)
    if res["ok"]:
        mostrar_mensaje(
            f"Reclutados {res['cantidad']} soldados en P{prov.id:02d}\n"
            f"  -{res['costo_oro']:.1f} oro, -{res['costo_poblacion']:,} pob, -1 PA",
            "exito")
    else:
        mostrar_mensaje(f"No se pudo reclutar: {res['motivo']}", "error")


def accion_torre(mapa, imperio_jugador):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "CONSTRUIR TORRE - Seleccionar provincia")
    if prov is None:
        return
    res = construir_torre_vigilancia(imperio_jugador, prov)
    if res["ok"]:
        mostrar_mensaje(
            f"Torre de Vigilancia construida en P{prov.id:02d}\n"
            f"  -{res['costo_oro']:.1f} oro, -{res['costo_pa']:.1f} PA",
            "exito")
    else:
        mostrar_mensaje(f"No se pudo construir la torre: {res['motivo']}", "error")


def accion_mover(mapa, diplomacia, imperio_jugador):
    origen = elegir_provincia_jugador(
        mapa, imperio_jugador, "MOVER TROPAS - Provincia de origen")
    if origen is None:
        return
    destino = elegir_provincia_mapa(mapa, "MOVER TROPAS - Provincia de destino")
    if destino is None:
        return
    cant = leer_numero(
        f"MOVER de P{origen.id:02d} a P{destino.id:02d}\n"
        f"  Tropas disponibles en origen: {origen.u_prov}\n"
        f"\n  Cantidad a mover:")
    if cant is None or cant <= 0:
        mostrar_mensaje("Cantidad invalida", "error")
        return
    res = ordenar_movimiento(mapa, diplomacia, imperio_jugador, origen, destino, cant)
    if res["ok"]:
        mostrar_mensaje(f"{res['mensaje']} (-{C_PA_MOVIMIENTO:.1f} PA)", "exito")
    else:
        mostrar_mensaje(f"No se pudo ordenar el movimiento: {res['motivo']}", "error")


def accion_fortificar(mapa, imperio_jugador):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "FORTIFICAR - Seleccionar provincia")
    if prov is None:
        return
    res = fortificar_provincia(imperio_jugador, prov)
    if res["ok"]:
        mostrar_mensaje(
            f"Provincia P{prov.id:02d} fortificada\n"
            f"  -{res['costo_oro']:.1f} oro, -{res['costo_pa']:.1f} PA",
            "exito")
    else:
        mostrar_mensaje(f"No se pudo fortificar: {res['motivo']}", "error")


def accion_saquear(mapa, imperio_jugador, lef, turno):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "SAQUEAR - Seleccionar provincia")
    if prov is None:
        return
    res = saquear(imperio_jugador, prov)
    if res["ok"]:
        imperio_jugador.puntos_accion_actual -= C_PA_SAQUEO
        lef.programar_evento("SAQUEO", turno + 1,
                             {"provincia": prov, "imperio": imperio_jugador})
        mostrar_mensaje(
            f"Saqueo (E10) programado para P{prov.id:02d} en turno {turno + 1}\n"
            f"  -{C_PA_SAQUEO:.0f} PA, +oro, -30 fel, -20% pob\n"
            f"  inactiva {DURACION_SAQUEO} turnos",
            "exito")
    else:
        mostrar_mensaje(f"No se puede saquear: {res['motivo']}", "error")


def accion_guerra(imperios, imperio_jugador, diplomacia):
    rival = otro_imperio(imperios, imperio_jugador)
    res = diplomacia.declarar_guerra(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Guerra declarada contra {rival.nombre} (E7)", "exito")
    else:
        mostrar_mensaje(f"No se pudo declarar guerra: {res['motivo']}", "error")


def accion_paz(imperios, imperio_jugador, diplomacia):
    rival = otro_imperio(imperios, imperio_jugador)
    res = diplomacia.proponer_paz(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"{res['motivo']} ({res['estado']})", "exito")
    else:
        mostrar_mensaje(f"No se pudo proponer paz: {res['motivo']}", "error")


def accion_alianza(imperios, imperio_jugador, diplomacia):
    rival = otro_imperio(imperios, imperio_jugador)
    res = diplomacia.formar_alianza(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Alianza firmada con {rival.nombre}", "exito")
    else:
        mostrar_mensaje(f"No se pudo formar alianza: {res['motivo']}", "error")


def accion_romper(imperios, imperio_jugador, diplomacia):
    rival = otro_imperio(imperios, imperio_jugador)
    res = diplomacia.romper_alianza(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Alianza rota con {rival.nombre}", "exito")
    else:
        mostrar_mensaje(f"No se pudo romper la alianza: {res['motivo']}", "error")


def accion_proteger(imperios, imperio_jugador, diplomacia):
    rival = otro_imperio(imperios, imperio_jugador)
    res = diplomacia.proteger(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(
            f"{rival.nombre} ahora es vasallo de {imperio_jugador.nombre} (paga tributo)",
            "exito")
    else:
        mostrar_mensaje(f"No se pudo establecer la proteccion: {res['motivo']}", "error")


def accion_relaciones(imperios, diplomacia):
    limpiar()
    print()
    print(f"  {'=' * ANCHO}")
    print("  RELACIONES DIPLOMATICAS")
    print(f"  {'=' * ANCHO}")
    mostrar_relaciones(diplomacia, imperios)
    print(f"  {'=' * ANCHO}")
    input("\n  Presione ENTER para volver...")


def accion_ver_mapa(mapa):
    limpiar()
    mostrar_mapa(mapa)
    input("  Presione ENTER para volver...")


def accion_estado(mapa):
    limpiar()
    print()
    print(f"  {'=' * ANCHO}")
    print("  ESTADO DE PROVINCIAS")
    print(f"  {'=' * ANCHO}")
    for fila in mapa:
        for p in fila:
            duenio = p.dueño.nombre if p.dueño else "libre"
            print(
                f"  P{p.id:02d} ({duenio}): "
                f"pob={p.poblacion:,.0f} "
                f"fel={p.felicidad:.1f} "
                f"reb={p.rebelion} "
                f"bloq={p.bloqueada_baja_felicidad} "
                f"sold={p.u_prov} "
                f"torre={'SI' if p.torre_vigilancia else 'no'} "
                f"fort={'SI' if p.fortificacion else 'no'}")
    print(f"  {'=' * ANCHO}")
    input("\n  Presione ENTER para volver...")


def accion_tropas_debug(mapa, imperios):
    prov = elegir_provincia_mapa(
        mapa, "DEPURACION: Fijar tropas - Seleccionar provincia")
    if prov is None:
        return
    cant = leer_numero(
        f"Fijar tropas en P{prov.id:02d}\n"
        f"  Tropas actuales: {prov.u_prov}\n"
        f"\n  Nueva cantidad:")
    if cant is None or cant < 0:
        mostrar_mensaje("Cantidad invalida", "error")
        return
    prov.u_prov = max(0, cant)
    recalcular_unidades_totales(imperios)
    mostrar_mensaje(
        f"Guarnicion de P{prov.id:02d} fijada a {prov.u_prov} (depuracion)",
        "exito")


def accion_fel_debug(mapa):
    prov = elegir_provincia_mapa(
        mapa, "DEPURACION: Fijar felicidad - Seleccionar provincia")
    if prov is None:
        return
    val = leer_numero(
        f"Fijar felicidad en P{prov.id:02d}\n"
        f"  Felicidad actual: {prov.felicidad:.1f}\n"
        f"\n  Nuevo valor (0-100):")
    if val is None:
        mostrar_mensaje("Valor invalido", "error")
        return
    prov.felicidad = min(100.0, max(0.0, float(val)))
    mostrar_mensaje(
        f"Felicidad de P{prov.id:02d} forzada a {prov.felicidad:.1f}",
        "exito")



def main():
    # variables de control de la partida
    turno = 1
    limite_turnos = 20
    partida_terminada = False

    # variables de Tablero
    filas = 4
    columnas = 4
    mapa = crear_mapa(filas, columnas)

    # Creacion de los imperios de prueba (Parte 1)
    imperio_jugador = Imperio("Jugador", tesoro_inicial=1000.0)
    imperio_ia = Imperio("IA", tesoro_inicial=1000.0)
    imperios = [imperio_jugador, imperio_ia]

    # Diplomacia: tabla de relaciones y vasallajes
    diplomacia = Diplomacia()

    # LEF: Lista de Eventos Futuros (Parte 7)
    lef = LEF()

    # IA de la CPU
    ia = IA_CPU()

    # Reparto inicial de provincias entre los dos imperios de prueba (incluye ubicacion del rey)
    asignar_provincias_iniciales(mapa, imperios)

    # Pantalla de inicio
    limpiar()
    borde = "=" * ANCHO
    print()
    print(f"  {borde}")
    print(f"  {'AGE OF CONQUEST IV':^{ANCHO - 4}}")
    print(f"  {borde}")
    print("  INICIO DE LA PARTIDA")
    print(f"  {borde}")
    mostrar_mapa_por_dueño(mapa)
    mostrar_estado_imperios(imperios)
    input("  Presione ENTER para comenzar...")

    # Bucle principal de turnos
    while not partida_terminada:
        pendientes = len(imperio_jugador.ordenes_movimiento)
        subtitulo = (
            f"Turno {turno}/{limite_turnos}  |  "
            f"Oro: {imperio_jugador.tesoro:.1f}  |  "
            f"PA: {imperio_jugador.puntos_accion_actual}/{imperio_jugador.puntos_accion_max}"
            f"  |  Mov pend: {pendientes}"
        )

        opciones = [
            "Reclutar soldados",           # 0
            "Construir torre",              # 1
            "Mover tropas",                 # 2
            "Fortificar provincia",         # 3
            "Saquear provincia",            # 4
            "Declarar guerra",              # 5
            "Proponer paz",                 # 6
            "Formar alianza",               # 7
            "Romper alianza",              # 8
            "Proteger (vasallaje)",         # 9
            "Ver relaciones",               # 10
            "Ver mapa",                     # 11
            "Ver estado detallado",         # 12
            "Avanzar turno",                # 13
            "[Dep] Fijar tropas",           # 14
            "[Dep] Fijar felicidad",        # 15
            "Salir",                        # 16
        ]

        idx = elegir(opciones, f"TURNO {turno}", subtitulo,
                      mapa_lineas(mapa, imperio_jugador))

        # ESC o "Salir" -> confirmar
        if idx == -1 or idx == 16:
            conf = elegir(["Si, salir", "No, volver"],
                          "Seguro que desea salir del juego?")
            if conf == 0:
                break
            continue

        # Despacho de acciones
        match idx:
            case 0:
                accion_reclutar(mapa, imperio_jugador)
            case 1:
                accion_torre(mapa, imperio_jugador)
            case 2:
                accion_mover(mapa, diplomacia, imperio_jugador)
            case 3:
                accion_fortificar(mapa, imperio_jugador)
            case 4:
                accion_saquear(mapa, imperio_jugador, lef, turno)
            case 5:
                accion_guerra(imperios, imperio_jugador, diplomacia)
            case 6:
                accion_paz(imperios, imperio_jugador, diplomacia)
            case 7:
                accion_alianza(imperios, imperio_jugador, diplomacia)
            case 8:
                accion_romper(imperios, imperio_jugador, diplomacia)
            case 9:
                accion_proteger(imperios, imperio_jugador, diplomacia)
            case 10:
                accion_relaciones(imperios, diplomacia)
            case 11:
                accion_ver_mapa(mapa)
            case 12:
                accion_estado(mapa)
            case 13:
                ia.planificar_turno(imperio_ia, mapa, diplomacia, imperios)
                if ia.acciones:
                    mostrar_mensaje(
                        f"IA ejecuto: {', '.join(ia.acciones)}", "info")
                cierre_de_turno(turno, imperios, mapa, diplomacia, lef)
                turno += 1
            case 14:
                accion_tropas_debug(mapa, imperios)
            case 15:
                accion_fel_debug(mapa)
            case _:
                pass

    limpiar()
    print("\n  === FIN DE LA PARTIDA ===\n")

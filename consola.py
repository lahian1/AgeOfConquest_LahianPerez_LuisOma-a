# consola.py - Interfaz de consola con menu interactivo por flechas
# Mantiene toda la logica original; solo cambia la presentacion y la interaccion.
# Navegacion: flechas arriba/abajo, Enter para seleccionar, ESC para volver/salir.

import os
import random
import msvcrt

from modelos import Imperio, Diplomacia, buscar_rivales
from mapa import (
    crear_mapa, asignar_provincias_iniciales, buscar_provincia,
    mostrar_mapa, mostrar_mapa_por_dueño, mostrar_estado_imperios,
    _obtener_adyacentes,
)
from economia import calcular_actividad_comercial, modificar_impuestos_anuales, modificar_impuestos_comercio, obtener_mes
from poblacion import poblacion_total
from unidades import reclutar_soldados, construir_torre_vigilancia, recalcular_unidades_totales
from diplomacia import mostrar_relaciones
from constantes import C_PA_SAQUEO, DURACION_SAQUEO, C_ORO_FERTILIDAD, C_PA_FERTILIDAD, COOLDOWN_FERTILIDAD, C_ORO_REPARTIR, C_PA_REPARTIR
from combat import ordenar_movimiento, fortificar_provincia, saquear, C_PA_MOVIMIENTO
from lef import LEF
from turno import cierre_de_turno
from ia import IA_CPU


ANCHO = 58


def verificar_fin_partida(imperios):
    """Verifica si la partida termino por captura del rey o eliminacion total.
    Devuelve el ganador o None si la partida continua."""
    eliminados = [i for i in imperios if i.rey_capturado or len(i.provincias) == 0]
    vivos = [i for i in imperios if not i.rey_capturado and len(i.provincias) > 0]
    if not vivos:
        return None
    if len(vivos) == 1 and len(imperios) > 1:
        return vivos[0]
    return None


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
    """Muestra un mensaje y pausa hasta que el usuario presione ENTER."""
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
    input("  Presione ENTER para continuar...")


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


def mapa_lineas(mapa, imperio_jugador, imperios):
    """Genera lineas compactas del mapa por duenio para el menu principal."""
    lineas = ["  Mapa por duenio:"]
    abrevs = {}
    for i, imp in enumerate(imperios):
        abrevs[id(imp)] = imp.nombre[:1].upper() if imp is not imperio_jugador else "J"
    for fila in mapa:
        partes = []
        for prov in fila:
            if prov.dueño:
                abrev = abrevs.get(id(prov.dueño), "?")
                partes.append(f"[{prov.id:02d}{abrev}]")
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


def elegir_rival(imperios, imperio_jugador, titulo):
    """Muestra la lista de rivales y deja elegir uno con flechas.
    Retorna el imperio rival o None si ESC."""
    rivales = buscar_rivales(imperios, imperio_jugador)
    vivos = [r for r in rivales if not r.rey_capturado and len(r.provincias) > 0]
    if not vivos:
        mostrar_mensaje("No hay rivales disponibles", "error")
        return None
    opciones = [f"{r.nombre} (Oro:{r.tesoro:.0f} Prov:{len(r.provincias)})" for r in vivos]
    idx = elegir(opciones, titulo)
    return vivos[idx] if idx >= 0 else None

def elegir_provincia_mapa_adyacente(mapa, titulo, adyacentes):
    """Lista todas las provincias adyacentes a una dada para seleccionar con flechas.
    Retorna la provincia elegida o None si ESC."""
    provs = [p for fila in mapa for p in fila if (p.posicion in adyacentes)]   
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
    adyacentes = _obtener_adyacentes(mapa, *origen.posicion)
    if not adyacentes:
        mostrar_mensaje("No hay provincias adyacentes para mover tropas", "error")
        return
    destino = elegir_provincia_mapa_adyacente(mapa, "MOVER TROPAS - Provincia de destino", adyacentes)
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


def accion_fertilidad(mapa, imperio_jugador):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "DECRETO FERTILIDAD - Seleccionar provincia")
    if prov is None:
        return
    if prov.cooldown_fertilidad > 0:
        mostrar_mensaje(
            f"P{prov.id:02d} en cooldown de fertilidad ({prov.cooldown_fertilidad} turnos restantes)",
            "error")
        return
    if imperio_jugador.tesoro < C_ORO_FERTILIDAD:
        mostrar_mensaje(f"Oro insuficiente (necesitas {C_ORO_FERTILIDAD:.0f})", "error")
        return
    if imperio_jugador.puntos_accion_actual < C_PA_FERTILIDAD:
        mostrar_mensaje(f"PA insuficiente (necesitas {C_PA_FERTILIDAD:.1f})", "error")
        return
    imperio_jugador.tesoro -= C_ORO_FERTILIDAD
    imperio_jugador.puntos_accion_actual -= C_PA_FERTILIDAD
    prov.decreto_f = True
    prov.cooldown_fertilidad = COOLDOWN_FERTILIDAD
    mostrar_mensaje(
        f"Decreto FERTILIDAD activado en P{prov.id:02d}\n"
        f"  -{C_ORO_FERTILIDAD:.0f} oro, -{C_PA_FERTILIDAD:.1f} PA\n"
        f"  +{15:.0f} felicidad este turno\n"
        f"  cooldown {COOLDOWN_FERTILIDAD} turnos",
        "exito")


def accion_repartir(mapa, imperio_jugador):
    prov = elegir_provincia_jugador(
        mapa, imperio_jugador, "DECRETO REPARTIR ORO - Seleccionar provincia")
    if prov is None:
        return
    if imperio_jugador.tesoro < C_ORO_REPARTIR:
        mostrar_mensaje(f"Oro insuficiente (necesitas {C_ORO_REPARTIR:.0f})", "error")
        return
    if imperio_jugador.puntos_accion_actual < C_PA_REPARTIR:
        mostrar_mensaje(f"PA insuficiente (necesitas {C_PA_REPARTIR:.1f})", "error")
        return
    imperio_jugador.tesoro -= C_ORO_REPARTIR
    imperio_jugador.puntos_accion_actual -= C_PA_REPARTIR
    prov.decreto_d = True
    mostrar_mensaje(
        f"Decreto REPARTIR ORO activado en P{prov.id:02d}\n"
        f"  -{C_ORO_REPARTIR:.0f} oro, -{C_PA_REPARTIR:.1f} PA\n"
        f"  +1% crecimiento poblacional este turno",
        "exito")


def accion_guerra(imperios, imperio_jugador, diplomacia):
    rival = elegir_rival(imperios, imperio_jugador, "Elegir imperio para DECLARAR GUERRA")
    if rival is None:
        return
    res = diplomacia.declarar_guerra(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Guerra declarada contra {rival.nombre} (E7)", "exito")
    else:
        mostrar_mensaje(f"No se pudo declarar guerra: {res['motivo']}", "error")


def accion_paz(imperios, imperio_jugador, diplomacia):
    rival = elegir_rival(imperios, imperio_jugador, "Elegir imperio para PROPONER PAZ")
    if rival is None:
        return
    res = diplomacia.proponer_paz(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"{res['motivo']} ({res['estado']})", "exito")
    else:
        mostrar_mensaje(f"No se pudo proponer paz: {res['motivo']}", "error")


def accion_alianza(imperios, imperio_jugador, diplomacia):
    rival = elegir_rival(imperios, imperio_jugador, "Elegir imperio para FORMAR ALIANZA")
    if rival is None:
        return
    res = diplomacia.formar_alianza(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Alianza firmada con {rival.nombre}", "exito")
    else:
        mostrar_mensaje(f"No se pudo formar alianza: {res['motivo']}", "error")


def accion_romper(imperios, imperio_jugador, diplomacia):
    rival = elegir_rival(imperios, imperio_jugador, "Elegir imperio para ROMPER ALIANZA")
    if rival is None:
        return
    res = diplomacia.romper_alianza(imperio_jugador, rival)
    if res["ok"]:
        mostrar_mensaje(f"Alianza rota con {rival.nombre}", "exito")
    else:
        mostrar_mensaje(f"No se pudo romper la alianza: {res['motivo']}", "error")


def accion_proteger(imperios, imperio_jugador, diplomacia):
    rival = elegir_rival(imperios, imperio_jugador, "Elegir imperio para VASALLAJE")
    if rival is None:
        return
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

def accion_modficar_impuesto(imperio_jugador, turno):
    tazas=[0, 5, 10, 15, 20]
    limpiar()
    print()
    print(f"  {'=' * ANCHO}")
    print("  MODIFICAR TASAS DE IMPUESTO")
    print(f"  {'=' * ANCHO}")
    print(f"  Tasa de impuesto directo actual: {imperio_jugador.tasa_impuesto:.1f}%")
    print(f"  Tasa de impuesto comercial actual: {imperio_jugador.tasa_impuesto_comercio:.1f}%")
    impuesto_comercio= elegir(["Modificar impuesto directo", "Modificar impuesto comercial"], "Seleccione la tasa a modificar")
    if (impuesto_comercio==0):
        if obtener_mes(turno) != 12:
            mostrar_mensaje("Solo se puede modificar la tasa de impuesto directo en el mes 12", "error")
            return
        nueva_taza = elegir(tazas, "Seleccione la nueva tasa de impuesto anual (solo se puede modificar en el mes 12)")
        if nueva_taza == -1:
            mostrar_mensaje("Opcion invalida", "error")
            return
        modificar_impuestos_anuales(imperio_jugador, tazas[nueva_taza])
        mostrar_mensaje(f"Tasa de impuesto directo modificada a {imperio_jugador.tasa_impuesto:.1f}%", "exito")
    elif impuesto_comercio == 1:
        nueva_taza = elegir(tazas, "Seleccione la nueva tasa de impuesto comercial")
        if nueva_taza == -1:
            mostrar_mensaje("Opcion invalida", "error")
            return
        modificar_impuestos_comercio(imperio_jugador, tazas[nueva_taza])
        mostrar_mensaje(f"Tasa de impuesto comercial modificada a {imperio_jugador.tasa_impuesto_comercio:.1f}%", "exito")
    else:
        mostrar_mensaje("Opcion invalida", "error")
        return  



def main():
    turno = 1
    limite_turnos = 50
    partida_terminada = False

    filas = 8
    columnas = 8
    mapa = crear_mapa(filas, columnas)

    imperio_jugador = Imperio("Jugador", tesoro_inicial=1000.0)
    imperio_norte   = Imperio("Norte",   tesoro_inicial=1000.0)
    imperio_sur     = Imperio("Sur",     tesoro_inicial=1000.0)
    imperio_este    = Imperio("Este",    tesoro_inicial=1000.0)
    imperios = [imperio_jugador, imperio_norte, imperio_sur, imperio_este]

    diplomacia = Diplomacia()
    lef = LEF()

    ias = {
        id(imperio_norte): IA_CPU(),
        id(imperio_sur):   IA_CPU(),
        id(imperio_este):  IA_CPU(),
    }

    asignar_provincias_iniciales(mapa, imperios)

    limpiar()
    borde = "=" * ANCHO
    print()
    print(f"  {borde}")
    print(f"  {'AGE OF CONQUEST IV':^{ANCHO - 4}}")
    print(f"  {borde}")
    print("  INICIO DE LA PARTIDA")
    print(f"  {borde}")
    print(f"  Mapa: {filas}x{columnas} = {filas * columnas} provincias")
    print(f"  Jugadores: 1 Humano + 3 IAs")
    mostrar_mapa_por_dueño(mapa)
    mostrar_estado_imperios(imperios)
    input("  Presione ENTER para comenzar...")

    while not partida_terminada:
        vivos = [i for i in imperios if not i.rey_capturado and len(i.provincias) > 0]
        if not vivos:
            break
        if len(vivos) == 1:
            ganador = vivos[0]
            limpiar()
            print("\n  ═══════════════════════════════════════")
            if ganador is imperio_jugador:
                print(f"  VICTORIA: {ganador.nombre} ha ganado la partida!")
            else:
                print(f"  DERROTA: {ganador.nombre} ha conquistado el mapa")
            print("  ═══════════════════════════════════════\n")
            mostrar_mapa_por_dueño(mapa)
            input("  Presione ENTER para finalizar...")
            break

        turno_humano = True
        while turno_humano:
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
                "Decreto: Fertilidad",          # 5
                "Decreto: Repartir oro",        # 6
                "Declarar guerra",              # 7
                "Proponer paz",                 # 8
                "Formar alianza",               # 9
                "Romper alianza",              # 10
                "Proteger (vasallaje)",         # 11
                "Ver relaciones",               # 12
                "Ver mapa",                     # 13
                "Ver estado detallado",         # 14
                "Terminar turno",               # 15
                "[Dep] Fijar tropas",           # 16
                "[Dep] Fijar felicidad",        # 17
                "Modificar impuesto",            # 18
                "Salir",                         # 19
            ]

            idx = elegir(opciones, f"TURNO {turno} - {imperio_jugador.nombre}", subtitulo,
                          mapa_lineas(mapa, imperio_jugador, imperios))

            if idx == -1 or idx == 19:
                conf = elegir(["Si, salir", "No, volver"],
                              "Seguro que desea salir del juego?")
                if conf == 0:
                    partida_terminada = True
                turno_humano = False
                continue

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
                    accion_fertilidad(mapa, imperio_jugador)
                case 6:
                    accion_repartir(mapa, imperio_jugador)
                case 7:
                    accion_guerra(imperios, imperio_jugador, diplomacia)
                case 8:
                    accion_paz(imperios, imperio_jugador, diplomacia)
                case 9:
                    accion_alianza(imperios, imperio_jugador, diplomacia)
                case 10:
                    accion_romper(imperios, imperio_jugador, diplomacia)
                case 11:
                    accion_proteger(imperios, imperio_jugador, diplomacia)
                case 12:
                    accion_relaciones(imperios, diplomacia)
                case 13:
                    accion_ver_mapa(mapa)
                case 14:
                    accion_estado(mapa)
                case 15:
                    turno_humano = False
                case 16:
                    accion_tropas_debug(mapa, imperios)
                case 17:
                    accion_fel_debug(mapa)
                case 18:
                    accion_modficar_impuesto(imperio_jugador, turno)
                case _:
                    pass

        if partida_terminada:
            break

        # 2. LUEGO todas las IAs planifican sus movimientos (sin mostrar aun)
        for imperio_actual in imperios:
            if imperio_actual is imperio_jugador:
                continue
            if imperio_actual.rey_capturado or len(imperio_actual.provincias) == 0:
                continue
            ia = ias.get(id(imperio_actual))
            if ia:
                ia.planificar_turno(imperio_actual, mapa, diplomacia, imperios)

        # 3. DESPUES cierre (el jugador ve su informe primero)
        orden_resolucion = [i for i in imperios if not i.rey_capturado and len(i.provincias) > 0]
        random.shuffle(orden_resolucion)
        cierre_de_turno(turno, imperios, mapa, diplomacia, lef, orden_resolucion)
        input("  Presione ENTER para continuar...")

        # 4. FINALMENTE mostrar que hicieron las IAs
        for imperio_actual in imperios:
            if imperio_actual is imperio_jugador:
                continue
            if imperio_actual.rey_capturado or len(imperio_actual.provincias) == 0:
                continue
            ia = ias.get(id(imperio_actual))
            if ia and ia.acciones:
                limpiar()
                borde = "=" * ANCHO
                print(f"\n  {borde}")
                print(f"  TURNO {turno} - IA: {imperio_actual.nombre}")
                print(f"  {borde}")
                for accion in ia.acciones:
                    print(f"    - {accion}")
                print(f"  {borde}")
                input("  Presione ENTER para continuar...")

        # 3. DESPUES cierre con orden aleatorio de resolucion
        orden_resolucion = [i for i in imperios if not i.rey_capturado and len(i.provincias) > 0]
        random.shuffle(orden_resolucion)
        cierre_de_turno(turno, imperios, mapa, diplomacia, lef, orden_resolucion)
        input("  Presione ENTER para continuar...")
        turno += 1
        if turno > limite_turnos:
            vivos = [i for i in imperios if not i.rey_capturado and len(i.provincias) > 0]
            ganador = max(vivos, key=lambda i: len(i.provincias)) if vivos else None
            limpiar()
            print("\n  ═══════════════════════════════════════")
            print(f"  SE ACABO EL TIEMPO!")
            if ganador:
                print(f"  GANADOR: {ganador.nombre} ({len(ganador.provincias)} provincias)")
            print("  ═══════════════════════════════════════\n")
            mostrar_mapa_por_dueño(mapa)
            input("  Presione ENTER para finalizar...")
            break

    limpiar()
    print("\n  === FIN DE LA PARTIDA ===\n")

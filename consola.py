# Interfaz de consola: bucle principal de turnos, lectura de comandos y
# pantalla de estado. Importa todos los subsistemas y delega el cierre
# a turno.cierre_de_turno.

from modelos import Imperio, Diplomacia, otro_imperio
from mapa import (
    crear_mapa, asignar_provincias_iniciales, buscar_provincia,
    mostrar_mapa, mostrar_mapa_por_dueño, mostrar_estado_imperios,
)
from economia import calcular_actividad_comercial
from poblacion import poblacion_total
from unidades import reclutar_soldados, construir_torre_vigilancia, recalcular_unidades_totales
from diplomacia import mostrar_relaciones
from combat import ordenar_movimiento, fortificar_provincia, C_PA_MOVIMIENTO
from turno import cierre_de_turno


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

    # Reparto inicial de provincias entre los dos imperios de prueba (incluye ubicacion del rey)
    asignar_provincias_iniciales(mapa, imperios)

    print("*************************************************")
    print("----INICIO DE LA PARTIDA----")
    print("*************************************************")

    mostrar_mapa_por_dueño(mapa)
    mostrar_estado_imperios(imperios)

    # Bucle principal de turnos
    while not partida_terminada:
        pendientes = len(imperio_jugador.ordenes_movimiento)
        print(f"Partida en turno {turno} | {imperio_jugador.nombre}: "
              f"tesoro={imperio_jugador.tesoro:.1f} oro, "
              f"PA={imperio_jugador.puntos_accion_actual}/{imperio_jugador.puntos_accion_max} | "
              f"movimientos pendientes={pendientes} | "
              f"Haga sus movimientos")
        mostrar_mapa(mapa)

        respuesta = input("ENTER avanzar | 'salir' | 'reclutar <id> <cant>' | 'torre <id>' | "
                          "'mover <origen> <destino> <cant>' | 'fortificar <id>' | "
                          "'guerra' | 'paz' | 'alianza' | 'romper' | 'proteger' | 'relaciones' | "
                          "'fel <id> <0-100>' | 'tropas <id> <cant>' | 'estado': ")
        respuesta = respuesta.strip().lower()

        if respuesta == "salir":
            print("Terminando juego...")
            break
        elif respuesta == "guerra":
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.declarar_guerra(imperio_jugador, rival)
            if res["ok"]:
                print(f"  Guerra declarada contra {rival.nombre} (E7)")
            else:
                print(f"  No se pudo declarar guerra: {res['motivo']}")
            continue
        elif respuesta == "paz":
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.proponer_paz(imperio_jugador, rival)
            if res["ok"]:
                print(f"  {res['motivo']} ({res['estado']})")
            else:
                print(f"  No se pudo proponer paz: {res['motivo']}")
            continue
        elif respuesta == "alianza":
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.formar_alianza(imperio_jugador, rival)
            if res["ok"]:
                print(f"  Alianza firmada con {rival.nombre}")
            else:
                print(f"  No se pudo formar alianza: {res['motivo']}")
            continue
        elif respuesta == "romper":
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.romper_alianza(imperio_jugador, rival)
            if res["ok"]:
                print(f"  Alianza rota con {rival.nombre}")
            else:
                print(f"  No se pudo romper la alianza: {res['motivo']}")
            continue
        elif respuesta == "proteger":
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.proteger(imperio_jugador, rival)
            if res["ok"]:
                print(f"  {rival.nombre} ahora es vasallo de {imperio_jugador.nombre} (paga tributo)")
            else:
                print(f"  No se pudo establecer la proteccion: {res['motivo']}")
            continue
        elif respuesta == "relaciones":
            mostrar_relaciones(diplomacia, imperios)
            continue
        elif respuesta.startswith("reclutar "):
            partes = respuesta.split()
            try:
                id_prov = int(partes[1])
                cantidad = int(partes[2])
                provincia = buscar_provincia(mapa, id_prov)
                if provincia is None:
                    print(f"  No existe la provincia {id_prov:02d}")
                else:
                    res = reclutar_soldados(imperio_jugador, provincia, cantidad)
                    if res["ok"]:
                        print(f"  Reclutados {res['cantidad']} soldados en P{id_prov:02d} "
                              f"(-{res['costo_oro']:.1f} oro, -{res['costo_poblacion']:,} poblacion, -1 PA)")
                    else:
                        print(f"  No se pudo reclutar: {res['motivo']}")
            except (ValueError, IndexError):
                print("  Uso: reclutar <id_provincia> <cantidad>")
            continue
        elif respuesta.startswith("torre "):
            partes = respuesta.split()
            try:
                id_prov = int(partes[1])
                provincia = buscar_provincia(mapa, id_prov)
                if provincia is None:
                    print(f"  No existe la provincia {id_prov:02d}")
                else:
                    res = construir_torre_vigilancia(imperio_jugador, provincia)
                    if res["ok"]:
                        print(f"  Torre de Vigilancia construida en P{id_prov:02d} "
                              f"(-{res['costo_oro']:.1f} oro, -{res['costo_pa']:.1f} PA)")
                    else:
                        print(f"  No se pudo construir la torre: {res['motivo']}")
            except (ValueError, IndexError):
                print("  Uso: torre <id_provincia>")
            continue
        elif respuesta.startswith("mover "):
            partes = respuesta.split()
            try:
                id_origen = int(partes[1])
                id_destino = int(partes[2])
                cantidad = int(partes[3])
                origen = buscar_provincia(mapa, id_origen)
                destino = buscar_provincia(mapa, id_destino)
                if origen is None or destino is None:
                    print("  No existe la provincia indicada")
                else:
                    res = ordenar_movimiento(mapa, diplomacia, imperio_jugador, origen, destino, cantidad)
                    if not res["ok"]:
                        print(f"  No se pudo ordenar el movimiento: {res['motivo']}")
                    else:
                        print(f"  {res['mensaje']} (-{C_PA_MOVIMIENTO:.1f} PA)")
            except (ValueError, IndexError):
                print("  Uso: mover <origen> <destino> <cantidad>")
            continue
        elif respuesta.startswith("fortificar "):
            partes = respuesta.split()
            try:
                id_prov = int(partes[1])
                provincia = buscar_provincia(mapa, id_prov)
                if provincia is None:
                    print(f"  No existe la provincia {id_prov:02d}")
                else:
                    res = fortificar_provincia(imperio_jugador, provincia)
                    if res["ok"]:
                        print(f"  Provincia P{id_prov:02d} fortificada "
                              f"(-{res['costo_oro']:.1f} oro, -{res['costo_pa']:.1f} PA)")
                    else:
                        print(f"  No se pudo fortificar: {res['motivo']}")
            except (ValueError, IndexError):
                print("  Uso: fortificar <id_provincia>")
            continue
        elif respuesta.startswith("tropas "):
            # Comando de depuracion de la Parte 6: fija la guarnicion de una provincia
            # para poder probar combates sin depender del reclutamiento normal.
            partes = respuesta.split()
            try:
                id_prov = int(partes[1])
                cantidad = int(partes[2])
                provincia = buscar_provincia(mapa, id_prov)
                if provincia is None:
                    print(f"  No existe la provincia {id_prov:02d}")
                else:
                    provincia.u_prov = max(0, cantidad)
                    recalcular_unidades_totales(imperios)
                    print(f"  Guarnicion de P{id_prov:02d} fijada a {provincia.u_prov} soldados (depuracion)")
            except (ValueError, IndexError):
                print("  Uso: tropas <id_provincia> <cantidad>")
            continue
        elif respuesta.startswith("fel "):
            # Comando para forzar la felicidad de una provincia y probar que funcione.
            partes = respuesta.split()
            try:
                id_prov = int(partes[1])
                valor = float(partes[2])
                encontrada = False
                for fila in mapa:
                    for provincia in fila:
                        if provincia.id == id_prov:
                            provincia.felicidad = min(100.0, max(0.0, valor))
                            print(f"  Felicidad de la provincia {id_prov:02d} forzada a {provincia.felicidad:.1f}")
                            encontrada = True
                if not encontrada:
                    print(f"  No existe la provincia {id_prov:02d}")
            except (ValueError, IndexError):
                print("  Uso: fel <id_provincia> <felicidad_0_100>")
            continue
        elif respuesta == "estado":
            for fila in mapa:
                for provincia in fila:
                    duenio = provincia.dueño.nombre if provincia.dueño else "libre"
                    print(f"  P{provincia.id:02d} ({duenio}): pob={provincia.poblacion:,.0f} "
                          f"fel={provincia.felicidad:.1f} reb={provincia.rebelion} "
                          f"bloq={provincia.bloqueada_baja_felicidad} "
                          f"soldados={provincia.u_prov} "
                          f"torre={'SI' if provincia.torre_vigilancia else 'no'} "
                          f"fort={'SI' if provincia.fortificacion else 'no'}")
            continue

        # Si el usuario solo presiona ENTER (respuesta vacia), cerrar el turno
        cierre_de_turno(turno, imperios, mapa, diplomacia)
        turno += 1

    print("\n=== FIN DE LA PARTIDA ===")

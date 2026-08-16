# Resolucion del cierre de turno (Cierre_De_Turno del pseudocodigo).
# Integra la LEF (Parte 7) para eventos diferidos.


from economia import (
    calcular_actividad_comercial, calcular_tributos,
    procesar_cierre_economico, mostrar_resumen_economico,
)
from poblacion import (
    procesar_crecimiento_poblacional, poblacion_total,
    procesar_cierre_felicidad, mostrar_resumen_felicidad,
)
from combat import resolver_ordenes_movimiento
from constantes import SAQUEO_BOTIN, SAQUEO_PENALIDAD_FELICIDAD, DURACION_SAQUEO


def ejecutar_eventos_lef(lef, turno, imperios, mapa):
    """Extrae y ejecuta todos los eventos de la LEF programados para el turno actual.
    Los eventos se ejecutan en orden de prioridad logica (combate < saqueo < produccion
    < economia < felicidad)."""
    if not lef.hay_eventos(turno):
        return

    eventos = lef.extraer_eventos(turno)
    print(f"--- Eventos LEF del turno {turno} ({len(eventos)} eventos) ---")
    for evento in eventos:
        tipo = evento["tipo"]
        datos = evento["datos"]

        if tipo == "SAQUEO":
            provincia = datos.get("provincia")
            imperio = datos.get("imperio")
            if provincia is None or imperio is None:
                print(f"  [!] Evento SAQUEO incompleto: datos faltantes")
                continue
            # Verificar que la provincia siga siendo del imperio
            if provincia.dueño is not imperio:
                print(f"  [!] Evento SAQUEO cancelado: P{provincia.id:02d} ya no pertenece a {imperio.nombre}")
                continue
            # Ejecutar efectos del saqueo (PA ya fue cobrado al ordenar)
            botin = SAQUEO_BOTIN * provincia.ac
            imperio.tesoro += botin
            provincia.poblacion = int(provincia.poblacion * 0.80)
            provincia.felicidad = max(0.0, provincia.felicidad - SAQUEO_PENALIDAD_FELICIDAD)
            provincia.turnos_saqueado = DURACION_SAQUEO
            print(f"  Saqueo (E10): +{botin:.1f} oro de botin, -30 felicidad, -20% poblacion "
                  f"en P{provincia.id:02d} (inactiva {DURACION_SAQUEO} turnos)")
        else:
            print(f"  [!] Evento desconocido: {tipo}")
    print("-------------------------------------------\n")


def cierre_de_turno(turno, imperios, mapa, diplomacia, lef):
    """Ejecuta los pasos del cierre del turno actual, incluyendo la LEF.
    Se llama al final de cada turno, despues de que el jugador (y la IA)
    terminaron de dar sus ordenes."""

    # 0. Eventos LEF diferidos: se ejecutan primero, antes de las fases normales.
    #    Combates y saqueos programados para este turno.
    ejecutar_eventos_lef(lef, turno, imperios, mapa)

    # 1. Movimiento y combate (paso 1 del pseudocodigo Cierre_De_Turno):
    #    se resuelven las ordenes de movimiento/ataque encoladas durante el turno.
    if any(imperio.ordenes_movimiento for imperio in imperios):
        print(f"--- Movimiento y combate del turno {turno} ---")
        resolver_ordenes_movimiento(mapa, diplomacia, imperios)
        print("-------------------------------------------\n")

    # 2. Crecimiento de poblacion usa la felicidad del
    #    turno anterior y actualiza la base imponible que vera la economia.
    print(f"\n--- Crecimiento de poblacion del turno {turno} ---")
    for imperio in imperios:
        antes = poblacion_total(imperio)
        procesar_crecimiento_poblacional(imperio)
        despues = poblacion_total(imperio)
        print(f"  [{imperio.nombre}] poblacion total: {antes:,.0f} -> {despues:,.0f}")
    print("-------------------------------------------\n")

    # 3. Cierre economico del turno que acaba de terminar.
    #    Antes de recaudar se calculan los tributos diplomaticos, que
    #    dependen de la actividad comercial ya actualizada de cada imperio.
    for imperio in imperios:
        for provincia in imperio.provincias:
            calcular_actividad_comercial(provincia)
    calcular_tributos(diplomacia, imperios, turno)

    print(f"--- Cierre economico del turno {turno} ---")
    for imperio in imperios:
        resumen = procesar_cierre_economico(imperio, turno)
        mostrar_resumen_economico(imperio, resumen)
    print("-------------------------------------------\n")

    # 4. Cierre de felicidad: usa los impuestos y
    #    saqueos YA aplicados en el cierre economico, evalua la rebelion (4.1)
    #    y actualiza el bloqueo de reclutamiento/construccion (4.2).
    print(f"--- Cierre de felicidad del turno {turno} ---")
    for imperio in imperios:
        resumenes = procesar_cierre_felicidad(imperio)
        mostrar_resumen_felicidad(imperio, resumenes)
    print("-------------------------------------------\n")

    # Avanzar turno: reponer PA de todos los imperios
    for imperio in imperios:
        imperio.resetear_puntos_accion()
    print("Avanzando al siguiente turno...")

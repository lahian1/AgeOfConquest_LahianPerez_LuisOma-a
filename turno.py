# Resolucion del cierre de turno (Cierre_De_Turno del pseudocodigo).
# El orden de ejecucion es fiel al Diagrama 1 del contexto.md:
#   1. Movimiento y combate (ordenes encoladas durante el turno)
#   2. Crecimiento de poblacion (actualiza base imponible para economia)
#   3. Cierre economico (actividad comercial, tributos, recaudacion, gastos, prestamo)
#   4. Cierre de felicidad (evalua rebelion y bloqueo de reclutamiento)

from economia import (
    calcular_actividad_comercial, calcular_tributos,
    procesar_cierre_economico, mostrar_resumen_economico,
)
from poblacion import (
    procesar_crecimiento_poblacional, poblacion_total,
    procesar_cierre_felicidad, mostrar_resumen_felicidad,
)
from combat import resolver_ordenes_movimiento


def cierre_de_turno(turno, imperios, mapa, diplomacia):
    """Ejecuta los 4 pasos del cierre del turno actual. Se llama al final de cada
    turno, despues de que el jugador (y la IA) terminaron de dar sus ordenes."""

    # 1. Movimiento y combate (paso 1 del pseudocodigo Cierre_De_Turno):
    #    se resuelven las ordenes de movimiento/ataque encoladas durante el turno.
    if any(imperio.ordenes_movimiento for imperio in imperios):
        print(f"--- Movimiento y combate del turno {turno} ---")
        resolver_ordenes_movimiento(mapa, diplomacia, imperios)
        print("-------------------------------------------\n")

    # 2. Crecimiento de poblacion usa la felicidad del
    #    turno anterior y actualiza la base imponible que verá la economia.
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

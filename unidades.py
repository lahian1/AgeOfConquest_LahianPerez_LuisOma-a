from constantes import C_ORO_TROPA, C_POB_TROPA, C_PA_TROPA, C_ORO_TORRE, C_PA_TORRE


def reclutar_soldados(imperio, provincia, cantidad):
    """Orden de reclutamiento (Evento E4): recluta `cantidad` soldados en la provincia.
    Validaciones y costos:
      - la provincia debe ser del imperio y no estar bloqueada por baja felicidad (4.2);
      - cantidad > 0;
      - PA disponibles >= C_PA_TROPA (1 PA fijo por orden, no por soldado);
      - tesoro >= cantidad * C_ORO_TROPA;
      - poblacion >= cantidad * C_POB_TROPA.
    Si todo pasa, se descuentan oro, poblacion y PA, y la cantidad se suma a la
    guarnicion de la provincia (u_prov) y al total del imperio (unidades_totales).
    Devuelve un diccionario con el resultado o el motivo de rechazo."""
    if provincia.dueño is not imperio:
        return {"ok": False, "motivo": "la provincia no pertenece a este imperio"}
    if provincia.turnos_saqueado > 0:
        return {"ok": False, "motivo": f"provincia saqueada e inactiva ({provincia.turnos_saqueado} turnos restantes)"}
    if provincia.bloqueada_baja_felicidad:
        return {"ok": False, "motivo": "provincia bloqueada por baja felicidad (Seccion 4.2)"}
    if cantidad <= 0:
        return {"ok": False, "motivo": "la cantidad debe ser positiva"}

    costo_oro = cantidad * C_ORO_TROPA
    costo_poblacion = cantidad * C_POB_TROPA

    if imperio.puntos_accion_actual < C_PA_TROPA:
        return {"ok": False, "motivo": "puntos de accion insuficientes"}
    if imperio.tesoro < costo_oro:
        return {"ok": False, "motivo": f"tesoro insuficiente (se necesitan {costo_oro:.1f} oro)"}
    if provincia.poblacion < costo_poblacion:
        return {"ok": False, "motivo": f"poblacion insuficiente (se necesitan {costo_poblacion:,} habitantes)"}

    imperio.tesoro -= costo_oro
    provincia.poblacion -= costo_poblacion
    imperio.puntos_accion_actual -= C_PA_TROPA
    provincia.u_prov += cantidad
    imperio.unidades_totales += cantidad

    return {"ok": True, "cantidad": cantidad, "costo_oro": costo_oro,
            "costo_poblacion": costo_poblacion}


def construir_torre_vigilancia(imperio, provincia):
    """Construye una Torre de Vigilancia en la provincia (se construye una sola vez).
    Validaciones: provincia propia, no bloqueada (4.2), sin torre previa,
    tesoro >= C_ORO_TORRE y PA >= C_PA_TORRE.
    Devuelve un diccionario con el resultado o el motivo de rechazo."""
    if provincia.dueño is not imperio:
        return {"ok": False, "motivo": "la provincia no pertenece a este imperio"}
    if provincia.turnos_saqueado > 0:
        return {"ok": False, "motivo": f"provincia saqueada e inactiva ({provincia.turnos_saqueado} turnos restantes)"}
    if provincia.bloqueada_baja_felicidad:
        return {"ok": False, "motivo": "provincia bloqueada por baja felicidad (Seccion 4.2)"}
    if provincia.torre_vigilancia:
        return {"ok": False, "motivo": "la provincia ya tiene torre de vigilancia"}
    if imperio.tesoro < C_ORO_TORRE:
        return {"ok": False, "motivo": f"tesoro insuficiente (se necesitan {C_ORO_TORRE:.1f} oro)"}
    if imperio.puntos_accion_actual < C_PA_TORRE:
        return {"ok": False, "motivo": "puntos de accion insuficientes"}

    imperio.tesoro -= C_ORO_TORRE
    imperio.puntos_accion_actual -= C_PA_TORRE
    provincia.torre_vigilancia = True

    return {"ok": True, "costo_oro": C_ORO_TORRE, "costo_pa": C_PA_TORRE}


def recalcular_unidades_totales(imperios):
    """Recomputa imperio.unidades_totales a partir de las guarniciones (u_prov).
    Se usa por el comando de depuracion `tropas` para mantener el contador al dia."""
    for imperio in imperios:
        imperio.unidades_totales = sum(p.u_prov for p in imperio.provincias)

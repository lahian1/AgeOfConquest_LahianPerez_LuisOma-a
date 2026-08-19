import random
from constantes import (
    P_MAX_POBLACION, TASA_CRECIMIENTO_POBLACION,
    DECRETO_D_BONO_CRECIMIENTO, DECRETO_F_BONO_FELICIDAD,
    FEL_UMBRAL, K3_RECUPERACION, K4_REBELION,
    PENALIDAD_IMPUESTOS_FELICIDAD,
    PORCENTAJE_PERDIDA_POBLACION_REBELION,
)


def actualizar_poblacion(provincia):
    """Crecimiento poblacional con modelo logistico modulado por la
    felicidad del turno anterior:
        Delta_P_i(t) = TASA_CRECIMIENTO * (Fel_i(t)/100) * P_i(t) * (1 - P_i(t)/P_MAX)
    El decreto de reparticion de oro (Decreto_d) suma un bono de crecimiento.
    El resultado respeta el tope P_MAX_POBLACION."""
    factor_felicidad = provincia.felicidad / 100.0
    tasa = TASA_CRECIMIENTO_POBLACION * factor_felicidad
    if provincia.decreto_d:
        tasa += DECRETO_D_BONO_CRECIMIENTO
    delta_p = tasa * provincia.poblacion * (1.0 - provincia.poblacion / P_MAX_POBLACION)
    provincia.poblacion = min(P_MAX_POBLACION, provincia.poblacion + delta_p)
    return provincia.poblacion


def procesar_crecimiento_poblacional(imperio):
    """hace crecer la poblacion de todas las provincias del
    imperio ANTES de la recaudacion, de modo que la economia del mismo turno ya
    opera sobre la base imponible actualizada."""
    for provincia in imperio.provincias:
        actualizar_poblacion(provincia)


def poblacion_total(imperio):
    """Suma la poblacion de todas las provincias del imperio (para reportes)."""
    return sum(p.poblacion for p in imperio.provincias)


def actualizar_felicidad(provincia, imperio):
    """La felicidad del turno siguiente se calcula como:
        Fel_i(t+1) = clip( Fel_i(t)
            + Delta_decretos_i(t)                       # bono del decreto de fertilidad (Decreto_f)
            - penalidad_fiscal(t)                       # los impuestos descontentan a la poblacion
            + k3 * (100 - Fel_i(t)) * 1[turnos_saqueado==0]  # recuperacion natural (bloqueada si saqueada)
            , 0, 100 )
    """
    fel = provincia.felicidad

    delta_decretos = DECRETO_F_BONO_FELICIDAD if provincia.decreto_f else 0.0

    penalidad_fiscal = PENALIDAD_IMPUESTOS_FELICIDAD * (
        imperio.tasa_impuesto + imperio.tasa_impuesto_comercio
    )

    recuperacion = 0.0
    if provincia.turnos_saqueado == 0:
        recuperacion = K3_RECUPERACION * (100.0 - fel)

    nueva_fel = fel + delta_decretos - penalidad_fiscal + recuperacion
    provincia.felicidad = min(100.0, max(0.0, nueva_fel))
    return provincia.felicidad


def evaluar_rebelion(provincia):
    """Seccion 4.1: si Fel_i(t) < Fel_umbral se calcula
        P_rebelion = min(1, k4 * (Fel_umbral - Fel_i(t))).
    Se genera u ~ U(0,1); si u <= P_rebelion estalla la rebelion (Evento E20).
    Devuelve True si la provincia se rebela este turno."""
    if provincia.felicidad >= FEL_UMBRAL:
        return False
    p_rebelion = min(1.0, K4_REBELION * (FEL_UMBRAL - provincia.felicidad))
    return random.random() <= p_rebelion


def aplicar_rebelion(provincia):
    """Consecuencias modeladas de la rebelion (Evento E20): la provincia pierde un
    porcentaje de su poblacion, su felicidad colapsa a 0 y queda marcada como
    rebelada (lo que activa el bloqueo de la Seccion 4.2)."""
    provincia.poblacion = int(provincia.poblacion * (1.0 - PORCENTAJE_PERDIDA_POBLACION_REBELION))
    provincia.felicidad = 0.0
    provincia.rebelion = True


def actualizar_bloqueo_reclutamiento(provincia):
    """Seccion 4.2: si Fel_i(t) < 50% la provincia queda bloqueada para reclutar
    tropas y construir estructuras."""
    provincia.bloqueada_baja_felicidad = provincia.felicidad < FEL_UMBRAL
    return provincia.bloqueada_baja_felicidad


def procesar_cierre_felicidad(imperio):
    resumenes = []
    for provincia in imperio.provincias:
        provincia.rebelion = False
        felicidad_anterior = provincia.felicidad

        if provincia.turnos_saqueado > 0:
            provincia.turnos_saqueado -= 1

        if provincia.cooldown_fertilidad > 0:
            provincia.cooldown_fertilidad -= 1

        actualizar_felicidad(provincia, imperio)

        # Los decretos duran 1 turno: se resetean despues de aplicar sus efectos
        provincia.decreto_f = False
        provincia.decreto_d = False

        se_rebelo = evaluar_rebelion(provincia)
        if se_rebelo:
            aplicar_rebelion(provincia)

        bloqueada = actualizar_bloqueo_reclutamiento(provincia)

        resumenes.append({
            "provincia": provincia,
            "felicidad_anterior": felicidad_anterior,
            "rebelion": se_rebelo,
            "bloqueada": bloqueada,
        })
    return resumenes


def mostrar_resumen_felicidad(imperio, resumenes):
    """Imprime el desglose de felicidad, rebelion y bloqueo por provincia (para pruebas)."""
    print(f"  [{imperio.nombre}] Felicidad:")
    for r in resumenes:
        p = r["provincia"]
        estado = f"Fel {r['felicidad_anterior']:.1f} -> {p.felicidad:.1f}"
        if r["rebelion"]:
            estado += " | [REBELION E20]"
        if r["bloqueada"]:
            estado += " | bloqueada reclutar/construir (4.2)"
        print(f"    P{p.id:02d} | {estado}")

from constantes import (
    TASA_INTERES_DEUDA, COEF_ADMINISTRATIVO,
    AC_BASE_COEF, FACTOR_SUELO, FACTOR_TERRENO, FACTOR_CLIMA,
    TASA_TRIBUTO, MANT_UNITARIO,
)


def obtener_mes(turno):
    """Convierte el numero de turno en 'mes' del ciclo anual (1-12).
    El impuesto directo por territorio solo se recauda cuando mes(t) = 1,
    tal como indica la funcion indicadora 1[mes(t)=1] de la Ecuacion 1.1."""
    return ((turno - 1) % 12) + 1


def calcular_actividad_comercial(provincia):
    """Ecuacion 1.3: AC_i(t) = AC_base,i * theta_terreno,i * theta_clima,i(t).
    Actualiza provincia.ac y tambien lo retorna.
    Si la provincia esta saqueada (turnos_saqueado > 0), AC = 0."""
    if provincia.turnos_saqueado > 0:
        provincia.ac = 0.0
        return 0.0
    ac_base = provincia.poblacion * AC_BASE_COEF * FACTOR_SUELO.get(provincia.suelo, 1.0)
    theta_terreno = FACTOR_TERRENO.get(provincia.terreno, 1.0)
    theta_clima = FACTOR_CLIMA.get(provincia.clima, 1.0)
    provincia.ac = ac_base * theta_terreno * theta_clima
    return provincia.ac


def calcular_pago_gobernador(poblacion):
    """funcion a trozos segun la poblacion de la provincia.
    Devuelve el pago en oro correspondiente a ese tramo de poblacion."""
    if poblacion < 50_000:
        return 0
    elif poblacion < 100_000:
        return 1
    elif poblacion < 250_000:
        return 2
    elif poblacion < 500_000:
        return 3
    elif poblacion < 750_000:
        return 4
    else:  # 750.000 <= poblacion <= 1.000.000 (P_MAX_POBLACION)
        return 5


def calcular_costo_gobierno(imperio):
    """Costo_Gobierno(t) = Sum f(Pob_i(t)) sobre todas las provincias del imperio."""
    return sum(calcular_pago_gobernador(p.poblacion) for p in imperio.provincias)


def calcular_gasto_mantenimiento(imperio):
    """Ecuacion 1.4: GM(t) = Cant_total(t) * Mant."""
    return imperio.unidades_totales * MANT_UNITARIO


def calcular_tributos(diplomacia, imperios, turno):
    """Calcula los tributos del turno a partir de las protecciones vigentes"""
    for imperio in imperios:
        imperio.tributos_recibidos = 0.0
        imperio.tributos_pagados = 0.0

    mes = obtener_mes(turno)
    for protegido, protector in diplomacia.protecciones.items():
        impuestos = 0.0
        for p in protegido.provincias:
            impuestos += (protegido.tasa_impuesto_comercio / 100) * p.ac
            if mes == 1:
                impuestos += (protegido.tasa_impuesto / 100) * p.poblacion
        tributo = TASA_TRIBUTO * impuestos
        protegido.tributos_pagados += tributo
        protector.tributos_recibidos += tributo


def procesar_cierre_economico(imperio, turno):
    """
    Aplica la Ecuacion 1.1 completa para un imperio en el turno indicado,
    siguiendo el orden: actividad comercial -> recaudacion -> gastos ->
    actualizacion del tesoro -> condicion de prestamo por deuda y
    devuelve un diccionario con el desglose, util para mostrar y verificar.
    """
    mes = obtener_mes(turno)

    # 1. Actualizar actividad comercial de cada provincia (Ecuacion 1.3)
    for provincia in imperio.provincias:
        calcular_actividad_comercial(provincia)

    # 2. Recaudacion (terminos positivos de la Ecuacion 1.1) - redondeada (sin decimales)
    impuestos_directos_anual = 0
    if mes == 1 and turno > 1:
        impuestos_directos_anual = round(sum(
            (imperio.tasa_impuesto / 100) * p.poblacion
            for p in imperio.provincias if p.turnos_saqueado == 0
        ))
    impuestos_comercio = round(sum(
        (imperio.tasa_impuesto_comercio / 100) * p.ac
        for p in imperio.provincias if p.turnos_saqueado == 0
    ))
    # Registrar el aporte individual de cada provincia (para inspeccion/depuracion)
    for provincia in imperio.provincias:
        if provincia.turnos_saqueado > 0:
            provincia.imp_prov = 0.0
        else:
            aporte_directo = (imperio.tasa_impuesto / 100) * provincia.poblacion if mes == 1 else 0.0
            aporte_comercio = (imperio.tasa_impuesto_comercio / 100) * provincia.ac
            provincia.imp_prov = aporte_directo + aporte_comercio

    trib_rec = round(imperio.tributos_recibidos)
    trib_pag = round(imperio.tributos_pagados)

    ingreso_total = impuestos_directos_anual + impuestos_comercio + trib_rec - trib_pag

    # 3. Gastos (terminos negativos de la Ecuacion 1.1) - redondeados
    gasto_mantenimiento = round(calcular_gasto_mantenimiento(imperio))
    intereses_deuda = 0
    if imperio.tesoro < 0:
        intereses_deuda = round(imperio.tesoro * TASA_INTERES_DEUDA)
    costo_gobierno = calcular_costo_gobierno(imperio)
    costo_administrativo = round(COEF_ADMINISTRATIVO * (impuestos_directos_anual + impuestos_comercio))

    gasto_total = gasto_mantenimiento + costo_gobierno + costo_administrativo

    # 4. Actualizacion de tesoreria (Ecuacion 1.1 completa) - sin decimales
    imperio.tesoro = round(imperio.tesoro + ingreso_total - gasto_total)

    # 5. Si el tesoro queda negativo, cobrar interes del 10%
    if imperio.tesoro < 0:
        imperio.tesoro = round(imperio.tesoro + imperio.tesoro * TASA_INTERES_DEUDA)

    return {
        "mes": mes,
        "impuestos_directos_anual": impuestos_directos_anual,
        "impuestos_comercio": impuestos_comercio,
        "tributos_recibidos": trib_rec,
        "tributos_pagados": trib_pag,
        "ingreso_total": ingreso_total,
        "gasto_mantenimiento": gasto_mantenimiento,
        "intereses_deuda": intereses_deuda,
        "costo_gobierno": costo_gobierno,
        "costo_administrativo": costo_administrativo,
        "gasto_total": gasto_total,
    }


def mostrar_resumen_economico(imperio, resumen):
    """Imprime el desglose del cierre economico de un imperio (para pruebas)."""
    print(f"  [{imperio.nombre}] mes={resumen['mes']} | "
          f"ingreso={resumen['ingreso_total']:.2f} "
          f"(directo_anual={resumen['impuestos_directos_anual']:.2f}, "
          f"comercio={resumen['impuestos_comercio']:.2f}, "
          f"trib_rec={resumen['tributos_recibidos']:.2f}, "
          f"trib_pag={resumen['tributos_pagados']:.2f}) | "
          f"gasto={resumen['gasto_total']:.2f} "
          f"(mantenimiento={resumen['gasto_mantenimiento']:.2f}, "
          f"interes={resumen['intereses_deuda']:.2f}, "
          f"gobierno={resumen['costo_gobierno']:.2f}, "
          f"administrativo={resumen['costo_administrativo']:.2f})")
    if imperio.tesoro < 0:
        print(f"    [!] Tesoro en deuda: {imperio.tesoro:.2f} oro "
              f"(interes del 10% por turno)")
    print(f"    -> Tesoro resultante: {imperio.tesoro:.2f}")


def modificar_impuestos_comercio(imperio, nueva_tasa):
    """Permite al jugador modificar la tasa de impuesto sobre comercio de un imperio.
    La nueva tasa debe estar entre 0 y 200 (porcentaje)."""
    posibles_impuestos = [0, 5, 10, 15, 20]
    if nueva_tasa in posibles_impuestos:
        imperio.tasa_impuesto_comercio = nueva_tasa
        print(f"[{imperio.nombre}] Tasa de impuesto sobre comercio modificada a {nueva_tasa:.1f}%")
    else:
        print(f"[{imperio.nombre}] Error: La tasa de impuesto sobre comercio debe estar entre 0 y 200%.")

def modificar_impuestos_anuales(imperio, nueva_tasa):
    """Permite al jugador modificar la tasa de impuesto directo de un imperio.
    La nueva tasa debe estar entre 0 y 200 (porcentaje)."""
    posibles_impuestos = [0, 5, 10, 15, 20]
    if nueva_tasa in posibles_impuestos:
        imperio.tasa_impuesto = nueva_tasa
        print(f"[{imperio.nombre}] Tasa de impuesto directo modificada a {nueva_tasa:.1f}%")
    else:
        print(f"[{imperio.nombre}] Error: La tasa de impuesto directo debe estar entre 0 y 200%.")

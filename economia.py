from constantes import (
    TASA_INTERES_DEUDA, FACTOR_PRESTAMO, COEF_ADMINISTRATIVO,
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
    Actualiza provincia.ac y tambien lo retorna."""
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

    # 2. Recaudacion (terminos positivos de la Ecuacion 1.1)
    impuestos_directos_anual = 0.0
    if mes == 1:
        impuestos_directos_anual = sum(
            (imperio.tasa_impuesto / 100) * p.poblacion for p in imperio.provincias
        )
    impuestos_comercio = sum(
        (imperio.tasa_impuesto_comercio / 100) * p.ac for p in imperio.provincias
    )
    # Registrar el aporte individual de cada provincia (para inspeccion/depuracion)
    for provincia in imperio.provincias:
        aporte_directo = (imperio.tasa_impuesto / 100) * provincia.poblacion if mes == 1 else 0.0
        aporte_comercio = (imperio.tasa_impuesto_comercio / 100) * provincia.ac
        provincia.imp_prov = aporte_directo + aporte_comercio

    trib_rec = imperio.tributos_recibidos   # Tributos diplomaticos entrantes (calculados por calcular_tributos, Parte 5)
    trib_pag = imperio.tributos_pagados     # Tributos diplomaticos salientes (Parte 5)

    ingreso_total = impuestos_directos_anual + impuestos_comercio + trib_rec - trib_pag

    # 3. Gastos (terminos negativos de la Ecuacion 1.1)
    gasto_mantenimiento = calcular_gasto_mantenimiento(imperio)          # Ecuacion 1.4 (GM)
    intereses_deuda = imperio.deuda * TASA_INTERES_DEUDA                  # Deuda(t) * tau_interes
    costo_gobierno = calcular_costo_gobierno(imperio)                     # Ecuacion 1.5
    costo_administrativo = COEF_ADMINISTRATIVO * (impuestos_directos_anual + impuestos_comercio)

    gasto_total = gasto_mantenimiento + intereses_deuda + costo_gobierno + costo_administrativo

    # 4. Actualizacion de tesoreria (Ecuacion 1.1 completa)
    imperio.tesoro = imperio.tesoro + ingreso_total - gasto_total

    # 5. Condicion de prestamo automatico por deuda (Seccion 4.4)
    prestamo_emitido = 0.0
    if imperio.tesoro < 0:
        prestamo_emitido = abs(imperio.tesoro)
        imperio.tesoro = 0.0
        imperio.deuda = (imperio.deuda + prestamo_emitido) * FACTOR_PRESTAMO

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
        "prestamo_emitido": prestamo_emitido,
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
    if resumen["prestamo_emitido"] > 0:
        print(f"    [!] Tesoro negativo: prestamo automatico emitido por "
              f"{resumen['prestamo_emitido']:.2f} oro (Seccion 4.4)")
    print(f"    -> Tesoro resultante: {imperio.tesoro:.2f} | Deuda: {imperio.deuda:.2f}")

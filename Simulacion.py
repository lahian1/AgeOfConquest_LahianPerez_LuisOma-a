import random

import numpy as np


# CONSTANTES DEL JUEGO (Parámetros fijos)

P_MAX_POBLACION = 1_000_000   # P_max: población máxima que puede tener una provincia 

# constantes del subsistema Economía
TASA_INTERES_DEUDA = 0.05     # τ_interes: %/turno sobre la deuda acumulada (parámetro de calibración)
FACTOR_PRESTAMO = 1.10        # recargo del 10% aplicado a la deuda cuando se emite un préstamo (Sección 4.4)
COEF_ADMINISTRATIVO = 0.591   # 59.1% de los impuestos totales recibidos

# Actividad Comercial. AC_base se calcula como población * coeficiente base,
# modulado por multiplicadores categóricos de suelo/terreno/clima (por ahora solo "Tierra",
# "Plano" y "Templado" existen en el mapa, se deja el diccionario listo para más categorías).
AC_BASE_COEF = 0.05
FACTOR_SUELO = {"Tierra": 1.0}
FACTOR_TERRENO = {"Plano": 1.0}
FACTOR_CLIMA = {"Templado": 1.0}

# constantes del subsistema Población y Felicidad 
FEL_UMBRAL = 50.0                     # Fel_umbral: umbral de felicidad para rebelion y bloqueo 
K3_RECUPERACION = 0.05                # k3: tasa de recuperación natural hacia 100 cuando no hay saqueo 
K4_REBELION = 0.02                    # k4: factor de probabilidad de rebelion
PENALIDAD_IMPUESTOS_FELICIDAD = 0.1   # cada punto % de tasa combinada resta esta fracción de felicidad (calibracion)
SAQUEO_PENALIDAD_FELICIDAD = 20.0     # reducción de felicidad por saqueo activo en la provincia 
DECRETO_F_BONO_FELICIDAD = 15.0       # Δ_decretos: bono de felicidad del decreto de fertilidad (Decreto_f)
DECRETO_D_BONO_CRECIMIENTO = 0.01     # bono extra de crecimiento poblacional del decreto de repartición de oro (Decreto_d)
TASA_CRECIMIENTO_POBLACION = 0.01     # tasa base de crecimiento poblacional por turno (calibracion) 
PORCENTAJE_PERDIDA_POBLACION_REBELION = 0.10  # la rebelion reduce la población de la provincia en este porcentaje (modelado)

# constantes del subsistema Unidades 
C_ORO_TROPA = 1.0        # C_oro_tropa: costo en oro por soldado reclutado
C_POB_TROPA = 100        # C_pob_tropa: habitantes necesarios por soldado reclutado
C_PA_TROPA = 1.0         # C_PA_tropa: costo fijo de PA por orden de reclutamiento
C_ORO_TORRE = 50.0       # C_oro_torre: costo en oro por Torre de Vigilancia
C_PA_TORRE = 0.5         # C_PA_torre: costo fijo de PA por construcción de torre
MANT_UNITARIO = 0.1      # Mant: costo de mantenimiento en oro por soldado y por turno 

# constantes del subsistema Diplomacia 
TASA_TRIBUTO = 0.05      # % de los impuestos del vasallo que se pagan como tributo al protector 


# CLASE IMPERIO

class Imperio:
    def __init__(self, nombre, tesoro_inicial=1000.0):
        self.nombre = nombre                # Variable auxiliar: identificador para UI y diplomacia
        self.tesoro = tesoro_inicial         # Variable de estado: reserva monetaria (oro)
        self.deuda = 0.0                     # Variable de estado: monto adeudado acumulado

        self.tributos_recibidos = 0.0        # Flujo (F): tributos entrantes por vasallaje recibido (Parte 5)
        self.tributos_pagados = 0.0          # Flujo (F): tributos salientes por protección otorgada (Parte 5)


        self.puntos_accion_max = 5.0         # Parámetro (P): capacidad fija de PA por turno
        self.puntos_accion_actual = self.puntos_accion_max  # Estado (E): PA disponibles este turno

        self.provincias = []                 # Lista de objetos Provincia que pertenecen a este imperio
        self.unidades_totales = 0            # (subsistema Unidades)

        # tasas fijadas por decreto del imperio Ecuación 1.1
        self.tasa_impuesto = 10.0            # % (τ_imp), aplicado una vez al año
        self.tasa_impuesto_comercio = 5.0    # % (τ_com), aplicado cada turno

        
        # total de provincias se implementará en la parte de Combate/Diplomacia.
        self.ubicacion_rey = None            # Referencia a la Provincia donde reside el rey
        self.rey_capturado = False           # Variable de estado (E): True si el rey fue capturado

    def agregar_provincia(self, provincia):
        """Asigna una provincia a este imperio y actualiza la referencia inversa."""
        provincia.dueño = self
        self.provincias.append(provincia)

    def resetear_puntos_accion(self):
        """Repone los puntos de acción disponibles al máximo del parámetro. Se llamará
        en el cierre de cada turno (Parte 2 en adelante)."""
        self.puntos_accion_actual = self.puntos_accion_max

    def __repr__(self):
        return (f"Imperio({self.nombre}, tesoro={self.tesoro:.1f}, "
                f"PA={self.puntos_accion_actual}/{self.puntos_accion_max}, "
                f"provincias={len(self.provincias)})")



# CLASE PROVINCIA
# Unidad espacial que produce recursos, alberga población y estructuras.

class Provincia:
    def __init__(self, id_prov, fila, columna, suelo, terreno):
        self.id = id_prov
        self.posicion = (fila, columna)

        # hay que generar estos parametros aleatoriamente pero ahora los dejo fijos para poder probar el juego
        self.suelo = suelo
        self.terreno = terreno
        self.clima = "Templado"

        self.dueño = None                    # Referencia al Imperio propietario (antes: dueño Y propietario duplicados)

        self.poblacion = 1000                # Variable de estado (personas). Tope: P_MAX_POBLACION (Sección 4.3)
        self.felicidad = 80.0                # Variable de estado, porcentaje 0-100
        self.fortificacion = False           # Variable de estado, booleana (efectividad 100%, ver Ecuación 2.2)
        self.tep = 0                         # Tiempo en Propiedad: turnos consecutivos bajo el mismo dueño
        self.torre_vigilancia = False        # Variable de estado, booleana
        self.u_prov = 0                      # Cantidad de soldados estacionados en esta provincia

        self.ac = 0.0                        # actividad_comercial: variable de flujo (Ecuación 1.3)
        self.imp_prov = 0.0                  # impuestos generados por esta provincia en el turno actual
        self.saqueo = False                  # Flujo (F): acción de saqueo activa este turno
        self.decreto_f = False               # Decreto_f: bono de felicidad (fertilidad)
        self.decreto_d = False               # Decreto_d: bono de población (repartición de oro)
        self.venta = False
        self.precio_venta = 0
        self.comprador_v = None

        self.rebelion = False                  # Variable de estado (E): True si la provincia se rebeló este turno (Evento E20)
        self.bloqueada_baja_felicidad = False  # Variable de estado (E): True bloquea reclutar/construir (Sección 4.2)

    def __repr__(self):
        dueño_nombre = self.dueño.nombre if self.dueño else "Sin dueño"
        return f"Provincia({self.id:02d}, dueño={dueño_nombre})"


def mostrar_mapa(mapa):
    """Imprime el tablero mostrando el ID de cada provincia."""
    print("\n          === MAPA DEL JUEGO (MATRIZ DE PROVINCIAS) ===")
    for fila in mapa:
        linea = ""
        for provincia in fila:
            linea += f"[ {provincia.id:02d} ] "
        print(linea)
    print("============================================\n")


def mostrar_mapa_por_dueño(mapa):
    """Imprime el tablero mostrando el imperio dueño de cada provincia (o '--' si no tiene)."""
    print("\n          === MAPA DEL JUEGO (POR IMPERIO) ===")
    for fila in mapa:
        linea = ""
        for provincia in fila:
            etiqueta = provincia.dueño.nombre[:3] if provincia.dueño else "---"
            linea += f"[ {etiqueta:^3} ] "
        print(linea)
    print("============================================\n")


def mostrar_estado_imperios(imperios):
    """Imprime el resumen de tesoro, PA y provincias de cada imperio (para pruebas)."""
    print("--- Estado inicial de los imperios ---")
    for imperio in imperios:
        ids_provincias = [p.id for p in imperio.provincias]
        rey = imperio.ubicacion_rey.id if imperio.ubicacion_rey else "sin asignar"
        print(f"{imperio.nombre}: tesoro={imperio.tesoro:.1f} oro | "
              f"PA={imperio.puntos_accion_actual}/{imperio.puntos_accion_max} | "
              f"rey_en_provincia={rey} | "
              f"provincias={ids_provincias}")
    print("---------------------------------------\n")


def buscar_provincia(mapa, id_prov):
    """Recorre la matriz y devuelve la Provincia con el ID indicado (o None si no existe)."""
    for fila in mapa:
        for provincia in fila:
            if provincia.id == id_prov:
                return provincia
    return None


def crear_mapa(filas, columnas):
    """Crea la matriz de provincias del tamaño indicado."""
    mapa = []
    id_provincia = 1
    for i in range(filas):
        fila = []
        for j in range(columnas):
            provincia = Provincia(id_provincia, i, j, "Tierra", "Plano")
            fila.append(provincia)
            id_provincia += 1
        mapa.append(fila)
    return mapa


def asignar_provincias_iniciales(mapa, imperios):
    """
    Reparte el mapa entre los imperios de prueba dividiéndolo por columnas
    (imperio 0 se queda con la mitad izquierda, imperio 1 con la mitad derecha).
    Además, asigna a cada imperio la primera provincia recibida como la
    ubicación inicial de su rey.
    Es una asignación provisional solo para poder probar el subsistema Economía
    en la Parte 2; el reparto real de inicio de partida lo vemos más adelante lahian.
    """
    columnas = len(mapa[0])
    mitad = columnas // 2
    for fila in mapa:
        for provincia in fila:
            _, columna = provincia.posicion
            if columna < mitad:
                imperios[0].agregar_provincia(provincia)
            else:
                imperios[1].agregar_provincia(provincia)

    for imperio in imperios:
        if imperio.provincias:
            imperio.ubicacion_rey = imperio.provincias[0]



# PARTE 2: SUBSISTEMA ECONOMÍA
# Implementa la Ecuación 1.1 (Actualización del Tesoro Imperial) y sus
# componentes auxiliares (1.3 Actividad Comercial, 1.5 Costo de Gobierno,


def obtener_mes(turno):
    """Convierte el número de turno en 'mes' del ciclo anual (1-12).
    El impuesto directo por territorio solo se recauda cuando mes(t) = 1,
    tal como indica la función indicadora 𝟙[mes(t)=1] de la Ecuación 1.1."""
    return ((turno - 1) % 12) + 1


def calcular_actividad_comercial(provincia):
    """Ecuación 1.3: AC_i(t) = AC_base,i · θ_terreno,i · θ_clima,i(t).
    Actualiza provincia.ac y también lo retorna."""
    ac_base = provincia.poblacion * AC_BASE_COEF * FACTOR_SUELO.get(provincia.suelo, 1.0)
    theta_terreno = FACTOR_TERRENO.get(provincia.terreno, 1.0)
    theta_clima = FACTOR_CLIMA.get(provincia.clima, 1.0)
    provincia.ac = ac_base * theta_terreno * theta_clima
    return provincia.ac


def calcular_pago_gobernador(poblacion):
    """función a trozos según la población de la provincia.
    Devuelve el pago en oro correspondiente a ese tramo de población."""
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
    """Costo_Gobierno(t) = Σ f(Pob_i(t)) sobre todas las provincias del imperio."""
    return sum(calcular_pago_gobernador(p.poblacion) for p in imperio.provincias)


def calcular_gasto_mantenimiento(imperio):
    """Ecuación 1.4: GM(t) = Cant_total(t) · Mant."""
    return imperio.unidades_totales * MANT_UNITARIO


def procesar_cierre_economico(imperio, turno):
    """
    Aplica la Ecuación 1.1 completa para un imperio en el turno indicado,
    siguiendo el orden: actividad comercial -> recaudación -> gastos ->
    actualización del tesoro -> condición de préstamo por deuda y
    devuelve un diccionario con el desglose, útil para mostrar y verificar.
    """
    mes = obtener_mes(turno)

    # 1. Actualizar actividad comercial de cada provincia (Ecuación 1.3)
    for provincia in imperio.provincias:
        calcular_actividad_comercial(provincia)

    # 2. Recaudacion (terminos positivos de la Ecuación 1.1)
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

    trib_rec = imperio.tributos_recibidos   # Tributos diplomáticos entrantes (calculados por calcular_tributos, Parte 5)
    trib_pag = imperio.tributos_pagados     # Tributos diplomáticos salientes (Parte 5)

    ingreso_total = impuestos_directos_anual + impuestos_comercio + trib_rec - trib_pag

    # 3. Gastos (terminos negativos de la Ecuación 1.1)
    gasto_mantenimiento = calcular_gasto_mantenimiento(imperio)          # Ecuación 1.4 (GM)
    intereses_deuda = imperio.deuda * TASA_INTERES_DEUDA                  # Deuda(t) · τ_interes
    costo_gobierno = calcular_costo_gobierno(imperio)                     # Ecuación 1.5
    costo_administrativo = COEF_ADMINISTRATIVO * (impuestos_directos_anual + impuestos_comercio)

    gasto_total = gasto_mantenimiento + intereses_deuda + costo_gobierno + costo_administrativo

    # 4. Actualización de tesorería (Ecuación 1.1 completa)
    imperio.tesoro = imperio.tesoro + ingreso_total - gasto_total

    # 5. Condición de préstamo automático por deuda (Sección 4.4)
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
    """Imprime el desglose del cierre económico de un imperio (para pruebas)."""
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



# PARTE 3: SUBSISTEMA POBLACIÓN Y FELICIDAD

def actualizar_poblacion(provincia):
    """Crecimiento poblacional con modelo logístico modulado por la
    felicidad del turno anterior:
        ΔP_i(t) = TASA_CRECIMIENTO · (Fel_i(t)/100) · P_i(t) · (1 − P_i(t)/P_MAX)
    El decreto de repartición de oro (Decreto_d) suma un bono de crecimiento.
    El resultado respeta el tope P_MAX_POBLACION."""
    factor_felicidad = provincia.felicidad / 100.0
    tasa = TASA_CRECIMIENTO_POBLACION * factor_felicidad
    if provincia.decreto_d:
        tasa += DECRETO_D_BONO_CRECIMIENTO
    delta_p = tasa * provincia.poblacion * (1.0 - provincia.poblacion / P_MAX_POBLACION)
    provincia.poblacion = min(P_MAX_POBLACION, provincia.poblacion + delta_p)
    return provincia.poblacion


def procesar_crecimiento_poblacional(imperio):
    """hace crecer la población de todas las provincias del
    imperio ANTES de la recaudación, de modo que la economía del mismo turno ya
    opera sobre la base imponible actualizada."""
    for provincia in imperio.provincias:
        actualizar_poblacion(provincia)


def poblacion_total(imperio):
    """Suma la población de todas las provincias del imperio (para reportes)."""
    return sum(p.poblacion for p in imperio.provincias)


def actualizar_felicidad(provincia, imperio):
    """La felicidad del turno siguiente se calcula como:
        Fel_i(t+1) = clip( Fel_i(t)
            + Δ_decretos_i(t)                       # bono del decreto de fertilidad (Decreto_f)
            − penalidad_fiscal(t)                   # los impuestos descontentan a la población
            − penalidad_saqueo(t)                   # el saqueo (Saq_i(t)) golpea la moral
            + k3 · (100 − Fel_i(t)) · 𝟙[sin_saqueo] # recuperación natural hacia el máximo
            , 0, 100 )
   """
    fel = provincia.felicidad

    delta_decretos = DECRETO_F_BONO_FELICIDAD if provincia.decreto_f else 0.0

    penalidad_fiscal = PENALIDAD_IMPUESTOS_FELICIDAD * (
        imperio.tasa_impuesto + imperio.tasa_impuesto_comercio
    )

    penalidad_saqueo = SAQUEO_PENALIDAD_FELICIDAD if provincia.saqueo else 0.0

    recuperacion = 0.0
    if not provincia.saqueo:
        recuperacion = K3_RECUPERACION * (100.0 - fel)

    nueva_fel = fel + delta_decretos - penalidad_fiscal - penalidad_saqueo + recuperacion
    provincia.felicidad = min(100.0, max(0.0, nueva_fel))
    return provincia.felicidad


def evaluar_rebelion(provincia):
    """Sección 4.1: si Fel_i(t) < Fel_umbral se calcula
        P_rebelion = min(1, k4 · (Fel_umbral − Fel_i(t))).
    Se genera u ~ U(0,1); si u <= P_rebelion estalla la rebelión (Evento E20).
    Devuelve True si la provincia se rebela este turno."""
    if provincia.felicidad >= FEL_UMBRAL:
        return False
    p_rebelion = min(1.0, K4_REBELION * (FEL_UMBRAL - provincia.felicidad))
    return random.random() <= p_rebelion


def aplicar_rebelion(provincia):
    """Consecuencias modeladas de la rebelión (Evento E20): la provincia pierde un
    porcentaje de su población, su felicidad colapsa a 0 y queda marcada como
    rebelada (lo que activa el bloqueo de la Sección 4.2)."""
    provincia.poblacion = int(provincia.poblacion * (1.0 - PORCENTAJE_PERDIDA_POBLACION_REBELION))
    provincia.felicidad = 0.0
    provincia.rebelion = True


def actualizar_bloqueo_reclutamiento(provincia):
    """Sección 4.2: si Fel_i(t) < 50% la provincia queda bloqueada para reclutar
    tropas y construir estructuras."""
    provincia.bloqueada_baja_felicidad = provincia.felicidad < FEL_UMBRAL
    return provincia.bloqueada_baja_felicidad


def procesar_cierre_felicidad(imperio):
    resumenes = []
    for provincia in imperio.provincias:
        provincia.rebelion = False
        felicidad_anterior = provincia.felicidad

        actualizar_felicidad(provincia, imperio)

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
    """Imprime el desglose de felicidad, rebelión y bloqueo por provincia (para pruebas)."""
    print(f"  [{imperio.nombre}] Felicidad:")
    for r in resumenes:
        p = r["provincia"]
        estado = f"Fel {r['felicidad_anterior']:.1f} -> {p.felicidad:.1f}"
        if r["rebelion"]:
            estado += " | [REBELION E20]"
        if r["bloqueada"]:
            estado += " | bloqueada reclutar/construir (4.2)"
        print(f"    P{p.id:02d} | {estado}")



# PARTE 4: SUBSISTEMA UNIDADES

def reclutar_soldados(imperio, provincia, cantidad):
    """Orden de reclutamiento (Evento E4): recluta `cantidad` soldados en la provincia.
    Validaciones y costos:
      - la provincia debe ser del imperio y no estar bloqueada por baja felicidad (4.2);
      - cantidad > 0;
      - PA disponibles >= C_PA_TROPA (1 PA fijo por orden, no por soldado);
      - tesoro >= cantidad · C_ORO_TROPA;
      - población >= cantidad · C_POB_TROPA.
    Si todo pasa, se descuentan oro, población y PA, y la cantidad se suma a la
    guarnición de la provincia (u_prov) y al total del imperio (unidades_totales).
    Devuelve un diccionario con el resultado o el motivo de rechazo."""
    if provincia.dueño is not imperio:
        return {"ok": False, "motivo": "la provincia no pertenece a este imperio"}
    if provincia.bloqueada_baja_felicidad:
        return {"ok": False, "motivo": "provincia bloqueada por baja felicidad (Sección 4.2)"}
    if cantidad <= 0:
        return {"ok": False, "motivo": "la cantidad debe ser positiva"}

    costo_oro = cantidad * C_ORO_TROPA
    costo_poblacion = cantidad * C_POB_TROPA

    if imperio.puntos_accion_actual < C_PA_TROPA:
        return {"ok": False, "motivo": "puntos de acción insuficientes"}
    if imperio.tesoro < costo_oro:
        return {"ok": False, "motivo": f"tesoro insuficiente (se necesitan {costo_oro:.1f} oro)"}
    if provincia.poblacion < costo_poblacion:
        return {"ok": False, "motivo": f"población insuficiente (se necesitan {costo_poblacion:,} habitantes)"}

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
    if provincia.bloqueada_baja_felicidad:
        return {"ok": False, "motivo": "provincia bloqueada por baja felicidad (Sección 4.2)"}
    if provincia.torre_vigilancia:
        return {"ok": False, "motivo": "la provincia ya tiene torre de vigilancia"}
    if imperio.tesoro < C_ORO_TORRE:
        return {"ok": False, "motivo": f"tesoro insuficiente (se necesitan {C_ORO_TORRE:.1f} oro)"}
    if imperio.puntos_accion_actual < C_PA_TORRE:
        return {"ok": False, "motivo": "puntos de acción insuficientes"}

    imperio.tesoro -= C_ORO_TORRE
    imperio.puntos_accion_actual -= C_PA_TORRE
    provincia.torre_vigilancia = True

    return {"ok": True, "costo_oro": C_ORO_TORRE, "costo_pa": C_PA_TORRE}



# PARTE 5: SUBSISTEMA DIPLOMACIA

class Diplomacia:
    """Tabla de relaciones entre pares de imperios y de protección (vasallaje)."""

    PAZ = "paz"
    GUERRA = "guerra"
    ALIANZA = "alianza"
    ALTO_AL_FUEGO = "alto_al_fuego"

    def __init__(self):
        self.estados = {}       # (imperio_a, imperio_b) -> estado de relación
        self.protecciones = {}  # protegido -> protector (vasallaje activo)

    @staticmethod
    def _clave(a, b):
        """Clave simétrica para la pareja de imperios (el orden no importa)."""
        return (a, b) if id(a) < id(b) else (b, a)

    def estado(self, a, b):
        """Devuelve el estado de relación actual."""
        return self.estados.get(self._clave(a, b), self.PAZ)

    def _establecer(self, a, b, estado):
        self.estados[self._clave(a, b)] = estado

    def declarar_guerra(self, a, b):
        """Evento E7: pasa la relación a guerra (si había alianza, esta se rompe).
        Solo en guerra es legal atacar."""
        if self.estado(a, b) == self.GUERRA:
            return {"ok": False, "motivo": "ya están en guerra"}
        self._establecer(a, b, self.GUERRA)
        return {"ok": True, "estado": self.GUERRA}

    def proponer_paz(self, a, b):
        """Propuesta de paz: de guerra pasa a alto el fuego (tregua); de alto el
        fuego a paz plena. Durante la tregua tampoco es legal atacar."""
        actual = self.estado(a, b)
        if actual == self.GUERRA:
            self._establecer(a, b, self.ALTO_AL_FUEGO)
            return {"ok": True, "estado": self.ALTO_AL_FUEGO,
                    "motivo": "alto el fuego acordado (tregua)"}
        elif actual == self.ALTO_AL_FUEGO:
            self._establecer(a, b, self.PAZ)
            return {"ok": True, "estado": self.PAZ, "motivo": "paz firmada"}
        elif actual == self.PAZ:
            return {"ok": False, "motivo": "ya están en paz"}
        else:
            return {"ok": False, "motivo": "no están en guerra; no tiene sentido proponer paz"}

    def formar_alianza(self, a, b):
        """Solo se puede firmar alianza desde el estado de paz."""
        if self.estado(a, b) != self.PAZ:
            return {"ok": False, "motivo": "solo se puede aliarse desde el estado de paz"}
        self._establecer(a, b, self.ALIANZA)
        return {"ok": True, "estado": self.ALIANZA}

    def romper_alianza(self, a, b):
        """Rompe la alianza activa (la relación vuelve a paz)."""
        if self.estado(a, b) != self.ALIANZA:
            return {"ok": False, "motivo": "no hay alianza activa"}
        self._establecer(a, b, self.PAZ)
        return {"ok": True, "estado": self.PAZ}

    def proteger(self, protector, protegido):
        """Establece vasallaje: el imperio protegido paga tributo al protector."""
        if protegido is protector:
            return {"ok": False, "motivo": "un imperio no puede protegerse a sí mismo"}
        if self.protecciones.get(protegido) == protector:
            return {"ok": False, "motivo": "ya existe esa protección"}
        self.protecciones[protegido] = protector
        return {"ok": True}

    def es_legal_atacar(self, a, b):
        """Regla de legalidad"""
        return self.estado(a, b) == self.GUERRA


def otro_imperio(imperios, imperio):
    """Devuelve el imperio rival (el que no es `imperio`) de la lista."""
    for otro in imperios:
        if otro is not imperio:
            return otro
    return None


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


def mostrar_relaciones(diplomacia, imperios):
    """Imprime la tabla de relaciones entre todos los pares de imperios y los vasallajes."""
    print("  Tabla de relaciones diplomáticas:")
    for i in range(len(imperios)):
        for j in range(i + 1, len(imperios)):
            a, b = imperios[i], imperios[j]
            print(f"    {a.nombre} <-> {b.nombre}: {diplomacia.estado(a, b)}")
    for protegido, protector in diplomacia.protecciones.items():
        print(f"    {protegido.nombre} esta protegido por {protector.nombre} (paga tributo)")


def main():
    # variables de control de la partida
    turno = 1
    limite_turnos = 20
    partida_terminada = False

    # variables de Tablero
 
    filas = 4
    columnas = 4
    mapa = crear_mapa(filas, columnas)

    # Creación de los imperios de prueba (Parte 1)
    imperio_jugador = Imperio("Jugador", tesoro_inicial=1000.0)
    imperio_ia = Imperio("IA", tesoro_inicial=1000.0)
    imperios = [imperio_jugador, imperio_ia]

    # Diplomacia: tabla de relaciones y vasallajes
    diplomacia = Diplomacia()

    # Reparto inicial de provincias entre los dos imperios de prueba (incluye ubicación del rey)
    asignar_provincias_iniciales(mapa, imperios)

    print("*************************************************")
    print("----INICIO DE LA PARTIDA----")
    print("*************************************************")

    mostrar_mapa_por_dueño(mapa)
    mostrar_estado_imperios(imperios)

    # Bucle principal de turnos
    while not partida_terminada:
        print(f"Partida en turno {turno} | {imperio_jugador.nombre}: "
              f"tesoro={imperio_jugador.tesoro:.1f} oro, "
              f"PA={imperio_jugador.puntos_accion_actual}/{imperio_jugador.puntos_accion_max} | "
              f"Haga sus movimientos")
        mostrar_mapa(mapa)

        # Aquí puedes agregar la lógica de la partida, como movimientos de jugadores, actualizaciones de estado, etc.
        #

        respuesta = input("ENTER avanzar | 'salir' | 'reclutar <id> <cant>' | 'torre <id>' | "
                          "'guerra' | 'paz' | 'alianza' | 'romper' | 'proteger' | 'relaciones' | "
                          "'fel <id> <0-100>' | 'estado': ")
        respuesta = respuesta.strip().lower()

        if respuesta == "salir":
            print("Terminando juego...")
            break
        elif respuesta == "guerra":
            # Parte 5: declara la guerra contra el otro imperio.
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.declarar_guerra(imperio_jugador, rival)
            if res["ok"]:
                print(f"  Guerra declarada contra {rival.nombre} (E7)")
            else:
                print(f"  No se pudo declarar guerra: {res['motivo']}")
            continue
        elif respuesta == "paz":
            # Parte 5: propone paz (guerra -> alto el fuego -> paz).
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
            # Parte 5: convierte al otro imperio en vasallo del Jugador (paga tributo).
            rival = otro_imperio(imperios, imperio_jugador)
            res = diplomacia.proteger(imperio_jugador, rival)
            if res["ok"]:
                print(f"  {rival.nombre} ahora es vasallo de {imperio_jugador.nombre} (paga tributo)")
            else:
                print(f"  No se pudo establecer la protección: {res['motivo']}")
            continue
        elif respuesta == "relaciones":
            mostrar_relaciones(diplomacia, imperios)
            continue
        elif respuesta.startswith("reclutar "):
            #recluta soldados en una provincia propia .
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
                              f"(-{res['costo_oro']:.1f} oro, -{res['costo_poblacion']:,} población, -1 PA)")
                    else:
                        print(f"  No se pudo reclutar: {res['motivo']}")
            except (ValueError, IndexError):
                print("  Uso: reclutar <id_provincia> <cantidad>")
            continue
        elif respuesta.startswith("torre "):
            # construye una Torre de Vigilancia en una provincia propia.
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
        elif respuesta.startswith("fel "):
            # Comando para forzar la felicidad de una provincia y probar que funcione. 
            # para poder probar el disparo de rebelión (4.1) y el bloqueo (4.2).
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
                    dueño = provincia.dueño.nombre if provincia.dueño else "libre"
                    print(f"  P{provincia.id:02d} ({dueño}): pob={provincia.poblacion:,.0f} "
                          f"fel={provincia.felicidad:.1f} reb={provincia.rebelion} "
                          f"bloq={provincia.bloqueada_baja_felicidad} "
                          f"soldados={provincia.u_prov} torre={'SI' if provincia.torre_vigilancia else 'no'}")
            continue

        # 1. Crecimiento de poblacion usa la felicidad del 
        #    turno anterior y actualiza la base imponible que verá la economia.
        print(f"\n--- Crecimiento de población del turno {turno} ---")
        for imperio in imperios:
            antes = poblacion_total(imperio)
            procesar_crecimiento_poblacional(imperio)
            despues = poblacion_total(imperio)
            print(f"  [{imperio.nombre}] población total: {antes:,.0f} -> {despues:,.0f}")
        print("-------------------------------------------\n")

        # 2. Cierre económico del turno que acaba de terminar.
        #    Antes de recaudar se calculan los tributos diplomáticos, que
        #    dependen de la actividad comercial ya actualizada de cada imperio.
        for imperio in imperios:
            for provincia in imperio.provincias:
                calcular_actividad_comercial(provincia)
        calcular_tributos(diplomacia, imperios, turno)

        print(f"--- Cierre económico del turno {turno} ---")
        for imperio in imperios:
            resumen = procesar_cierre_economico(imperio, turno)
            mostrar_resumen_economico(imperio, resumen)
        print("-------------------------------------------\n")

        # 3. Cierre de felicidad: usa los impuestos y
        #    saqueos YA aplicados en el cierre económico, evalúa la rebelión (4.1)
        #    y actualiza el bloqueo de reclutamiento/construcción (4.2).
        print(f"--- Cierre de felicidad del turno {turno} ---")
        for imperio in imperios:
            resumenes = procesar_cierre_felicidad(imperio)
            mostrar_resumen_felicidad(imperio, resumenes)
        print("-------------------------------------------\n")

        turno += 1
        for imperio in imperios:
            imperio.resetear_puntos_accion()   # los PA se reponen al iniciar el nuevo turno (Parte 4)
        print("Avanzando al siguiente turno...")
      # inspeccionar_provincia(mapa, input("Ingrese el ID de la provincia a inspeccionar: "))
    print("\n=== FIN DE LA PARTIDA ===")


if __name__ == "__main__":
    main()

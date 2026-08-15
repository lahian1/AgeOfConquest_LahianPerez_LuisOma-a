import numpy as np


# CONSTANTES DEL JUEGO (Parámetros fijos)

P_MAX_POBLACION = 1_000_000   # P_max: población máxima que puede tener una provincia 

# --- constantes del subsistema Economía ---
TASA_INTERES_DEUDA = 0.05     # τ_interes: %/turno sobre la deuda acumulada (parámetro de calibración)
FACTOR_PRESTAMO = 1.10        # recargo del 10% aplicado a la deuda cuando se emite un préstamo (Sección 4.4)
COEF_ADMINISTRATIVO = 0.591   # 59.1% de los impuestos totales recibidos (Ecuación 1.1)

# Ecuación 1.3: Actividad Comercial. AC_base se calcula como población * coeficiente base,
# modulado por multiplicadores categóricos de suelo/terreno/clima (por ahora solo "Tierra",
# "Plano" y "Templado" existen en el mapa, se deja el diccionario listo para más categorías).
AC_BASE_COEF = 0.05
FACTOR_SUELO = {"Tierra": 1.0}
FACTOR_TERRENO = {"Plano": 1.0}
FACTOR_CLIMA = {"Templado": 1.0}


# CLASE IMPERIO

class Imperio:
    def __init__(self, nombre, tesoro_inicial=1000.0):
        self.nombre = nombre                # Variable auxiliar: identificador para UI y diplomacia
        self.tesoro = tesoro_inicial         # Variable de estado: reserva monetaria (oro)
        self.deuda = 0.0                     # Variable de estado: monto adeudado acumulado


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
    ubicación inicial de su rey (mecánica de Colapso de Corona, Sección 4.5).
    Es una asignación provisional solo para poder probar el subsistema Economía
    en la Parte 2; el reparto real de inicio de partida se definirá más adelante.
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
# y la condición de préstamo automático por deuda, Sección 4.4).

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
    """Ecuación 1.5: f(P_i(t)), función a trozos según la población de la provincia.
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
    """Ecuación 1.4: GM(t) = Cant_total(t) · Mant.
    Por ahora no existen unidades, así que
    devuelve 0, pero la estructura ya queda lista para cuando exista
    imperio.unidades_totales y una constante MANT_UNITARIO."""
    return imperio.unidades_totales * 0  # placeholder


def procesar_cierre_economico(imperio, turno):
    """
    Aplica la Ecuación 1.1 completa para un imperio en el turno indicado,
    siguiendo el orden: actividad comercial -> recaudación -> gastos ->
    actualización del tesoro -> condición de préstamo por deuda (Sección 4.4).
    Devuelve un diccionario con el desglose, útil para mostrar y verificar.
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

    trib_rec = 0.0   # Tributos diplomaticos
    trib_pag = 0.0

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
          f"comercio={resumen['impuestos_comercio']:.2f}) | "
          f"gasto={resumen['gasto_total']:.2f} "
          f"(mantenimiento={resumen['gasto_mantenimiento']:.2f}, "
          f"interes={resumen['intereses_deuda']:.2f}, "
          f"gobierno={resumen['costo_gobierno']:.2f}, "
          f"administrativo={resumen['costo_administrativo']:.2f})")
    if resumen["prestamo_emitido"] > 0:
        print(f"    ⚠ Tesoro negativo: préstamo automático emitido por "
              f"{resumen['prestamo_emitido']:.2f} oro (Sección 4.4)")
    print(f"    -> Tesoro resultante: {imperio.tesoro:.2f} | Deuda: {imperio.deuda:.2f}")


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

    # Reparto inicial de provincias entre los dos imperios de prueba (incluye ubicación del rey)
    asignar_provincias_iniciales(mapa, imperios)

    print("*************************************************")
    print("----INICIO DE LA PARTIDA----")
    print("*************************************************")

    mostrar_mapa_por_dueño(mapa)
    mostrar_estado_imperios(imperios)

    # Bucle principal de turnos
    while not partida_terminada:
        print("Partida en turno:", turno, "Haga sus movimientos")
        mostrar_mapa(mapa)

        # Aquí puedes agregar la lógica de la partida, como movimientos de jugadores, actualizaciones de estado, etc.
        #

        respuesta = input("Presiona ENTER para avanzar (o escribe 'salir' para terminar): ")
        if respuesta.strip().lower() == "salir":
            print("Terminando juego...")
            break

        # ---cierre económico del turno que acaba de terminar ---
        print(f"\n--- Cierre económico del turno {turno} ---")
        for imperio in imperios:
            resumen = procesar_cierre_economico(imperio, turno)
            mostrar_resumen_economico(imperio, resumen)
        print("-------------------------------------------\n")

        turno += 1
        print("Avanzando al siguiente turno...")
      # inspeccionar_provincia(mapa, input("Ingrese el ID de la provincia a inspeccionar: "))
    print("\n=== FIN DE LA PARTIDA ===")


if __name__ == "__main__":
    main()

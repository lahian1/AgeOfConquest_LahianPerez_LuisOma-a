# CONSTANTES DEL JUEGO (Parametros fijos)

P_MAX_POBLACION = 1_000_000   # P_max: poblacion maxima que puede tener una provincia

# constantes del subsistema Economia
TASA_INTERES_DEUDA = 0.10     # tau_interes: %/turno sobre el saldo negativo del tesoro (Seccion 4.4)
COEF_ADMINISTRATIVO = 0.591   # 59.1% de los impuestos totales recibidos

# Actividad Comercial. AC_base se calcula como poblacion * coeficiente base,
# modulado por multiplicadores categoricos de suelo/terreno/clima (por ahora solo "Tierra",
# "Plano" y "Templado" existen en el mapa, se deja el diccionario listo para mas categorias).
AC_BASE_COEF = 0.002
FACTOR_SUELO = {"Tierra": 1.0}
FACTOR_TERRENO = {"Plano": 1.0}
FACTOR_CLIMA = {"Templado": 1.0}

# constantes del subsistema Poblacion y Felicidad
FEL_UMBRAL = 50.0                     # Fel_umbral: umbral de felicidad para rebelion y bloqueo
K3_RECUPERACION = 0.05                # k3: tasa de recuperacion natural hacia 100 cuando no hay saqueo
K4_REBELION = 0.02                    # k4: factor de probabilidad de rebelion
PENALIDAD_IMPUESTOS_FELICIDAD = 0.1   # cada punto % de tasa combinada resta esta fraccion de felicidad (calibracion)
SAQUEO_PENALIDAD_FELICIDAD = 30.0     # reduccion de felicidad al saquear una provincia
DECRETO_F_BONO_FELICIDAD = 15.0       # Delta_decretos: bono de felicidad del decreto de fertilidad (Decreto_f)
DECRETO_D_BONO_CRECIMIENTO = 0.01     # bono extra de crecimiento poblacional del decreto de reparticion de oro (Decreto_d)
TASA_CRECIMIENTO_POBLACION = 0.00277     # tasa base de crecimiento poblacional por turno (calibracion)
PORCENTAJE_PERDIDA_POBLACION_REBELION = 0.10  # la rebelion reduce la poblacion de la provincia en este porcentaje (modelado)

# costos de decretos
C_ORO_FERTILIDAD = 37.0       # costo en oro del decreto de fertilidad
C_PA_FERTILIDAD = 0.5         # costo en PA del decreto de fertilidad
COOLDOWN_FERTILIDAD = 5       # turnos de cooldown antes de volver a usar fertilidad
C_ORO_REPARTIR = 22.0         # costo en oro del decreto de repartir dinero
C_PA_REPARTIR = 0.1           # costo en PA del decreto de repartir dinero

# constantes del subsistema Unidades
C_ORO_TROPA = 1.0        # C_oro_tropa: costo en oro por soldado reclutado
C_POB_TROPA = 100        # C_pob_tropa: habitantes necesarios por soldado reclutado
C_PA_TROPA = 1.0         # C_PA_tropa: costo fijo de PA por orden de reclutamiento
C_ORO_TORRE = 50.0       # C_oro_torre: costo en oro por Torre de Vigilancia
C_PA_TORRE = 0.5         # C_PA_torre: costo fijo de PA por construccion de torre
MANT_UNITARIO = 0.1      # Mant: costo de mantenimiento en oro por soldado y por turno

# constantes del subsistema Diplomacia
TASA_TRIBUTO = 0.05      # % de los impuestos del vasallo que se pagan como tributo al protector

# constantes del subsistema Movimiento y Combate
ALPHA_ATAQUE = 1.0        # alpha_ataque: coeficiente base de efectividad ofensiva (Ecuacion 2.1)
ALPHA_DEFENSA = 1.2       # alpha_defensa: coeficiente base de efectividad defensiva (Ecuacion 2.1)
ALPHA_LETALIDAD = 0.10    # alpha: letalidad del poder ofensivo sobre el defensor (Ecuacion 2.4)
BETA_LETALIDAD = 0.08     # beta: letalidad del poder defensivo sobre el atacante (Ecuacion 2.4)
PHI_FORT = 0.5            # phi_fort: reduccion de bajas del defensor si esta fortificada (50% -> bajas a la mitad, Seccion 2.2)
X_MIN = 0.85              # niebla de guerra: X ~ U(X_MIN, X_MAX) (Seccion 2.3)
X_MAX = 1.15
MAX_RONDAS_COMBATE = 20   # tope de rondas de la Ley Cuadratica antes de declarar la batalla sin resolucion
C_PA_MOVIMIENTO = 1.0     # PA consumidos por cada orden de movimiento o ataque
C_ORO_FORT = 100.0        # costo en oro de fortificar una provincia (Seccion 2.2)
C_PA_FORT = 0.5           # costo en PA de fortificar una provincia
SAQUEO_BOTIN = 0.5        # % de la actividad comercial obtenido como botin al saquear (Evento E10)
DURACION_SAQUEO = 4        # turnos de inactividad de la provincia tras un saqueo (Seccion 4.6)
C_PA_SAQUEO = 1.0          # PA consumidos por ordenar un saqueo
FACTOR_TERRENO_ATAQUE = {"Plano": 1.0}    # theta_terreno,atacante: multiplicador por terreno del atacante (2.1)
FACTOR_TERRENO_DEFENSA = {"Plano": 1.0}   # theta_terreno,defensor: multiplicador por terreno del defensor (2.1)

# constantes del subsistema Puntos de Accion (dinamicos)
PA_BASE = 3.2                    # intercepto: PA maximo con 1 provincia
PA_COEF_PROVINCIAS = 0.45         # pendiente: PA extra por provincia
PA_RECUPERACION = 0.2             # PA que se recuperan por turno en paz
PA_PENALIDAD_ATAQUE = 0.5         # PA que se pierden por provincia atacada

# constantes del subsistema LEF (Parte 7) - prioridad logica de ejecucion dentro del mismo turno
PRIORIDAD_COMBATE = 1      # se ejecuta primero: resolver combates pendientes
PRIORIDAD_SAQUEO = 2       # despues de combate: ejecutar saqueos programados
PRIORIDAD_PRODUCCION = 3   # crecimiento poblacional y produccion de unidades
PRIORIDAD_ECONOMIA = 4     # recaudacion y gastos
PRIORIDAD_FELICIDAD = 5    # actualizacion de felicidad y evaluacion de rebelion

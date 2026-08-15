import numpy as np

# CONSTANTES DEL JUEGO (Parámetros fijos, ver Diccionario Formal)

P_MAX_POBLACION = 1_000_000   # P_max: población máxima que puede tener una provincia (punto 4.3)

# CLASE IMPERIO
# Representa al actor estratégico del juego (jugador o IA).
# Centraliza recursos económicos y la lista de provincias que posee.
# Corresponde al componente "Imperio" del Diccionario Formal 

class Imperio:
    def __init__(self, nombre, tesoro_inicial=1000.0):
        self.nombre = nombre                # Variable auxiliar: identificador para UI y diplomacia
        self.tesoro = tesoro_inicial         # Variable de estado: reserva monetaria (oro)
        self.deuda = 0.0                     # Variable de estado: monto adeudado acumulado

        self.puntos_accion_max = 5.0         # Parámetro (P): capacidad fija de PA por turno
        self.puntos_accion_actual = self.puntos_accion_max  # Estado (E): PA disponibles este turno

        self.provincias = []                 # Lista de objetos Provincia que pertenecen a este imperio
        self.unidades_totales = 0           

        # tasas fijadas por decreto del imperio (Ecuación 1.1, ya sin subíndice por provincia)
        self.tasa_impuesto = 10.0            # % (τ_imp), aplicado una vez al año
        self.tasa_impuesto_comercio = 5.0    # % (τ_com), aplicado cada turno

        self.ubicacion_rey = None            # Referencia a la Provincia donde reside el rey
        self.rey_capturado = False           # Variable de estado (E): True si el rey fue capturado

    def agregar_provincia(self, provincia):
        """Asigna una provincia a este imperio y actualiza la referencia inversa."""
        provincia.dueño = self
        self.provincias.append(provincia)

    def resetear_puntos_accion(self):
        self.puntos_accion_actual = self.puntos_accion_max

    def __repr__(self):
        return (f"Imperio({self.nombre}, tesoro={self.tesoro:.1f}, "
                f"PA={self.puntos_accion_actual}/{self.puntos_accion_max}, "
                f"provincias={len(self.provincias)})")



# CLASE PROVINCIA
# Unidad espacial que produce recursos, alberga población y estructuras.
# NOTA (Parte 1): se elimina la duplicidad "dueño"/"propietario" del
# código original; ahora solo existe self.dueño, que apunta al objeto
# Imperio propietario (o None si la provincia no tiene dueño todavía).
class Provincia:
    def __init__(self, id_prov, fila, columna, suelo, terreno):
        self.id = id_prov
        self.posicion = (fila, columna)

        # hay que generar estos parametros aleatoriamente pero ahora los dejo fijos para poder probar el juego
        self.suelo = suelo
        self.terreno = terreno
        self.clima = "Templado"

        self.dueño = None                    # Referencia al Imperio propietario 

        self.poblacion = 1000                # Variable de estado (personas). Tope: P_MAX_POBLACION 
        self.felicidad = 80.0                # Variable de estado, porcentaje 0-100
        self.fortificacion = False           # Variable de estado, booleana (efectividad 100%)
        self.tep = 0                         # Tiempo en Propiedad: turnos consecutivos bajo el mismo dueño
        self.torre_vigilancia = False        # Variable de estado, booleana
        self.u_prov = 0                      # Cantidad de soldados estacionados en esta provincia

        self.ac = 0.0                        # actividad_comercial: variable de flujo 
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
    print("==================================================\n")


def mostrar_mapa_por_dueño(mapa):
    """Imprime el tablero mostrando el imperio dueño de cada provincia (o '--' si no tiene)."""
    print("\n          === MAPA DEL JUEGO (POR IMPERIO) ===")
    for fila in mapa:
        linea = ""
        for provincia in fila:
            etiqueta = provincia.dueño.nombre[:3] if provincia.dueño else "---"
            linea += f"[ {etiqueta:^3} ] "
        print(linea)
    print("==================================================\n")


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
    ubicación inicial de su rey (mecánica de Colapso de Corona).
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


def main():
    # variables de control de la partida
    turno = 1
    limite_turnos = 20
    partida_terminada = False

    # variables de Tablero
    filas = 4
    columnas = 4
    mapa = crear_mapa(filas, columnas)

    # Creación de los imperios de prueba 
    imperio_jugador = Imperio("Jugador", tesoro_inicial=1000.0)
    imperio_ia = Imperio("IA", tesoro_inicial=1000.0)
    imperios = [imperio_jugador, imperio_ia]

    # Reparto inicial de provincias entre los dos imperios de prueba)
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
        turno += 1
        print("Avanzando al siguiente turno...")
    # inspeccionar_provincia(mapa, input("Ingrese el ID de la provincia a inspeccionar: "))
    print("\n=== FIN DE LA PARTIDA ===")


if __name__ == "__main__":
    main()
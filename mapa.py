import random
from modelos import Provincia


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
    """Imprime el tablero mostrando el imperio duenio de cada provincia (o '--' si no tiene)."""
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
    """Crea la matriz de provincias del tamano indicado."""
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
    Reparte el mapa entre los imperios de prueba dividiendolo por columnas
    (imperio 0 se queda con la mitad izquierda, imperio 1 con la mitad derecha).
    Ademas, asigna a cada imperio la primera provincia recibida como la
    ubicacion inicial de su rey.
    Es una asignacion provisional solo para poder probar el subsistema Economia
    en la Parte 2; el reparto real de inicio de partida lo vemos mas adelante lahian.
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

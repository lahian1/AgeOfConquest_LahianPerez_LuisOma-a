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


def _obtener_adyacentes(mapa, fila, columna):
    """Devuelve las posiciones ortogonales validas alrededor de (fila, columna)."""
    filas = len(mapa)
    columnas = len(mapa[0])
    adyacentes = []
    for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nf, nc = fila + df, columna + dc
        if 0 <= nf < filas and 0 <= nc < columnas:
            adyacentes.append((nf, nc))
    return adyacentes


def _obtener_adyacentes_con_diagonales(mapa, fila, columna):
    """Devuelve las 8 posiciones validas alrededor de (fila, columna) incluyendo diagonales."""
    filas = len(mapa)
    columnas = len(mapa[0])
    adyacentes = []
    for df in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if df == 0 and dc == 0:
                continue
            nf, nc = fila + df, columna + dc
            if 0 <= nf < filas and 0 <= nc < columnas:
                adyacentes.append((nf, nc))
    return adyacentes


def asignar_provincias_iniciales(mapa, imperios):
    """
    Asigna aleatoriamente una provincia inicial (provincia del rey) a cada imperio.
    La provincia del rey se elige al azar entre las casillas disponibles.
    Las casillas colindantes a una provincia ya elegida quedan inhabilitadas
    para los siguientes imperios. Se repite hasta que cada imperio tenga su
    provincia y su rey ubicado.
    Las provincias del rey obtienen poblacion=250000 y tropas=100.
    Las demas provincias vacias obtienen poblacion aleatoria entre 50000 y 250000.
    """
    filas = len(mapa)
    columnas = len(mapa[0])
    total = filas * columnas

    disponibles = set(range(total))
    inhabilitadas = set()

    for imperio in imperios:
        opciones = list(disponibles - inhabilitadas)
        elegido = random.choice(opciones)
        disponibles.discard(elegido)

        fila = elegido // columnas
        columna = elegido % columnas
        provincia = mapa[fila][columna]

        imperio.agregar_provincia(provincia)
        imperio.ubicacion_rey = provincia

        for af, ac in _obtener_adyacentes_con_diagonales(mapa, fila, columna):
            idx = af * columnas + ac
            if idx in disponibles:
                inhabilitadas.add(idx)

    # Asignar poblacion aleatoria a provincias vacias y stats iniciales al rey
    for fila in mapa:
        for provincia in fila:
            if provincia.dueño is not None:
                # Provincia del rey: poblacion y tropas fijas
                provincia.poblacion = 250000
                provincia.u_prov = 100
            else:
                # Provincia vacia: poblacion aleatoria
                provincia.poblacion = random.randint(50000, 250000)
                provincia.u_prov = 0

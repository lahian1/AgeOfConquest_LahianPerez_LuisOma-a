import numpy as np

#Clase Provincia que representa cada provincia en el mapa del juego
class Provincia:
    def __init__(self, id_prov, fila, columna, suelo, terreno):
        self.id = id_prov
        self.posicion = (fila, columna)
        self.dueño = None
        # hay que generar estos parametros aleatoriamente pero ahora los dejo fijos para poder probar el juego
        self.suelo = suelo
        self.terreno = terreno
        self.clima = "Templado"  
        
        self.propietario = None
        self.poblacion = 1000
        self.felicidad = 80.0
        self.fortificacion = False
        self.tep = 0
        self.torre_vigilancia = False
        self.u_prov = 0

        self.ac = 0.0
        self.imp_prov = 0.0
        self.saqueo = False
        self.decreto_f = False
        self.decreto_d = False
        self.venta = False
        self.precio_venta = 0
        self.comprador_v = None

def mostrar_mapa(mapa):
    print("\n          === MAPA DEL JUEGO (MATRIZ DE PROVINCIAS) ===")
    for fila in mapa:
        linea = ""
        for provincia in fila:
            linea += f"[ {provincia.id:02d} ] "
        print(linea)
    print("============================================\n")


def main():
    #varibles de control de la partida
    turno = 1
    limite_turnos = 20
    partida_terminada = False

    #varibles de Tablero
    filas = 10
    columnas = 10
    mapa = []
    id_provincia = 1


    for i in range(filas):
        fila = []
        for j in range(columnas):
            provincia = Provincia(id_provincia, i, j, "Tierra", "Plano")
            fila.append(provincia)
            id_provincia += 1
        mapa.append(fila)


    print("*************************************************")
    print("----INICIO DE LA PARTIDA----")
    print("*************************************************")
    
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
    inspeccionar_provincia(mapa, input("Ingrese el ID de la provincia a inspeccionar: ")) 
    print("\n=== FIN DE LA PARTIDA ===")


if __name__ == "__main__":
    main()

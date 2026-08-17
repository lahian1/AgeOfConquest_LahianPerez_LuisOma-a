import random

def definir_orden_turno(imperios):
    orden = list(imperios)
    random.shuffle(orden)
    return orden

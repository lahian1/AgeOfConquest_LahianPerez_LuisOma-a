# LEF: Lista de Eventos Futuros (Parte 7)
# Cola de prioridad que permite programar eventos para turnos futuros.
# La prioridad logica define el orden de ejecucion dentro del mismo turno.

from constantes import PRIORIDAD_COMBATE, PRIORIDAD_SAQUEO, PRIORIDAD_PRODUCCION, PRIORIDAD_ECONOMIA, PRIORIDAD_FELICIDAD


class LEF:
    """Cola de prioridad de eventos futuros. Cada evento tiene un turno objetivo,
    un tipo, datos asociados y una prioridad logica para ordenar dentro del mismo turno."""

    def __init__(self):
        self.eventos = []   # lista de dicts: {turno, prioridad, tipo, datos}

    def programar_evento(self, tipo, turno_objetivo, datos=None, prioridad=None):
        """Programa un evento para el turno indicado. Si no se pasa prioridad,
        se usa la prioridad por defecto del tipo de evento."""
        if prioridad is None:
            prioridad = _prioridad_por_tipo(tipo)
        evento = {
            "turno": turno_objetivo,
            "prioridad": prioridad,
            "tipo": tipo,
            "datos": datos or {},
        }
        self.eventos.append(evento)

    def extraer_eventos(self, turno_actual):
        """Devuelve todos los eventos programados para el turno actual,
        ordenados por prioridad (menor numero = mayor prioridad).
        Los eventos extraidos se eliminan de la cola."""
        pendientes = [e for e in self.eventos if e["turno"] == turno_actual]
        pendientes.sort(key=lambda e: e["prioridad"])
        self.eventos = [e for e in self.eventos if e["turno"] != turno_actual]
        return pendientes

    def hay_eventos(self, turno_actual):
        """Devuelve True si hay eventos pendientes para el turno indicado."""
        return any(e["turno"] == turno_actual for e in self.eventos)

    def __len__(self):
        return len(self.eventos)

    def __repr__(self):
        return f"LEF({len(self.eventos)} eventos pendientes)"


def _prioridad_por_tipo(tipo):
    """Asigna la prioridad logica segun el tipo de evento.
    Menor numero = se ejecuta primero dentro del mismo turno."""
    mapa = {
        "COMBATE": PRIORIDAD_COMBATE,
        "SAQUEO": PRIORIDAD_SAQUEO,
        "PRODUCCION": PRIORIDAD_PRODUCCION,
        "ECONOMIA": PRIORIDAD_ECONOMIA,
        "FELICIDAD": PRIORIDAD_FELICIDAD,
    }
    return mapa.get(tipo, 99)

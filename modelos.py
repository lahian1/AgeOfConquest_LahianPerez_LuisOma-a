# CLASES DEL MODELO: Imperio, Provincia, Diplomacia y helpers asociados.
# Estas clases son compartidas por todos los subsistemas del juego.


# CLASE IMPERIO

class Imperio:
    def __init__(self, nombre, tesoro_inicial=100.0):
        self.nombre = nombre                # Variable auxiliar: identificador para UI y diplomacia
        self.tesoro = tesoro_inicial         # Variable de estado: reserva monetaria (oro)

        self.tributos_recibidos = 0.0        # Flujo (F): tributos entrantes por vasallaje recibido (Parte 5)
        self.tributos_pagados = 0.0          # Flujo (F): tributos salientes por proteccion otorgada (Parte 5)


        self.puntos_accion_max = 3.2         # Parametro (P): capacidad maxima de PA (calculada por provincia)
        self.puntos_accion_actual = self.puntos_accion_max  # Estado (E): PA disponibles este turno

        self.provincias = []                 # Lista de objetos Provincia que pertenecen a este imperio
        self.unidades_totales = 0            # (subsistema Unidades)
        self.ordenes_movimiento = []         # Lista_Movimientos(t): ordenes encoladas durante el turno, se resuelven al cierre (Parte 6)

        # tasas fijadas por decreto del imperio Ecuacion 1.1
        self.tasa_impuesto = 5.0            # % (tau_imp), aplicado una vez al ano
        self.tasa_impuesto_comercio = 10.0    # % (tau_com), aplicado cada turno


        self.ubicacion_rey = None            # Referencia a la Provincia donde reside el rey
        self.rey_capturado = False           # Variable de estado (E): True si el rey fue capturado

    def agregar_provincia(self, provincia):
        """Asigna una provincia a este imperio y actualiza la referencia inversa."""
        provincia.dueño = self
        self.provincias.append(provincia)

    def recalcular_pa_maximo(self):
        """Recalcula el PA maximo segun la cantidad de provincias (formula lineal).
        PA_max = PA_BASE + (provincias * PA_COEF_PROVINCIAS)"""
        from constantes import PA_BASE, PA_COEF_PROVINCIAS
        self.puntos_accion_max = PA_BASE + len(self.provincias) * PA_COEF_PROVINCIAS

    def recuperar_puntos_accion(self, en_guerra):
        """Recupera PA al inicio de turno. Si esta en guerra, no recupera.
        Si esta en paz, recupera PA_RECUPERACION hasta el maximo."""
        from constantes import PA_RECUPERACION
        if not en_guerra:
            self.puntos_accion_actual = min(
                self.puntos_accion_max,
                self.puntos_accion_actual + PA_RECUPERACION
            )

    def __repr__(self):
        return (f"Imperio({self.nombre}, tesoro={self.tesoro:.1f}, "
                f"PA={self.puntos_accion_actual}/{self.puntos_accion_max}, "
                f"provincias={len(self.provincias)})")


# CLASE PROVINCIA
# Unidad espacial que produce recursos, alberga poblacion y estructuras.

class Provincia:
    def __init__(self, id_prov, fila, columna, suelo, terreno):
        self.id = id_prov
        self.posicion = (fila, columna)

        self.suelo = suelo
        self.terreno = terreno
        self.clima = "Templado"

        self.dueño = None                    # Referencia al Imperio propietario

        self.poblacion = 250000                # Variable de estado (personas). Tope: P_MAX_POBLACION (Seccion 4.3)
        self.felicidad = 80.0                # Variable de estado, porcentaje 0-100
        self.fortificacion = False           # Variable de estado, booleana (efectividad 100%, ver Ecuacion 2.2)
        self.tep = 0                         # Tiempo en Propiedad: turnos consecutivos bajo el mismo duenio
        self.torre_vigilancia = False        # Variable de estado, booleana
        self.u_prov = 100                      # Cantidad de soldados estacionados en esta provincia

        self.ac = 0.0                        # actividad_comercial: variable de flujo (Ecuacion 1.3)
        self.imp_prov = 0.0                  # impuestos generados por esta provincia en el turno actual
        self.turnos_saqueado = 0             # Variable de estado (E): turnos restantes de inactividad por saqueo (4.6)
        self.decreto_f = False               # Decreto_f: bono de felicidad (fertilidad)
        self.decreto_d = False               # Decreto_d: bono de poblacion (reparticion de oro)
        self.cooldown_fertilidad = 0         # turnos restantes de cooldown antes de volver a usar fertilidad
        self.venta = False
        self.precio_venta = 0
        self.comprador_v = None

        self.rebelion = False                  # Variable de estado (E): True si la provincia se rebelo este turno (Evento E20)
        self.bloqueada_baja_felicidad = False  # Variable de estado (E): True bloquea reclutar/construir (Seccion 4.2)

    def __repr__(self):
        duenio_nombre = self.dueño.nombre if self.dueño else "Sin duenio"
        return f"Provincia({self.id:02d}, duenio={duenio_nombre})"


# CLASE DIPLOMACIA

class Diplomacia:
    """Tabla de relaciones entre pares de imperios y de proteccion (vasallaje)."""

    PAZ = "paz"
    GUERRA = "guerra"
    ALIANZA = "alianza"
    ALTO_AL_FUEGO = "alto_al_fuego"

    def __init__(self):
        self.estados = {}       # (imperio_a, imperio_b) -> estado de relacion
        self.protecciones = {}  # protegido -> protector (vasallaje activo)

    @staticmethod
    def _clave(a, b):
        """Clave simetrica para la pareja de imperios (el orden no importa)."""
        return (a, b) if id(a) < id(b) else (b, a)

    def estado(self, a, b):
        """Devuelve el estado de relacion actual."""
        return self.estados.get(self._clave(a, b), self.PAZ)

    def _establecer(self, a, b, estado):
        self.estados[self._clave(a, b)] = estado

    def declarar_guerra(self, a, b):
        """Evento E7: pasa la relacion a guerra (si habia alianza, esta se rompe).
        Solo en guerra es legal atacar."""
        if self.estado(a, b) == self.GUERRA:
            return {"ok": False, "motivo": "ya estan en guerra"}
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
            return {"ok": False, "motivo": "ya estan en paz"}
        else:
            return {"ok": False, "motivo": "no estan en guerra; no tiene sentido proponer paz"}

    def formar_alianza(self, a, b):
        """Solo se puede firmar alianza desde el estado de paz."""
        if self.estado(a, b) != self.PAZ:
            return {"ok": False, "motivo": "solo se puede aliarse desde el estado de paz"}
        self._establecer(a, b, self.ALIANZA)
        return {"ok": True, "estado": self.ALIANZA}

    def romper_alianza(self, a, b):
        """Rompe la alianza activa (la relacion vuelve a paz)."""
        if self.estado(a, b) != self.ALIANZA:
            return {"ok": False, "motivo": "no hay alianza activa"}
        self._establecer(a, b, self.PAZ)
        return {"ok": True, "estado": self.PAZ}

    def proteger(self, protector, protegido):
        """Establece vasallaje: el imperio protegido paga tributo al protector."""
        if protegido is protector:
            return {"ok": False, "motivo": "un imperio no puede protegerse a si mismo"}
        if self.protecciones.get(protegido) == protector:
            return {"ok": False, "motivo": "ya existe esa proteccion"}
        self.protecciones[protegido] = protector
        return {"ok": True}

    def es_legal_atacar(self, a, b):
        """Regla de legalidad"""
        return self.estado(a, b) == self.GUERRA


# HELPERS

def buscar_rivales(imperios, imperio):
    """Devuelve la lista de todos los imperios que no son `imperio`."""
    return [o for o in imperios if o is not imperio]

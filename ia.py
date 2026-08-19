from constantes import C_ORO_TROPA, C_POB_TROPA, C_ORO_TORRE, C_ORO_FORT
from unidades import reclutar_soldados, construir_torre_vigilancia
from combat import ordenar_movimiento, fortificar_provincia, saquear


# ═══════════════════════════════════════════════════════════════════════
#  FUNCIONES DE APOYO
# ═══════════════════════════════════════════════════════════════════════

def _adyacentes(prov, mapa):
    filas, cols = len(mapa), len(mapa[0])
    f, c = prov.posicion
    resultado = []
    for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nf, nc = f + df, c + dc
        if 0 <= nf < filas and 0 <= nc < cols:
            resultado.append(mapa[nf][nc])
    return resultado


def _tiene_enemigos_cerca(imperio, mapa):
    for p in imperio.provincias:
        for a in _adyacentes(p, mapa):
            if a.dueño is not imperio and a.u_prov > 0:
                return True
    return False


def _provincias_vacias(imperio, mapa):
    vacias = []
    for p in imperio.provincias:
        for a in _adyacentes(p, mapa):
            if a.dueño is None and a not in vacias:
                vacias.append(a)
    return vacias


def _pares_enemigos(imperio, mapa):
    pares = []
    for p in imperio.provincias:
        for a in _adyacentes(p, mapa):
            if a.dueño is not imperio and a.dueño is not None and a.u_prov > 0:
                pares.append((p, a))
    return pares


def _en_guerra(imperio, diplomacia, imperios):
    for o in imperios:
        if o is not imperio and diplomacia.estado(imperio, o) == "guerra":
            return True
    return False


def _rivales(imperio, imperios):
    """Devuelve la lista de todos los imperios que no son `imperio`."""
    return [o for o in imperios if o is not imperio]


def _en_guerra_con(imperio, rival, diplomacia):
    """Devuelve True si imperio y rival estan en guerra."""
    return diplomacia.estado(imperio, rival) == "guerra"


def _calc_recluta(prov, imperio):
    max_oro = int(imperio.tesoro // C_ORO_TROPA)
    max_pob = int(prov.poblacion * 0.8 // C_POB_TROPA)
    return max(0, min(max_oro, max_pob))


# ═══════════════════════════════════════════════════════════════════════
#  CLASE IA_CPU
# ═══════════════════════════════════════════════════════════════════════

class IA_CPU:
    def __init__(self):
        self.acciones = []
        self._comprometidas = {}
        self._expandidos = set()
        self._origenes_usados = set()

    def planificar_turno(self, imperio, mapa, diplomacia, imperios):
        self.acciones.clear()
        self._comprometidas.clear()
        self._expandidos.clear()
        self._origenes_usados.clear()
        self._mapa = mapa
        self._dipl = diplomacia
        rivales = _rivales(imperio, imperios)
        expansiones = 0

        while imperio.puntos_accion_actual > 0:
            amenaza = _tiene_enemigos_cerca(imperio, mapa)
            vacias = _provincias_vacias(imperio, mapa)
            guerra = _en_guerra(imperio, diplomacia, imperios)
            pares = _pares_enemigos(imperio, mapa)

            # 1. Amenaza -> defender
            if amenaza and self._defender(imperio, mapa):
                continue

            # 2. En guerra con enemigos adyacentes -> atacar
            if guerra and pares and self._atacar(imperio, pares, rivales):
                continue

            # 3. Expandir (max 2 por turno)
            if vacias and expansiones < 2:
                if self._expandir(imperio, mapa, vacias):
                    expansiones += 1
                    continue

            # 4. Reclutar
            if self._reclutar(imperio):
                continue

            # 5. Diplomacia
            if self._decidir_diplomacia(imperio, mapa, rivales, diplomacia, guerra):
                continue

            # 6. Torre
            if self._torre(imperio):
                continue

            # 7. Saqueo si esta en guerra y sin oro
            if guerra and imperio.tesoro < 30 and self._saquear(imperio):
                continue

            break

    # ── Acciones simples ────────────────────────────────────────────

    def _defender(self, imperio, mapa):
        for p in imperio.provincias:
            if not p.fortificacion and imperio.tesoro >= C_ORO_FORT:
                for a in _adyacentes(p, mapa):
                    if a.dueño is not imperio and a.u_prov > 0:
                        return self._ejecutar("fortificar", imperio, p)
        return False

    def _atacar(self, imperio, pares, rivales):
        mejor = None
        mejor_dif = float("inf")
        reyes_rivales = {r.ubicacion_rey for r in rivales if r.ubicacion_rey}
        for prop, enem in pares:
            if enem in self._expandidos:
                continue
            if prop in self._origenes_usados:
                continue
            disp = self._disp(prop)
            if disp < 2:
                continue
            dif = enem.u_prov - disp
            if dif < mejor_dif:
                mejor_dif = dif
                mejor = (prop, enem)
        if mejor is None:
            return False
        origen, destino = mejor
        cant = self._disp(origen)
        if destino not in reyes_rivales:
            cant = max(2, cant // 2)
        resultado = self._ejecutar("mover", imperio, origen, destino, cant)
        if resultado:
            self._expandidos.add(destino)
        return resultado

    def _expandir(self, imperio, mapa, vacias):
        rey = imperio.ubicacion_rey
        if rey is None:
            return False
        mejor = None
        mejor_dist = float("inf")
        for v in vacias:
            if v in self._expandidos:
                continue
            d = abs(v.posicion[0] - rey.posicion[0]) + abs(v.posicion[1] - rey.posicion[1])
            if d < mejor_dist:
                mejor_dist = d
                mejor = v
        if mejor is None:
            return False
        origen = None
        max_tropas = 0
        for p in imperio.provincias:
            disp = self._disp(p)
            if (disp > max_tropas
                    and p is not mejor
                    and p not in self._origenes_usados
                    and mejor in _adyacentes(p, mapa)):
                max_tropas = disp
                origen = p
        if origen is None or max_tropas <= 0:
            return False
        cant = max(1, max_tropas // 2)
        resultado = self._ejecutar("mover", imperio, origen, mejor, cant)
        if resultado:
            self._expandidos.add(mejor)
        return resultado

    def _reclutar(self, imperio):
        mejor = None
        max_pob = 0
        for p in imperio.provincias:
            if not p.bloqueada_baja_felicidad and p.turnos_saqueado == 0:
                if p.poblacion > max_pob:
                    max_pob = p.poblacion
                    mejor = p
        if mejor is None:
            return False
        cant = _calc_recluta(mejor, imperio)
        if cant <= 0:
            return False
        return self._ejecutar("reclutar", imperio, mejor, cant)

    def _decidir_diplomacia(self, imperio, mapa, rivales, diplomacia, guerra):
        if not rivales:
            return False
        fuerza = sum(p.u_prov for p in imperio.provincias)
        if guerra:
            for rival in rivales:
                if _en_guerra_con(imperio, rival, diplomacia):
                    fuerza_r = sum(p.u_prov for p in rival.provincias)
                    if fuerza < fuerza_r:
                        return self._ejecutar("paz", imperio, rival)
            return False
        for rival in rivales:
            pares_con_rival = [(p, e) for p, e in _pares_enemigos(imperio, mapa) if e.dueño is rival]
            if pares_con_rival and fuerza >= 20 and imperio.tesoro >= 200:
                return self._ejecutar("guerra", imperio, rival)
        return False

    def _torre(self, imperio):
        for p in imperio.provincias:
            if not p.torre_vigilancia and not p.bloqueada_baja_felicidad:
                if imperio.tesoro >= C_ORO_TORRE:
                    return self._ejecutar("torre", imperio, p)
        return False

    def _saquear(self, imperio):
        mejor = None
        max_ac = 0
        for p in imperio.provincias:
            if p.turnos_saqueado == 0 and not p.bloqueada_baja_felicidad:
                if p.ac > max_ac:
                    max_ac = p.ac
                    mejor = p
        if mejor is None or mejor.ac <= 0:
            return False
        return self._ejecutar("saquear", imperio, mejor)

    # ── Helpers ─────────────────────────────────────────────────────

    def _disp(self, p):
        return max(0, p.u_prov - self._comprometidas.get(p, 0))

    def _registrar(self, txt):
        self.acciones.append(txt)
        return True

    def _ejecutar(self, tipo, imperio, *args):
        match tipo:
            case "fortificar":
                res = fortificar_provincia(imperio, args[0])
                if res["ok"]:
                    return self._registrar(f"Fortificar P{args[0].id:02d}")

            case "reclutar":
                res = reclutar_soldados(imperio, args[0], args[1])
                if res["ok"]:
                    return self._registrar(f"Reclutar {res['cantidad']} en P{args[0].id:02d}")

            case "mover":
                o, d, c = args[0], args[1], args[2]
                if c > self._disp(o):
                    return False
                if o in self._origenes_usados:
                    return False
                res = ordenar_movimiento(self._mapa, self._dipl, imperio, o, d, c)
                if res["ok"]:
                    self._comprometidas[o] = self._comprometidas.get(o, 0) + c
                    self._origenes_usados.add(o)
                    return self._registrar(f"Mover {c} de P{o.id:02d} a P{d.id:02d}")

            case "torre":
                res = construir_torre_vigilancia(imperio, args[0])
                if res["ok"]:
                    return self._registrar(f"Torre en P{args[0].id:02d}")

            case "guerra":
                if imperio.puntos_accion_actual < 1.0:
                    return False
                res = self._dipl.declarar_guerra(imperio, args[0])
                if res["ok"]:
                    imperio.puntos_accion_actual -= 1.0
                    return self._registrar(f"Guerra a {args[0].nombre}")

            case "paz":
                if imperio.puntos_accion_actual < 1.0:
                    return False
                res = self._dipl.proponer_paz(imperio, args[0])
                if res["ok"]:
                    imperio.puntos_accion_actual -= 1.0
                    return self._registrar(f"Paz con {args[0].nombre}")

            case "vasallaje":
                res = self._dipl.proteger(imperio, args[0])
                if res["ok"]:
                    return self._registrar(f"Vasallaje: {args[0].nombre} paga tributo")

            case "saquear":
                res = saquear(imperio, args[0])
                if res["ok"]:
                    imperio.puntos_accion_actual -= 1.0
                    return self._registrar(f"Saquear P{args[0].id:02d}")

        return False

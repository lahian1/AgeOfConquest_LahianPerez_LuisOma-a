import random
from constantes import (
    ALPHA_ATAQUE, ALPHA_DEFENSA, ALPHA_LETALIDAD, BETA_LETALIDAD,
    PHI_FORT, X_MIN, X_MAX, MAX_RONDAS_COMBATE,
    C_PA_MOVIMIENTO, C_ORO_FORT, C_PA_FORT, SAQUEO_BOTIN,
    SAQUEO_PENALIDAD_FELICIDAD, DURACION_SAQUEO, C_PA_SAQUEO,
    FACTOR_TERRENO_ATAQUE, FACTOR_TERRENO_DEFENSA,
)


def generar_x_aleatoria():
    """Seccion 2.3: X = 0.85 + u * (1.15 - 0.85), con u ~ U(0,1). Es la variable
    aleatoria de "niebla de guerra", generada independiente para cada bando y ronda."""
    return X_MIN + random.random() * (X_MAX - X_MIN)


def provincias_vecinas(mapa, provincia):
    """Devuelve las provincias adyacentes a `provincia` (4 direcciones: arriba,
    abajo, izquierda y derecha dentro de la matriz)."""
    filas = len(mapa)
    columnas = len(mapa[0])
    fila, col = provincia.posicion
    vecinas = []
    for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nf, nc = fila + df, col + dc
        if 0 <= nf < filas and 0 <= nc < columnas:
            vecinas.append(mapa[nf][nc])
    return vecinas


def resolver_combate(cant_atacante, cant_defensor, provincia,
                     terreno_atacante=1.0, terreno_defensor=1.0):
    """Seccion 2 completa."""
    a = float(cant_atacante)
    d = float(cant_defensor)
    fort = PHI_FORT if provincia.fortificacion else 0.0
    registro = []
    ronda = 0
    while a > 0 and d > 0 and ronda < MAX_RONDAS_COMBATE:
        ronda += 1
        x_a = generar_x_aleatoria()
        x_d = generar_x_aleatoria()
        pe_atacante = a * ALPHA_ATAQUE * terreno_atacante * x_a
        pe_defensor = d * ALPHA_DEFENSA * terreno_defensor * x_d
        bajas_atacante = BETA_LETALIDAD * pe_defensor
        bajas_defensor = ALPHA_LETALIDAD * pe_atacante * (1.0 - fort)
        a = max(0.0, a - bajas_atacante)
        d = max(0.0, d - bajas_defensor)
        registro.append({
            "ronda": ronda, "x_a": x_a, "x_d": x_d,
            "pe_atacante": pe_atacante, "pe_defensor": pe_defensor,
            "bajas_atacante": bajas_atacante, "bajas_defensor": bajas_defensor,
            "a": a, "d": d,
        })

    # Seccion 2.5: determinacion del resultado
    if d == 0 and a > 0:
        resultado = "VICTORIA_ATACANTE"      # E9: conquista de provincia
    elif a == 0 and d > 0:
        resultado = "VICTORIA_DEFENSOR"      # el atacante se repliega
    elif a == 0 and d == 0:
        resultado = "EMPATE"
    else:
        resultado = "SIN_RESOLUCION"         # se agotaron las rondas sin vencedor

    return {
        "resultado": resultado,
        "atacantes_supervivientes": int(round(a)),
        "defensores_supervivientes": int(round(d)),
        "rondas": registro,
    }


def atacar(mapa, imperio_atacante, imperio_defensor, origen, destino, cantidad):
    """Resuelve el ataque a una provincia enemiga (Eventos E7-E9, Seccion 2).
    Aplica el recuento de bajas y, si gana el atacante, conquista la provincia
    (E9). En caso de derrota o empate, los supervivientes del atacante se
    repliegan al origen. Devuelve el reporte del combate."""
    defensores = destino.u_prov
    terreno_atacante = FACTOR_TERRENO_ATAQUE.get(origen.terreno, 1.0)
    terreno_defensor = FACTOR_TERRENO_DEFENSA.get(destino.terreno, 1.0)

    reporte = resolver_combate(cantidad, defensores, destino,
                               terreno_atacante, terreno_defensor)

    # Bajas del atacante: salen todas las tropas; si no hay conquista vuelven las vivas
    imperio_atacante.unidades_totales -= cantidad
    origen.u_prov -= cantidad

    # Bajas del defensor
    imperio_defensor.unidades_totales -= defensores
    destino.u_prov = 0

    reporte["conquistada"] = False
    reporte["rey_capturado"] = False
    reporte["imperio_perdedor"] = None
    if reporte["resultado"] == "VICTORIA_ATACANTE":
        reporte["conquistada"] = True
        # E9: la provincia cambia de duenio y recibe a los supervivientes del atacante
        imperio_atacante.unidades_totales += reporte["atacantes_supervivientes"]
        destino.u_prov = reporte["atacantes_supervivientes"]
        destino.tep = 0
        imperio_defensor.provincias.remove(destino)
        imperio_atacante.agregar_provincia(destino)

        # Seccion 4.5 - Colapso de Corona: si se conquista la provincia del rey,
        # el rey queda capturado y todas las provincias restantes pasan al atacante.
        if destino is imperio_defensor.ubicacion_rey:
            reporte["rey_capturado"] = True
            reporte["imperio_perdedor"] = imperio_defensor
            imperio_defensor.rey_capturado = True
            provincias_restantes = list(imperio_defensor.provincias)
            for prov in provincias_restantes:
                imperio_defensor.provincias.remove(prov)
                prov.u_prov = 0
                prov.tep = 0
                imperio_atacante.agregar_provincia(prov)
            imperio_atacante.unidades_totales += imperio_defensor.unidades_totales
            imperio_defensor.unidades_totales = 0
    else:
        # El atacante se repliega y el defensor conserva la provincia con sus vivos
        imperio_atacante.unidades_totales += reporte["atacantes_supervivientes"]
        origen.u_prov += reporte["atacantes_supervivientes"]
        imperio_defensor.unidades_totales += reporte["defensores_supervivientes"]
        destino.u_prov = reporte["defensores_supervivientes"]

    reporte["ok"] = True
    reporte["tipo"] = "combate"
    reporte["origen"] = origen.id
    reporte["destino"] = destino.id
    reporte["atacantes_iniciales"] = cantidad
    reporte["defensores_iniciales"] = defensores
    return reporte


def ordenar_movimiento(mapa, diplomacia, imperio, origen, destino, cantidad):
    """Encola una orden de movimiento/ataque para el cierre del turno (la
    "Lista_Movimientos(t)" del pseudocodigo Cierre_De_Turno). Solo valida y
    consume los PA en este momento; el traslado o el combate se resuelven en
    resolver_ordenes_movimiento cuando el turno cierra."""
    if origen.dueño is not imperio:
        return {"ok": False, "tipo": "error", "motivo": "la provincia de origen no es tuya"}
    if destino not in provincias_vecinas(mapa, origen):
        return {"ok": False, "tipo": "error", "motivo": "las provincias no son vecinas"}
    if cantidad <= 0:
        return {"ok": False, "tipo": "error", "motivo": "la cantidad debe ser positiva"}
    if cantidad > origen.u_prov:
        return {"ok": False, "tipo": "error",
                "motivo": f"solo hay {origen.u_prov} soldados en la provincia de origen"}
    if imperio.puntos_accion_actual < C_PA_MOVIMIENTO:
        return {"ok": False, "tipo": "error", "motivo": "puntos de accion insuficientes"}

    # Destino enemigo: solo se puede ordenar el ataque estando en guerra
    if destino.dueño is not imperio and destino.dueño is not None:
        if not diplomacia.es_legal_atacar(imperio, destino.dueño):
            return {"ok": False, "tipo": "error",
                    "motivo": f"no se puede atacar a {destino.dueño.nombre}: solo se ataca en guerra"}

    imperio.puntos_accion_actual -= C_PA_MOVIMIENTO
    imperio.ordenes_movimiento.append({
        "origen": origen,
        "destino": destino,
        "cantidad": cantidad,
    })
    return {"ok": True, "tipo": "orden",
            "mensaje": f"orden encolada: {cantidad} tropas de P{origen.id:02d} a P{destino.id:02d} "
                       f"(se resolvera al cierre del turno)"}


def resolver_ordenes_movimiento(mapa, diplomacia, imperios):
    """Pseudocodigo paso 1 del Cierre_De_Turno: resuelve las ordenes de movimiento
    de todos los imperios una por una."""
    for imperio in imperios:
        while imperio.ordenes_movimiento:
            orden = imperio.ordenes_movimiento.pop(0)
            origen, destino, cantidad = orden["origen"], orden["destino"], orden["cantidad"]

            # Revalidacion en el momento de ejecutar la orden
            if origen.dueño is not imperio:
                print(f"  [!] Orden cancelada: P{origen.id:02d} ya no es de {imperio.nombre}")
                continue
            if cantidad > origen.u_prov:
                print(f"  [!] Orden cancelada: quedan solo {origen.u_prov} tropas en P{origen.id:02d}")
                continue
            if destino not in provincias_vecinas(mapa, origen):
                print(f"  [!] Orden cancelada: P{origen.id:02d} y P{destino.id:02d} ya no son vecinas")
                continue

            # Destino enemigo: requiere guerra vigente -> combate
            if destino.dueño is not imperio and destino.dueño is not None:
                if not diplomacia.es_legal_atacar(imperio, destino.dueño):
                    print(f"  [!] Orden cancelada: ya no se puede atacar a P{destino.id:02d} "
                          f"(no hay guerra con {destino.dueño.nombre})")
                    continue
                reporte = atacar(mapa, imperio, destino.dueño, origen, destino, cantidad)
                mostrar_reporte_combate(reporte)
                continue

            if destino.dueño is None:
                # Destino libre: se conquista sin combate
                origen.u_prov -= cantidad
                destino.u_prov += cantidad
                destino.dueño = imperio
                imperio.agregar_provincia(destino)
                print(f"  Tropas movidas de P{origen.id:02d} a P{destino.id:02d} ({cantidad} soldados) "
                      f"-> provincia conquistada (E9)")
                continue

            # Destino propio: desplazamiento simple
            origen.u_prov -= cantidad
            destino.u_prov += cantidad
            print(f"  Tropas movidas de P{origen.id:02d} a P{destino.id:02d} ({cantidad} soldados)")


def fortificar_provincia(imperio, provincia):
    """Seccion 2.2: construye la fortificacion de la provincia (una sola vez).
    La fortificacion reduce a la mitad las bajas del defensor (phi_fort = 50%, Ecuacion 2.4)."""
    if provincia.dueño is not imperio:
        return {"ok": False, "motivo": "la provincia no pertenece a este imperio"}
    if provincia.bloqueada_baja_felicidad:
        return {"ok": False, "motivo": "provincia bloqueada por baja felicidad (Seccion 4.2)"}
    if provincia.fortificacion:
        return {"ok": False, "motivo": "la provincia ya esta fortificada"}
    if imperio.tesoro < C_ORO_FORT:
        return {"ok": False, "motivo": f"tesoro insuficiente (se necesitan {C_ORO_FORT:.1f} oro)"}
    if imperio.puntos_accion_actual < C_PA_FORT:
        return {"ok": False, "motivo": "puntos de accion insuficientes"}

    imperio.tesoro -= C_ORO_FORT
    imperio.puntos_accion_actual -= C_PA_FORT
    provincia.fortificacion = True
    return {"ok": True, "costo_oro": C_ORO_FORT, "costo_pa": C_PA_FORT}


def saquear(imperio, provincia):
    """Valida si se puede ordenar un saqueo a una provincia propia (Evento E10).
    La provincia no puede estar ya saqueada, y el imperio debe tener PA suficiente.
    No aplica efectos aqui: los ejecuta la LEF en el turno programado.
    Devuelve el resultado o motivo de rechazo."""
    if provincia.turnos_saqueado > 0:
        return {"ok": False, "motivo": f"la provincia ya esta saqueada (quedan {provincia.turnos_saqueado} turnos)"}
    if imperio.puntos_accion_actual < C_PA_SAQUEO:
        return {"ok": False, "motivo": "puntos de accion insuficientes"}
    return {"ok": True}


def mostrar_reporte_combate(reporte):
    """Imprime el detalle de rondas y el resultado de un combate ya resuelto."""
    print(f"  Combate en P{reporte['destino']:02d}: {reporte['atacantes_iniciales']} atacantes "
          f"vs {reporte['defensores_iniciales']} defensores")

    if reporte["resultado"] == "VICTORIA_ATACANTE":
        print(f"  -> VICTORIA DEL ATACANTE (E9): provincia conquistada, "
              f"sobreviven {reporte['atacantes_supervivientes']} atacantes")
        if reporte.get("rey_capturado"):
            perdedor = reporte["imperio_perdedor"]
            print(f"  -> CAPTURA DEL REY (4.5): el rey de {perdedor.nombre} fue capturado, "
                  f"todas sus provincias pasan al atacante")
            print(f"  >>> {perdedor.nombre} HA SIDO DERROTADO <<<")
    elif reporte["resultado"] == "VICTORIA_DEFENSOR":
        print(f"  -> VICTORIA DEL DEFENSOR: el atacante se repliega, "
              f"sobreviven {reporte['defensores_supervivientes']} defensores")
    else:
        print(f"  -> {reporte['resultado']}: la provincia no cambia de duenio")

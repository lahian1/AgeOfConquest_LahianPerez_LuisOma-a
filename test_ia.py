import sys
import os

# Ocultar stdin para que msvcrt no bloquee
sys.stdin = open(os.devnull, 'r')

from modelos import Imperio, Diplomacia
from mapa import crear_mapa, asignar_provincias_iniciales, mostrar_mapa_por_dueño
from ia import IA_CPU
from turno import cierre_de_turno
from lef import LEF

def test_ia():
    turno = 1
    limite = 10

    mapa = crear_mapa(4, 4)
    jugador = Imperio("Jugador", 1000.0)
    ia_imperio = Imperio("IA", 1000.0)
    imperios = [jugador, ia_imperio]
    diplomacia = Diplomacia()
    lef = LEF()
    ia_cpu = IA_CPU()

    asignar_provincias_iniciales(mapa, imperios)

    print("=" * 60)
    print("  TEST IA - SIMULACION DE 10 TURNOS")
    print("=" * 60)
    mostrar_mapa_por_dueño(mapa)
    for imp in imperios:
        rey = imp.ubicacion_rey.id if imp.ubicacion_rey else "?"
        print(f"  {imp.nombre}: oro={imp.tesoro:.0f} PA={imp.puntos_accion_actual:.0f} "
              f"provs={len(imp.provincias)} tropas={imp.unidades_totales} rey=P{rey}")
    print()

    while turno <= limite:
        print(f"\n{'='*60}")
        print(f"  TURNO {turno}")
        print(f"{'='*60}")

        ia_cpu.planificar_turno(ia_imperio, mapa, diplomacia, imperios)

        if ia_cpu.acciones:
            print(f"  [IA acciones]:")
            for a in ia_cpu.acciones:
                print(f"    - {a}")
        else:
            print(f"  [IA]: sin acciones este turno")

        print(f"\n  --- Cierre de turno {turno} ---")
        cierre_de_turno(turno, imperios, mapa, diplomacia, lef)

        print(f"\n  Estado despues del turno {turno}:")
        for imp in imperios:
            rey = imp.ubicacion_rey.id if imp.ubicacion_rey else "CAPTURADO"
            print(f"    {imp.nombre}: oro={imp.tesoro:.0f} PA={imp.puntos_accion_actual:.0f} "
                  f"provs={len(imp.provincias)} tropas={imp.unidades_totales} rey=P{rey}")
            for p in imp.provincias:
                print(f"      P{p.id:02d}: pob={p.poblacion:.0f} fel={p.felicidad:.1f} "
                      f"sold={p.u_prov} fort={p.fortificacion} torre={p.torre_vigilancia}")

        if ia_imperio.rey_capturado:
            print(f"\n  >>> IA DERROTADA - rey capturado en turno {turno}")
            break
        if jugador.rey_capturado:
            print(f"\n  >>> JUGADOR DERROTADO - rey capturado en turno {turno}")
            break
        if not ia_imperio.provincias:
            print(f"\n  >>> IA SIN PROVINCIAS en turno {turno}")
            break
        if not jugador.provincias:
            print(f"\n  >>> JUGADOR SIN PROVINCIAS en turno {turno}")
            break

        turno += 1

    print(f"\n{'='*60}")
    print("  ESTADO FINAL DEL MAPA")
    print(f"{'='*60}")
    mostrar_mapa_por_dueño(mapa)

if __name__ == "__main__":
    test_ia()

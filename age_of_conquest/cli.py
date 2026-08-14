from .model import GameState


def run_cli() -> None:
    game = GameState.default_game()

    print("=== Age of Conquest IV (Interfaz simple) ===")
    while True:
        print("\n" + game.status())
        print("\nOpciones: 1) Atacar  2) Reforzar  3) Terminar turno  4) Salir")
        option = input("Selecciona una opción: ").strip()

        try:
            if option == "1":
                from_t = input("Territorio origen: ").strip()
                to_t = input("Territorio destino: ").strip()
                armies = int(input("Ejércitos que atacan: ").strip())
                captured = game.attack(from_t, to_t, armies)
                print("Territorio conquistado." if captured else "Ataque repelido.")
            elif option == "2":
                territory = input("Territorio a reforzar: ").strip()
                armies = int(input("Ejércitos a agregar: ").strip())
                game.reinforce(territory, armies)
                print("Refuerzo aplicado.")
            elif option == "3":
                game.end_turn()
                print("Turno finalizado.")
            elif option == "4":
                print("Juego finalizado.")
                break
            else:
                print("Opción no válida.")
        except ValueError as error:
            print(f"Error: {error}")

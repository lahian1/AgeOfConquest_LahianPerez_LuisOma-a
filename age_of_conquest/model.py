from dataclasses import dataclass


@dataclass
class Territory:
    name: str
    owner: str
    armies: int


class GameState:
    def __init__(self, players: list[str], territories: dict[str, Territory], current_player_index: int = 0, turn_number: int = 1):
        if len(players) < 2:
            raise ValueError("El juego requiere al menos 2 jugadores.")
        if not territories:
            raise ValueError("Debe existir al menos un territorio.")
        self.players = players
        self.territories = territories
        self.current_player_index = current_player_index
        self.turn_number = turn_number

    @classmethod
    def default_game(cls) -> "GameState":
        players = ["Jugador 1", "Jugador 2"]
        territories = {
            "A": Territory("A", "Jugador 1", 5),
            "B": Territory("B", "Jugador 1", 3),
            "C": Territory("C", "Jugador 2", 5),
            "D": Territory("D", "Jugador 2", 3),
        }
        return cls(players, territories)

    @property
    def current_player(self) -> str:
        return self.players[self.current_player_index]

    def reinforce(self, territory_name: str, armies: int) -> None:
        territory = self._get_territory(territory_name)
        if territory.owner != self.current_player:
            raise ValueError("Solo puedes reforzar territorios propios.")
        if armies <= 0:
            raise ValueError("Los ejércitos a reforzar deben ser mayores que cero.")
        territory.armies += armies

    def attack(self, from_territory: str, to_territory: str, attacking_armies: int) -> bool:
        source = self._get_territory(from_territory)
        target = self._get_territory(to_territory)

        if source.owner != self.current_player:
            raise ValueError("Solo puedes atacar desde territorios propios.")
        if target.owner == self.current_player:
            raise ValueError("No puedes atacar territorios propios.")
        if attacking_armies <= 0:
            raise ValueError("El ataque debe usar al menos 1 ejército.")
        if source.armies <= attacking_armies:
            raise ValueError("Debes dejar al menos 1 ejército en el territorio origen.")

        source.armies -= attacking_armies
        if attacking_armies > target.armies:
            target.owner = self.current_player
            target.armies = attacking_armies - target.armies
            return True

        target.armies -= attacking_armies
        return False

    def end_turn(self) -> None:
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.turn_number += 1

    def status(self) -> str:
        lines = [f"Turno: {self.turn_number}", f"Jugador actual: {self.current_player}", "Territorios:"]
        for territory in self.territories.values():
            lines.append(f"- {territory.name}: {territory.owner} ({territory.armies})")
        return "\n".join(lines)

    def _get_territory(self, territory_name: str) -> Territory:
        territory = self.territories.get(territory_name)
        if territory is None:
            raise ValueError(f"Territorio inexistente: {territory_name}")
        return territory

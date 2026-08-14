import unittest

from age_of_conquest.model import GameState


class GameStateTest(unittest.TestCase):
    def test_default_game_has_two_players(self):
        game = GameState.default_game()

        self.assertEqual(["Jugador 1", "Jugador 2"], game.players)
        self.assertEqual("Jugador 1", game.current_player)
        self.assertEqual(4, len(game.territories))

    def test_successful_attack_captures_territory(self):
        game = GameState.default_game()
        game.territories["A"].armies = 6
        game.territories["C"].armies = 2

        captured = game.attack("A", "C", 3)

        self.assertTrue(captured)
        self.assertEqual("Jugador 1", game.territories["C"].owner)
        self.assertEqual(1, game.territories["C"].armies)
        self.assertEqual(3, game.territories["A"].armies)

    def test_failed_attack_reduces_defender_armies(self):
        game = GameState.default_game()

        captured = game.attack("A", "C", 2)

        self.assertFalse(captured)
        self.assertEqual("Jugador 2", game.territories["C"].owner)
        self.assertEqual(3, game.territories["C"].armies)
        self.assertEqual(3, game.territories["A"].armies)

    def test_end_turn_changes_current_player(self):
        game = GameState.default_game()

        game.end_turn()

        self.assertEqual("Jugador 2", game.current_player)
        self.assertEqual(2, game.turn_number)


if __name__ == "__main__":
    unittest.main()

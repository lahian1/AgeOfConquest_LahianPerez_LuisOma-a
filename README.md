# AgeOfConquest_LahianPerez_LuisOma-a
Implementación del Modelo Operacional del juego Age of conquest IV.

## Estructura
- `age_of_conquest/model.py`: backend del modelo operacional (jugadores, territorios, atacar, reforzar, turno).
- `age_of_conquest/cli.py`: interfaz simple por consola.
- `main.py`: punto de entrada de la aplicación.
- `tests/test_model.py`: pruebas unitarias del modelo.

## Ejecutar interfaz simple
```bash
python main.py
```

## Ejecutar pruebas
```bash
python -m unittest discover -s tests -v
```

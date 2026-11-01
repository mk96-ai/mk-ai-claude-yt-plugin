"""Punto de entrada del plugin mk-yt. Solo biblioteca estandar: se lanza con cualquier Python 3.10+.

  python mkyt.py setup [funcion...] [--cpu] [--models-from <carpeta>]   prepara el equipo (una vez)
  python mkyt.py doctor [funcion...]                                    comprueba que todo esta listo
  python mkyt.py features                                               lista las funciones y sus ordenes
  python mkyt.py <funcion> <orden> [argumentos]                         ejecuta una orden de una funcion
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mkyt_core.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Ponto de entrada do executável (o PyInstaller precisa de um script, não de `python -m`)."""
import sys

from legenday.app import main

if __name__ == "__main__":
    sys.exit(main())

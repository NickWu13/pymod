"""The DSL front-end package."""
from .parser import parse_source, Program

__all__ = ["parse_source", "Program"]
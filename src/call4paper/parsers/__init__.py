"""Parsers module for different publishers."""

from .base import BaseParser
from .elsevier import ElsevierParser
from .springer import SpringerParser
from .ieee import IEEEParser
from .wiley import WileyParser
from .generic import GenericParser

__all__ = [
    "BaseParser",
    "ElsevierParser",
    "SpringerParser",
    "IEEEParser",
    "WileyParser",
    "GenericParser",
]

"""Parsers module for different publishers."""

from .base import BaseParser
from .elsevier import ElsevierParser
from .nature import NatureParser
from .springer import SpringerParser
from .ieee import IEEEParser
from .wiley import WileyParser
from .generic import GenericParser

__all__ = [
    "BaseParser",
    "ElsevierParser",
    "NatureParser",
    "SpringerParser",
    "IEEEParser",
    "WileyParser",
    "GenericParser",
]

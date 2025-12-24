"""Primitive version representation for Ubiquiti mFi mPower integration."""

from __future__ import annotations

from typing import NamedTuple


class Version(NamedTuple):
    major: int
    minor: int

    def __str__(self):
        return f"{self.major}.{self.minor}"

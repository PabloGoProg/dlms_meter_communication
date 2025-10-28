# models/enums.py
from enum import Enum


class Medium(str, Enum):
    TCP = "TCP"
    SERIAL = "SERIAL"


class Profile(str, Enum):
    WRAPPER = "WRAPPER"
    HDLC_TUNNELING = "HDLC_TUNNELING"


class Auth(str, Enum):
    NONE = "NONE"
    LLS = "LLS"
    HLS = "HLS"


class Phase(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    TOTAL = "TOTAL"
    NEUTRAL = "NEUTRAL"
    NONE = "NONE"


class Direction(str, Enum):
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    NONE = "NONE"


class Quantity(str, Enum):
    ENERGY_ACTIVE = "ENERGY_ACTIVE"
    ENERGY_REACTIVE = "ENERGY_REACTIVE"
    POWER_ACTIVE = "POWER_ACTIVE"
    POWER_REACTIVE = "POWER_REACTIVE"
    VOLTAGE = "VOLTAGE"
    CURRENT = "CURRENT"
    POWER_FACTOR = "POWER_FACTOR"

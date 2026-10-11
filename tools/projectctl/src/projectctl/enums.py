from enum import StrEnum


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class ScopeClass(StrEnum):
    F0 = "F0"
    F1 = "F1"
    R1 = "R1"
    R2 = "R2"
    S = "S"
    X = "X"

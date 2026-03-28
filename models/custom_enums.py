from enum import IntEnum

class SymptomLikelihood(IntEnum):
    ABSENT     = 0
    UNLIKELY   = 1
    NEUTRAL    = 2
    LIKELY     = 3
    CONFIRMED  = 4
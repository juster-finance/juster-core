from decimal import ROUND_DOWN
from decimal import Context
from decimal import Decimal


def quantize(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        Decimal(1),
        context=Context(rounding=ROUND_DOWN)
    )


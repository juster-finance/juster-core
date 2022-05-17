from models.pool import PoolModel
from copy import deepcopy
from unittest import TestCase
from decimal import Decimal


class PoolModelTestCase(TestCase):
    def test_should_fail_to_cmp_different_models_after_copy(self):
        model = PoolModel()
        model_copy = deepcopy(model)
        self.assertEqual(model_copy, model)
        model_copy.default(Decimal(1_000_000))
        self.assertNotEqual(model_copy, model)


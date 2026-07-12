import unittest

from wizard_avatar.expressions import get_expression
from wizard_avatar.layers import render_wizard_local
from wizard_avatar.models import EXPRESSIONS, WizardState


class ExpressionTests(unittest.TestCase):
    def test_all_expressions_are_defined(self):
        for expression in EXPRESSIONS:
            self.assertIn("mouth", get_expression(expression))

    def test_expression_changes_stay_near_face(self):
        base = WizardState(time_seconds=1.0, expression="neutral")
        happy = WizardState(time_seconds=1.0, expression="happy")
        neutral_canvas = render_wizard_local(base)
        happy_canvas = render_wizard_local(happy)
        changed = []
        for y in range(neutral_canvas.height):
            for x in range(neutral_canvas.width):
                if neutral_canvas.get(x, y) != happy_canvas.get(x, y):
                    changed.append((x, y))
        self.assertTrue(changed)
        self.assertTrue(all(14 <= y <= 25 for _x, y in changed))


if __name__ == "__main__":
    unittest.main()

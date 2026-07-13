import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource


class VisualContractTests(unittest.TestCase):
    def _is_visible_avatar_cell(self, rgb):
        return min(rgb) < 185 or (max(rgb) - min(rgb) > 35 and min(rgb) < 245)

    def _character_bounds(self, frame):
        xs = []
        ys = []
        for cell_index in range(0, len(frame.cells), 4):
            if frame.cells[cell_index] == 32:
                continue
            color = tuple(frame.cells[cell_index + 1 : cell_index + 4])
            if self._is_visible_avatar_cell(color):
                grid_index = cell_index // 4
                xs.append(grid_index % frame.cols)
                ys.append(grid_index // frame.cols)
        return min(xs), min(ys), max(xs), max(ys)

    def test_frame_contains_reference_png_color_families(self):
        source = ProceduralWizardFrameSource()
        frame = source.render_next_frame()
        colors = [
            tuple(frame.cells[i + 1 : i + 4])
            for i in range(0, len(frame.cells), 4)
            if frame.cells[i] != 32
        ]

        def count_where(predicate):
            return sum(1 for color in colors if predicate(*color))

        self.assertGreater(count_where(lambda r, g, b: b > 120 and b > r + 25 and b >= g - 10), 800)
        self.assertGreater(count_where(lambda r, g, b: r > 210 and g > 155 and b < 100), 120)
        self.assertGreater(count_where(lambda r, g, b: r > 150 and b > 90 and g < 120), 80)
        self.assertGreater(count_where(lambda r, g, b: r > 80 and 35 < g < 145 and b < 90), 400)
        self.assertGreater(count_where(lambda r, g, b: r > 200 and g < 110 and b < 100), 100)
        self.assertGreater(count_where(lambda r, g, b: g > 130 and r < 120 and b < 130), 80)
        self.assertGreater(count_where(lambda r, g, b: r > 190 and 105 < g < 190 and 60 < b < 150), 100)

    def test_default_avatar_has_readable_browser_footprint(self):
        source = ProceduralWizardFrameSource()
        frame = source.render_next_frame()
        min_x, min_y, max_x, max_y = self._character_bounds(frame)
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        self.assertGreaterEqual(width, 80)
        self.assertGreaterEqual(height, 100)
        self.assertGreaterEqual(min_y, 15)
        self.assertLessEqual(max_y, frame.rows - 6)

    def test_reference_avatar_uses_fixed_white_background_with_faint_floor(self):
        source = ProceduralWizardFrameSource()
        frame = source.render_next_frame()
        upper_sample_index = (10 * frame.cols + 10) * 4
        self.assertEqual(frame.cells[upper_sample_index], 32)
        self.assertEqual(tuple(frame.cells[upper_sample_index + 1 : upper_sample_index + 4]), (255, 255, 255))

        floor_sample_index = (100 * frame.cols + 10) * 4
        floor_rgb = tuple(frame.cells[floor_sample_index + 1 : floor_sample_index + 4])
        self.assertGreaterEqual(min(floor_rgb), 235)


if __name__ == "__main__":
    unittest.main()

"""Configuration boundaries and compatibility of production layouts."""
import unittest
from src.renderer.layout import layout_config


class ProductionLayoutTests(unittest.TestCase):
    def test_preserved_layouts(self):
        fixed = layout_config('fixed')
        self.assertEqual((fixed['BOARD_SIZE'], fixed['BOARD_X'], fixed['BOARD_Y']), (960, 60, 180))
        self.assertEqual(fixed, layout_config('fixed', 'crop'))
        safe = layout_config('off')
        self.assertEqual((safe['BOARD_SIZE'], safe['BOARD_X'], safe['BOARD_Y']), (808, 136, 556))
        self.assertEqual((safe['VIEWPORT_WIDTH'], safe['VIEWPORT_HEIGHT']), (1032, 1640))

    def test_crop_and_invalid_options(self):
        crop = layout_config('off', 'crop')
        self.assertEqual((crop['BOARD_SIZE'], crop['BOARD_X'], crop['BOARD_Y']), (1440, -180, 240))
        self.assertEqual((crop['VIEWPORT_WIDTH'], crop['VIEWPORT_HEIGHT']), (1080, 1800))
        for meme, layout in [('piece', 'safe'), ('off', 'unknown'), ('fixed', 'unknown')]:
            with self.assertRaises(ValueError):
                layout_config(meme, layout)


if __name__ == '__main__':
    unittest.main()

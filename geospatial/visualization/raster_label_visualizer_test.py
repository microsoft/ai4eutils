"""Tests for geospatial.visualization.raster_label_visualizer."""


import unittest

from geospatial.visualization.raster_label_visualizer import RasterLabelVisualizer


class TestRasterLabelVisualizer(unittest.TestCase):

    def setUp(self):
        test_label_map = {
            # serialized JSON object has to have str keys
            'num_to_name': {
                "1": "Urban and infrastructure",
                "2": "Agriculture",
                "3": "Arboreal and forestry crops",
                "4": "Pasture",
                "5": "Vegetation",
                "6": "Forest",
                "7": "Savanna",
                "8": "Sand, rocks and bare land",
                "9": "Unavailable",
                "10": "Swamp",
                "11": "Water",
                "12": "Seasonal savanna",
                "13": "Seasonally flooded savanna",
                "0": "Empty of data"
            },
            'num_to_color': {
                "0": "black",
                "1": "lightgray",
                "2": "pink",
                "3": "teal",
                "4": "salmon",
                "5": "goldenrod",
                "6": "darkseagreen",
                "7": "gold",
                "8": "blanchedalmond",
                "9": "whitesmoke",
                "10": "darkolivegreen",
                "11": "deepskyblue",
                "12": "khaki",
                "13": "thistle"
            }
        }
        self.visualizer = RasterLabelVisualizer(test_label_map)

    def tearDown(self):
        pass

    def test_uint8_rgb_to_hex(self):
        hex_str = RasterLabelVisualizer.uint8_rgb_to_hex(0, 100, 255)
        self.assertEqual(hex_str.upper(), '#0064FF')


if __name__ == '__main__':
    unittest.main()

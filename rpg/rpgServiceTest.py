import unittest

from rpg.rpgService import RpgService


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.rpg_service = RpgService()

    def test_get_equipment_string(self):
        result = self.rpg_service.get_equipment_string([1, 2])
        self.assertEqual(result, 'Rusty Iron Sword, Steel Longsword')  # add assertion here




if __name__ == '__main__':
    unittest.main()

import json
import os
from config import COLORS, STARTING_GOLD


class RpgService:

    def __init__(self):
        self.data_file = 'data/rpg/rpg.json'
        self.equipment_file = 'data/rpg/equipment.json'
        self.users = self.__load_users()

    def __load_users(self):
        """Load user rpg data from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def __save_users(self):
        """Save user rpg data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)


    def load_equipment_data(self):
        """Load equipment data from JSON file"""
        if not os.path.exists('data/rpg'):
            os.makedirs('data/rpg')

        if os.path.exists(self.equipment_file):
            try:
                with open(self.equipment_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}



    def get_equipment_string(self, equipment_array):
        equipmentData = self.load_equipment_data()
        first = True
        equipment_string = ''
        for equipment in equipment_array:
            if not first: equipment_string += ', '

            equipment_string += equipmentData[str(equipment)]['name']
            first = False
        return equipment_string

    def get_user_data(self, user_id):
        """Get or create user data"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'gold': STARTING_GOLD,
                'hp': 100,
                'level':1,
                'mp': 10,
                'equipment': [1, 2],
            }

            self.__save_users()
        return self.users[user_id]



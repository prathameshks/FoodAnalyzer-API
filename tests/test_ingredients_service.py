import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from services.ingredients import get_ingredient_data, save_ingredient_data, filter_ingredients_by_preferences

class TestIngredientService(unittest.TestCase):

    @patch('services.ingredients.get_ingredient_by_name')
    @patch('services.ingredients.fetch_ingredient_data_from_api')
    @patch('services.ingredients.save_ingredient_data')
    def test_get_ingredient_data(self, mock_save_ingredient_data, mock_fetch_ingredient_data_from_api, mock_get_ingredient_by_name):
        db = MagicMock(spec=Session)
        mock_get_ingredient_by_name.return_value = None
        mock_fetch_ingredient_data_from_api.return_value = {"name": "test_ingredient", "nutritional_info": "test_info"}

        result = get_ingredient_data(db, "test_ingredient")

        mock_get_ingredient_by_name.assert_called_once_with(db, "test_ingredient")
        mock_fetch_ingredient_data_from_api.assert_called_once_with("test_ingredient")
        mock_save_ingredient_data.assert_called_once_with(db, "test_ingredient", {"name": "test_ingredient", "nutritional_info": "test_info"})
        self.assertEqual(result, {"name": "test_ingredient", "nutritional_info": "test_info"})

    def test_save_ingredient_data(self):
        db = MagicMock(spec=Session)
        name = "test_ingredient"
        data = {"name": "test_ingredient", "nutritional_info": "test_info"}

        save_ingredient_data(db, name, data)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_filter_ingredients_by_preferences(self):
        ingredients = [
            {"text": "ingredient1", "sugar": 10, "fat": 5, "allergens": ["allergen1"]},
            {"text": "ingredient2", "sugar": 3, "fat": 2, "allergens": []},
            {"text": "ingredient3", "sugar": 6, "fat": 1, "allergens": ["allergen2"]}
        ]
        preferences = {
            "low_sugar": True,
            "low_fat": True,
            "allergens": ["allergen1"]
        }

        result = filter_ingredients_by_preferences(ingredients, preferences)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "ingredient2")

if __name__ == '__main__':
    unittest.main()

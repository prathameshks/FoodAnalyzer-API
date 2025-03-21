import unittest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from services.analysis_agent import analyze_ingredients, provide_personalized_recommendations
from models.user_preferences import UserPreferences
from models.ingredient import Ingredient

class TestAnalysisAgentService(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.user_id = 1
        self.ingredients = [
            {"text": "sugar"},
            {"text": "salt"},
            {"text": "flour"}
        ]
        self.preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions="low sugar",
            allergens="",
            preferred_ingredients="",
            disliked_ingredients=""
        )
        self.db.query.return_value.filter.return_value.first.return_value = self.preferences

    def test_analyze_ingredients(self):
        self.db.query.return_value.filter.return_value.first.return_value = self.preferences
        self.db.query.return_value.all.return_value = [
            Ingredient(name="sugar", nutritional_info={"calories": 100}),
            Ingredient(name="salt", nutritional_info={"sodium": 200}),
            Ingredient(name="flour", nutritional_info={"carbs": 300})
        ]

        result = analyze_ingredients(self.db, self.ingredients, self.user_id)

        self.assertIn("safe_ingredients", result)
        self.assertIn("unsafe_ingredients", result)
        self.assertIn("additional_facts", result)
        self.assertEqual(len(result["safe_ingredients"]), 2)
        self.assertEqual(len(result["unsafe_ingredients"]), 1)

    def test_provide_personalized_recommendations(self):
        self.db.query.return_value.all.return_value = [
            Ingredient(name="sugar", nutritional_info={"calories": 100}),
            Ingredient(name="salt", nutritional_info={"sodium": 200}),
            Ingredient(name="flour", nutritional_info={"carbs": 300})
        ]

        result = provide_personalized_recommendations(self.db, self.user_id)

        self.assertIn("recommended_ingredients", result)
        self.assertEqual(len(result["recommended_ingredients"]), 3)

if __name__ == "__main__":
    unittest.main()

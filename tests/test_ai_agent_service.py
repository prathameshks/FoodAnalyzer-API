import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from services.ai_agent import preprocess_data, validate_data, clean_data, standardize_data, enrich_data, process_data, integrate_hugging_face_transformers
from models.product import Product
from models.ingredient import Ingredient

class TestAIAgentService(unittest.TestCase):

    @patch('services.ai_agent.fetch_product_data_from_api')
    def test_preprocess_data(self, mock_fetch_product_data_from_api):
        mock_fetch_product_data_from_api.return_value = {
            'product': {
                'product_name_en': 'Test Product',
                'generic_name_en': 'Test Generic',
                'brands': 'Test Brand',
                'ingredients': [
                    {
                        'text': 'Test Ingredient',
                        'percent': 50,
                        'vegan': 'yes',
                        'vegetarian': 'yes',
                        'ingredients': [
                            {
                                'text': 'Sub Ingredient',
                                'percent': 25,
                                'vegan': 'yes',
                                'vegetarian': 'yes'
                            }
                        ]
                    }
                ],
                'ingredients_text_en': 'Test Ingredients Text',
                'ingredients_analysis': {},
                'nutriscore': {},
                'nutrient_levels': {},
                'nutriments': {},
                'data_quality_warnings_tags': []
            }
        }
        result = preprocess_data('test_barcode')
        self.assertEqual(result['product_name'], 'Test Product')
        self.assertEqual(result['generic_name'], 'Test Generic')
        self.assertEqual(result['brands'], 'Test Brand')
        self.assertEqual(result['ingredients'][0]['text'], 'Test Ingredient')
        self.assertEqual(result['ingredients'][0]['sub_ingredients'][0]['text'], 'Sub Ingredient')

    def test_validate_data(self):
        valid_data = {
            'product_name': 'Test Product',
            'generic_name': 'Test Generic',
            'brands': 'Test Brand',
            'ingredients': [],
            'nutriscore': {},
            'nutrient_levels': {},
            'nutriments': {}
        }
        invalid_data = {
            'product_name': '',
            'generic_name': '',
            'brands': '',
            'ingredients': [],
            'nutriscore': {},
            'nutrient_levels': {},
            'nutriments': {}
        }
        self.assertTrue(validate_data(valid_data))
        self.assertFalse(validate_data(invalid_data))

    def test_clean_data(self):
        data = {
            'ingredients': [
                {
                    'text': 'Test Ingredient',
                    'percent': 'N/A',
                    'sub_ingredients': [
                        {
                            'text': 'Sub Ingredient',
                            'percent': 'N/A'
                        }
                    ]
                }
            ]
        }
        cleaned_data = clean_data(data)
        self.assertEqual(cleaned_data['ingredients'][0]['percent'], 0)
        self.assertEqual(cleaned_data['ingredients'][0]['sub_ingredients'][0]['percent'], 0)

    def test_standardize_data(self):
        data = {
            'ingredients': [
                {
                    'text': 'Test Ingredient',
                    'sub_ingredients': [
                        {
                            'text': 'Sub Ingredient'
                        }
                    ]
                }
            ]
        }
        standardized_data = standardize_data(data)
        self.assertEqual(standardized_data['ingredients'][0]['text'], 'test ingredient')
        self.assertEqual(standardized_data['ingredients'][0]['sub_ingredients'][0]['text'], 'sub ingredient')

    @patch('services.ai_agent.get_ingredient_by_name')
    @patch('services.ai_agent.fetch_product_data_from_api')
    @patch('services.ai_agent.save_ingredient_data')
    def test_enrich_data(self, mock_save_ingredient_data, mock_fetch_product_data_from_api, mock_get_ingredient_by_name):
        db = MagicMock(spec=Session)
        data = {
            'ingredients': [
                {
                    'text': 'Test Ingredient',
                    'sub_ingredients': []
                }
            ]
        }
        mock_get_ingredient_by_name.return_value = None
        mock_fetch_product_data_from_api.return_value = {'nutritional_info': 'Test Info'}
        enriched_data = enrich_data(db, data)
        self.assertEqual(enriched_data['ingredients'][0]['nutritional_info'], {'nutritional_info': 'Test Info'})
        mock_save_ingredient_data.assert_called_once_with(db, 'Test Ingredient', {'nutritional_info': 'Test Info'})

    @patch('services.ai_agent.preprocess_data')
    @patch('services.ai_agent.validate_data')
    @patch('services.ai_agent.clean_data')
    @patch('services.ai_agent.standardize_data')
    @patch('services.ai_agent.enrich_data')
    @patch('services.ai_agent.save_json_file')
    def test_process_data(self, mock_save_json_file, mock_enrich_data, mock_standardize_data, mock_clean_data, mock_validate_data, mock_preprocess_data):
        db = MagicMock(spec=Session)
        mock_preprocess_data.return_value = {'product_name': 'Test Product'}
        mock_validate_data.return_value = True
        mock_clean_data.return_value = {'product_name': 'Test Product'}
        mock_standardize_data.return_value = {'product_name': 'Test Product'}
        mock_enrich_data.return_value = {'product_name': 'Test Product'}
        result = process_data(db, 'test_barcode')
        self.assertEqual(result['product_name'], 'Test Product')
        mock_save_json_file.assert_called_once_with('test_barcode', {'product_name': 'Test Product'})

    @patch('services.ai_agent.pipeline')
    def test_integrate_hugging_face_transformers(self, mock_pipeline):
        mock_pipeline.return_value = lambda text: [{'sequence': 'Test sequence'}]
        result = integrate_hugging_face_transformers('test_model', 'Test text')
        self.assertEqual(result, 'Test sequence')

    @patch('services.ai_agent.get_ingredient_by_name')
    @patch('services.ai_agent.fetch_ingredient_data_from_api')
    @patch('services.ai_agent.save_ingredient_data')
    def test_process_data_saves_ingredient_details(self, mock_save_ingredient_data, mock_fetch_ingredient_data_from_api, mock_get_ingredient_by_name):
        db = MagicMock(spec=Session)
        mock_get_ingredient_by_name.return_value = None
        mock_fetch_ingredient_data_from_api.return_value = {'nutritional_info': 'Test Info'}
        data = {
            'product_name': 'Test Product',
            'generic_name': 'Test Generic',
            'brands': 'Test Brand',
            'ingredients': [
                {
                    'text': 'Test Ingredient',
                    'sub_ingredients': []
                }
            ],
            'ingredients_text': 'Test Ingredients Text',
            'ingredients_analysis': {},
            'nutriscore': {},
            'nutrient_levels': {},
            'nutriments': {},
            'data_quality_warnings': []
        }
        with patch('services.ai_agent.preprocess_data', return_value=data), \
             patch('services.ai_agent.validate_data', return_value=True), \
             patch('services.ai_agent.clean_data', return_value=data), \
             patch('services.ai_agent.standardize_data', return_value=data), \
             patch('services.ai_agent.enrich_data', return_value=data):
            result = process_data(db, 'test_barcode')
            self.assertEqual(result['product_name'], 'Test Product')
            mock_save_ingredient_data.assert_called_once_with(db, 'Test Ingredient', {'nutritional_info': 'Test Info'})

    @patch('services.ai_agent.preprocess_data')
    @patch('services.ai_agent.validate_data')
    @patch('services.ai_agent.clean_data')
    @patch('services.ai_agent.standardize_data')
    @patch('services.ai_agent.enrich_data')
    @patch('services.ai_agent.save_json_file')
    def test_process_data_saves_product_details(self, mock_save_json_file, mock_enrich_data, mock_standardize_data, mock_clean_data, mock_validate_data, mock_preprocess_data):
        db = MagicMock(spec=Session)
        mock_preprocess_data.return_value = {'product_name': 'Test Product'}
        mock_validate_data.return_value = True
        mock_clean_data.return_value = {'product_name': 'Test Product'}
        mock_standardize_data.return_value = {'product_name': 'Test Product'}
        mock_enrich_data.return_value = {'product_name': 'Test Product'}
        result = process_data(db, 'test_barcode')
        self.assertEqual(result['product_name'], 'Test Product')
        mock_save_json_file.assert_called_once_with('test_barcode', {'product_name': 'Test Product'})
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

if __name__ == '__main__':
    unittest.main()

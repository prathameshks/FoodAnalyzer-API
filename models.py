from pydantic import BaseModel

class ProductInfo(BaseModel):
    product_name: str
    generic_name: str
    brands: str
    ingredients: list
    ingredients_text: str
    ingredients_analysis: dict
    nutriscore: dict
    nutrient_levels: dict
    nutriments: dict
    data_quality_warnings: list

class Barcodes(BaseModel):
    barcodes: dict

class ProductData(BaseModel):
    product: dict
from sqlalchemy.orm import Session
from typing import Optional
from db.models import Product

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def add_product(self, name: str, ingredients_text: str) -> Product:
        product = Product(product_name=name, ingredients_text=ingredients_text)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

from sqlalchemy.orm import Session
from typing import Optional
from db.models import Product
from interfaces.productModels import ProductCreate

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def add_product(self, product_create: ProductCreate) -> Product:
        product = Product(**product_create.model_dump())
        
        self.db.add(product)        
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

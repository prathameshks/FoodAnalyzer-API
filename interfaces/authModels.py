from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True  # This enables ORM mode
        
        
class TokenData(BaseModel):
    email: str | None = None
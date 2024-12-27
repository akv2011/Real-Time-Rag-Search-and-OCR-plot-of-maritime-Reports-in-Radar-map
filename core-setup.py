# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    MODEL_NAME: str
    TESSERACT_CMD: str
    SPEECH_LANGUAGE: str
    PREDICTION_WINDOW_HOURS: int
    HISTORICAL_DATA_RETENTION_DAYS: int
    
    class Config:
        env_file = ".env"

# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import Settings

settings = Settings()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# app/models/database.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_type = Column(String(50))
    identifier = Column(String(100))
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50))
    
    positions = relationship("Position", back_populates="contact")
    alerts = relationship("Alert", back_populates="contact")

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    heading = Column(Float)
    speed = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("Contact", back_populates="positions")

# app/schemas/contact.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ContactBase(BaseModel):
    contact_type: str
    identifier: str
    status: str

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    first_detected: datetime
    last_updated: datetime

    class Config:
        from_attributes = True

# app/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..database import SessionLocal
from ..config import Settings

settings = Settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from passlib.hash import bcrypt
from database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(200), nullable=True)

    # back-reference to bids
    bids = relationship("Bid", back_populates="item")
        # ─── New fields for auction mode ────────────────────
    auction_live     = Column(Boolean, default=False, nullable=False)
    youtube_channel  = Column(String(100), nullable=True)   # e.g. UC_xxx...
    fallback_image   = Column(String(200), nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # back-references
    bids = relationship("Bid", back_populates="user")
    messages = relationship("Message", back_populates="sender")

    def set_password(self, raw_password: str):
        """Hash & store a new password."""
        self.password = bcrypt.hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """Check given password against stored hash."""
        return bcrypt.verify(raw_password, self.password)


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    user = relationship("User", back_populates="bids")
    item = relationship("Item", back_populates="bids")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String(100), index=True)         # e.g. "auction_5" or "chat_2_7"
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationship
    sender = relationship("User", back_populates="messages")

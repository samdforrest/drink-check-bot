#database models/schema
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    total_credits = Column(Integer, default=0)
    
    # Relationships
    drink_checks = relationship("DrinkCheck", back_populates="user")
    credits = relationship("Credit", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', total_credits={self.total_credits})>"

class DrinkCheck(Base):
    __tablename__ = 'drink_checks'

    message_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_reply = Column(Boolean, default=False)
    replied_to_message_id = Column(BigInteger, nullable=True)
    chain_id = Column(Integer, ForeignKey('active_chains.chain_id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="drink_checks")
    credits = relationship("Credit", back_populates="drink_check")
    chain = relationship("ActiveChain", back_populates="drink_checks")

    def __repr__(self):
        return f"<DrinkCheck(message_id={self.message_id}, user_id={self.user_id}, is_reply={self.is_reply})>"

class Credit(Base):
    __tablename__ = 'credits'

    credit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    message_id = Column(BigInteger, ForeignKey('drink_checks.message_id'))
    credit_type = Column(String(50))  # 'initial' or 'chain'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="credits")
    drink_check = relationship("DrinkCheck", back_populates="credits")

    def __repr__(self):
        return f"<Credit(credit_id={self.credit_id}, user_id={self.user_id}, credit_type='{self.credit_type}')>"

class ActiveChain(Base):
    __tablename__ = 'active_chains'

    chain_id = Column(Integer, primary_key=True, autoincrement=True)
    starter_id = Column(BigInteger, ForeignKey('users.user_id'))  # User who started the chain
    start_message_id = Column(BigInteger, unique=True)  # First message in chain
    last_message_id = Column(BigInteger)  # Most recent message in chain
    last_message_author_id = Column(BigInteger)  # Author of the last message
    start_time = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)  # Last non-self-reply activity
    is_active = Column(Boolean, default=True)
    
    # Relationships
    drink_checks = relationship("DrinkCheck", back_populates="chain")

    def __repr__(self):
        return f"<ActiveChain(chain_id={self.chain_id}, starter_id={self.starter_id}, is_active={self.is_active})>"

    def is_expired(self):
        """Check if chain has expired (30 minutes without activity)"""
        if not self.is_active:
            return True
        
        now = datetime.utcnow()
        time_diff = now - self.last_activity
        return time_diff.total_seconds() >= 1800  # 30 minutes in seconds
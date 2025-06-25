#database models/schema
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, create_engine, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import pytz
import enum

Base = declarative_base()

# Set up Central timezone
central = pytz.timezone('America/Chicago')

class CreditType(enum.Enum):
    initial = 'initial'
    chain = 'chain'

class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    total_credits = Column(Integer, default=0)
    longest_chain_participation = Column(Integer, default=0)  # Longest chain they were part of
    
    # Relationships
    drink_checks = relationship("DrinkCheck", back_populates="user")
    credits = relationship("Credit", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', total_credits={self.total_credits})>"

class DrinkCheck(Base):
    __tablename__ = 'drink_checks'

    message_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    chain_id = Column(Integer, ForeignKey('active_chains.chain_id'), nullable=True)
    is_reply = Column(Boolean, default=False)
    replied_to_message_id = Column(BigInteger, nullable=True)
    timestamp = Column(DateTime(timezone=True))
    
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
    credit_type = Column(SQLEnum(CreditType))
    timestamp = Column(DateTime(timezone=True))
    
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
    last_message_author_id = Column(BigInteger, ForeignKey('users.user_id'))
    start_time = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    unique_participants_count = Column(Integer, default=1)  # Count of unique participants
    participant_ids = Column(String(1000), default='')  # Comma-separated list of participant IDs
    is_server_record = Column(Boolean, default=False)  # Whether this chain set a server record
    
    # Relationships
    drink_checks = relationship("DrinkCheck", back_populates="chain")

    def __repr__(self):
        return f"<ActiveChain(chain_id={self.chain_id}, starter_id={self.starter_id}, is_active={self.is_active})>"

    def is_expired(self):
        """Check if the chain has expired (30 minutes of inactivity)"""
        if not self.last_activity:
            return True
            
        # Get current time in UTC since our timestamps are in UTC
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        # Convert last_activity to UTC for comparison (if it's not already)
        last_activity_utc = self.last_activity.replace(tzinfo=pytz.UTC) if self.last_activity.tzinfo is None else self.last_activity
        
        # Chain expires after 30 minutes of inactivity
        return (now - last_activity_utc) > timedelta(minutes=30)

    def get_participants(self) -> set:
        """Get set of participant IDs"""
        return set(int(id) for id in self.participant_ids.split(',') if id)

    def add_participant(self, user_id: int) -> bool:
        """Add a participant to the chain. Returns True if this is a new participant."""
        participants = self.get_participants()
        if user_id not in participants:
            participants.add(user_id)
            self.participant_ids = ','.join(str(id) for id in participants)
            self.unique_participants_count = len(participants)
            return True
        return False
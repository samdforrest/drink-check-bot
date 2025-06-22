from database.models import User, DrinkCheck, Credit, ActiveChain
from database.connection import DatabaseSession
from sqlalchemy import inspect
from datetime import datetime

def check_tables():
    print("Checking database tables and contents...")
    with DatabaseSession() as db:
        # Get inspector
        inspector = inspect(db.get_bind())
        
        # List all tables
        print("\nExisting tables:")
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")
        
        # Check Users table
        print("\nUsers in database:")
        users = db.query(User).all()
        for user in users:
            print(f"User ID: {user.user_id}, Username: {user.username}, Total Credits: {user.total_credits}")
        
        # Check DrinkChecks table
        print("\nDrink Checks in database:")
        drink_checks = db.query(DrinkCheck).all()
        for dc in drink_checks:
            print(f"Message ID: {dc.message_id}, User ID: {dc.user_id}, Is Reply: {dc.is_reply}")
        
        # Check Credits table
        print("\nCredits in database:")
        credits = db.query(Credit).all()
        for credit in credits:
            print(f"Credit ID: {credit.credit_id}, User ID: {credit.user_id}, Type: {credit.credit_type}")

        # Check Active Chains
        print("\nActive Chains:")
        active_chains = db.query(ActiveChain).filter_by(is_active=True).all()
        for chain in active_chains:
            now = datetime.utcnow()
            time_diff = now - chain.last_activity
            minutes_left = 30 - (time_diff.total_seconds() / 60)
            
            print(f"Chain ID: {chain.chain_id}")
            print(f"Started by: {chain.starter_id}")
            print(f"Last activity: {chain.last_activity}")
            print(f"Minutes until expiry: {minutes_left:.1f}")
            print(f"Is expired: {chain.is_expired()}")
            print("---")

if __name__ == "__main__":
    check_tables() 
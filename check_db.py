from database.models import User, DrinkCheck, Credit, ActiveChain
from database.connection import DatabaseSession
from sqlalchemy import inspect
from datetime import datetime
import pytz

# Set up Central timezone
central = pytz.timezone('America/Chicago')

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
            # Convert UTC timestamp to Central Time for display
            ct_time = dc.timestamp.astimezone(central) if dc.timestamp else "No timestamp"
            print(f"Message ID: {dc.message_id}, User ID: {dc.user_id}, Time (CT): {ct_time}, Is Reply: {dc.is_reply}")
        
        # Check Credits table
        print("\nCredits in database:")
        credits = db.query(Credit).all()
        for credit in credits:
            # Convert UTC timestamp to Central Time for display
            ct_time = credit.timestamp.astimezone(central) if credit.timestamp else "No timestamp"
            print(f"Credit ID: {credit.credit_id}, User ID: {credit.user_id}, Type: {credit.credit_type}, Time (CT): {ct_time}")

        # Check Active Chains
        print("\nActive Chains:")
        active_chains = db.query(ActiveChain).filter_by(is_active=True).all()
        for chain in active_chains:
            # Get current time in UTC since our timestamps are in UTC
            now = datetime.utcnow().replace(tzinfo=pytz.UTC)
            
            # Convert chain timestamps to Central Time for display
            start_time_ct = chain.start_time.astimezone(central) if chain.start_time else "No start time"
            last_activity_ct = chain.last_activity.astimezone(central) if chain.last_activity else "No activity"
            
            # Calculate time difference
            if chain.last_activity:
                last_activity_utc = chain.last_activity.replace(tzinfo=pytz.UTC) if chain.last_activity.tzinfo is None else chain.last_activity
                time_diff = now - last_activity_utc
                minutes_left = 30 - (time_diff.total_seconds() / 60)
            else:
                minutes_left = 0
            
            print(f"Chain ID: {chain.chain_id}")
            print(f"Started by: {chain.starter_id}")
            print(f"Start time (CT): {start_time_ct}")
            print(f"Last activity (CT): {last_activity_ct}")
            print(f"Minutes until expiry: {minutes_left:.1f}")
            print(f"Is expired: {chain.is_expired()}")
            print("---")

if __name__ == "__main__":
    check_tables() 
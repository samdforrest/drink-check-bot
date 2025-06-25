"""
Migration script to update the database to use the new streak system.
Run this script once after updating the code.
"""

from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Update database to use the new streak system."""
    try:
        # Create engine
        engine = create_engine('sqlite:///drink_check.db')
        
        with engine.connect() as conn:
            # Rename old columns in users table
            conn.execute(text("""
                ALTER TABLE users 
                RENAME COLUMN longest_chain_participation TO longest_chain_streak;
            """))
            
            # Update active_chains table
            conn.execute(text("""
                ALTER TABLE active_chains 
                ADD COLUMN total_messages INTEGER DEFAULT 1;
            """))
            
            # Drop old columns from active_chains
            conn.execute(text("""
                ALTER TABLE active_chains 
                DROP COLUMN unique_participants_count;
            """))
            
            conn.execute(text("""
                ALTER TABLE active_chains 
                DROP COLUMN participant_ids;
            """))
            
            # Update existing chains to count total messages
            conn.execute(text("""
                UPDATE active_chains
                SET total_messages = (
                    SELECT COUNT(*)
                    FROM drink_checks
                    WHERE drink_checks.chain_id = active_chains.chain_id
                );
            """))
            
            # Update user streaks based on their participation in chains
            conn.execute(text("""
                UPDATE users
                SET longest_chain_streak = (
                    SELECT MAX(total_messages)
                    FROM active_chains ac
                    JOIN drink_checks dc ON dc.chain_id = ac.chain_id
                    WHERE dc.user_id = users.user_id
                );
            """))
            
            # Commit the changes
            conn.commit()
            
        logger.info("Successfully migrated database to new streak system")
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Check the logs for details.") 
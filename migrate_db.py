"""
Migration script to add new chain tracking columns to the database.
Run this script once after updating the code to add the new columns.
"""

from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add new columns for chain tracking."""
    try:
        # Create engine
        engine = create_engine('sqlite:///drink_check.db')
        
        # Add new columns if they don't exist
        with engine.connect() as conn:
            # Add columns to users table
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN longest_chain_participation INTEGER DEFAULT 0;
            """))
            
            # Add columns to active_chains table
            conn.execute(text("""
                ALTER TABLE active_chains 
                ADD COLUMN unique_participants_count INTEGER DEFAULT 1;
            """))
            
            conn.execute(text("""
                ALTER TABLE active_chains 
                ADD COLUMN participant_ids TEXT DEFAULT '';
            """))
            
            conn.execute(text("""
                ALTER TABLE active_chains 
                ADD COLUMN is_server_record BOOLEAN DEFAULT 0;
            """))
            
            # Commit the changes
            conn.commit()
            
        logger.info("Successfully added new columns to database")
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
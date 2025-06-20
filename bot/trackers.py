#Trackers for drink check messages and responses
from typing import Optional
from config.settings import TRACKED_CHANNELS

class DrinkCheckTracker:
    def __init__(self):
        self.keywords = ["drink check", "dc"]
        self.tracked_channels = TRACKED_CHANNELS  # Use channels from config
        
    def is_drink_check(self, content: str) -> bool:
        # Check if message contains drink check keywords
        # Convert to lowercase and removes any leading/trailing whitespace
        content_lower = content.lower().strip()
        
        # Generate variations from the base keywords
        variations = []
        for keyword in self.keywords:
            variations.extend([
                keyword,
                f"{keyword}!",
                f"{keyword}?",
                f"{keyword}.",
                "d c",
            ])
        
        return any(variation in content_lower for variation in variations)
        
    def is_response_to_drink_check(self, message) -> Optional[int]:
        # Check if message is a reply to a tracked drink check
        # Return drink check ID if it is
        if message.reference and message.reference.message_id:
            # This is a reply to another message
            # We'll need to check if the referenced message is a drink check
            # For now, return None (will implement database lookup later)
            return None
        return None
        
    async def track_new_drink_check(self, message):
        # Store new drink check in database
        # Update statistics
        # For now, just print for debugging
        print(f"New drink check detected: {message.content} by {message.author.name}")
        
    async def track_response(self, message, drink_check_id: int):
        # Store response in database
        # Update response count
        # For now, just print for debugging
        print(f"Response to drink check {drink_check_id}: {message.content} by {message.author.name}")


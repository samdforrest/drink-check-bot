#Trackers for drink check messages and responses
from typing import Optional
from config.settings import TRACKED_CHANNELS

class DrinkCheckTracker:
    def __init__(self, database=None):
        self.keywords = ["drink check", "dc"]
        self.tracked_channels = TRACKED_CHANNELS  # Use channels from config
        self.database = database
        
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
        
    async def is_response_to_drink_check(self, message) -> Optional[int]:
        # Check if message is a reply to a tracked drink check
        # Return drink check ID if it is
        if message.reference and message.reference.message_id:
            # This is a reply to another message
            # Check if the referenced message is a drink check in our database
            if self.database:
                drink_check_id = await self.database.get_drink_check_by_message_id(str(message.reference.message_id))
                return drink_check_id
        return None
        
    async def track_new_drink_check(self, message):
        # Store new drink check in database
        print(f"New drink check detected: {message.content} by {message.author.name}")
        
        if self.database:
            drink_check_id = await self.database.save_drink_check(
                message_id=str(message.id),
                author_id=str(message.author.id),
                author_name=message.author.name,
                content=message.content,
                channel_id=str(message.channel.id)
            )
            if drink_check_id > 0:
                print(f"Saved drink check with ID: {drink_check_id}")
        
    async def track_response(self, message, drink_check_id: int):
        # Store response in database
        print(f"Response to drink check {drink_check_id}: {message.content} by {message.author.name}")
        
        if self.database:
            response_id = await self.database.save_response(
                drink_check_id=drink_check_id,
                message_id=str(message.id),
                author_id=str(message.author.id),
                author_name=message.author.name,
                content=message.content
            )
            if response_id > 0:
                print(f"Saved response with ID: {response_id}")


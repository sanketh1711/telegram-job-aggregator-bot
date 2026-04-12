from telegram import Bot
from telegram.error import TelegramError
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')

async def is_user_subscribed(user_id):
    """Check if user is a member of the required channel"""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        # Get channel member status
        member = await bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}",
            user_id=user_id
        )
        
        # Check if user is subscribed (not kicked, not restricted)
        if member.status in ['member', 'administrator', 'creator', 'restricted']:
            logger.info(f"✅ User {user_id} is subscribed (status: {member.status})")
            return True
        
        logger.info(f"❌ User {user_id} is not subscribed (status: {member.status})")
        return False
        
    except TelegramError as e:
        logger.error(f"❌ Error checking subscription: {e}")
        # If there's an error, allow access (don't block)
        return True
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return True
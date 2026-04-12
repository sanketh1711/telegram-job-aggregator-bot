import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from subscription_checker import is_user_subscribed
from job_scraper import job_scraper
from keep_alive import keep_alive

# Import our database functions
from database.init_db import (
    init_database, add_user, get_user, is_premium,
    add_premium, remove_premium, increment_searches, 
    increment_viewed, reset_daily_counts
)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database on startup
init_database()

# ============================================================================
# START COMMAND
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # Register user in database
    add_user(user_id, username, first_name)
    
    logger.info(f"✅ User {user_id} ({first_name}) started the bot")
    
    # Send welcome message with buttons
    welcome_text = """
👋 Welcome to *Remote Jobs Bot*!

🌟 Powered by RemoteOK - The #1 Remote Jobs Platform

Find 20+ quality remote jobs for:
• 💻 Technology
• 💰 Finance
• 🛠️ Services

✅ All jobs are REMOTE!
✅ Load More button for unlimited results!

Click below to get started:
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Find Jobs", callback_data="find_jobs")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help_info")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")]
    ])
    
    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# HELP COMMAND
# ============================================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 *How to Use This Bot:*

1. Click *🔎 Find Jobs*
2. Select your *level* (Intern, Junior, Senior, etc.)
3. Choose *job category* (Technology, Finance, Services)
4. Get instant remote job listings! 🎯

💻 *All Jobs Are REMOTE:*
• Remote Full-Time
• Remote Part-Time
• Remote Internship

💳 *Premium Features:*
• Unlimited searches
• 100 jobs per day
• No daily limits

🚀 *Getting Started:*
• `/start` - Welcome menu
• `/help` - This message
• `/status` - Check your account

🌟 *Job Source:*
• RemoteOK - Remote jobs API (Most reliable)

📥 *Load More:*
After viewing 10 jobs, click "Load More 10 Jobs"
to see more opportunities!

Need help? Contact @JobBotSupport
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# STATUS COMMAND
# ============================================================================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ User not found. Send /start first.")
        return
    
    user_id, username, first_name, is_prem, premium_until, searches, viewed, last_search, created_at = user
    
    # Check if premium is still valid
    premium_status = "🎉 *Premium (Active)*" if is_premium(user_id) else "❌ *Free Tier*"
    
    status_text = f"""
📊 *Your Account Status:*

👤 Name: {first_name}
🆔 User ID: {user_id}
💳 {premium_status}

📈 *Today's Usage:*
• Searches: {searches}/5
• Jobs Viewed: {viewed}/30

⏰ Account Created: {created_at[:10]}
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Subscribe Now", callback_data="subscribe")],
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await update.message.reply_text(status_text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# BUTTON CALLBACKS
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks with subscription check"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()  # Remove loading state
    
    # Check if user is subscribed (skip for certain buttons)
    if query.data not in ["start", "subscribe", "subscribe_info", "verify_subscription", "help_info", "my_status"]:
        if not await is_user_subscribed(user_id):
            await subscription_required(query)
            return
    
    # Route based on button pressed
    if query.data == "find_jobs":
        await find_jobs_callback(query)
    elif query.data.startswith("level_"):
        await handle_level_selection(query, context)
    elif query.data.startswith("category_"):
        await handle_job_category(query, context)
    elif query.data == "load_more_jobs":
        await handle_load_more_jobs(query, context)
    elif query.data == "help_info":
        await help_info_callback(query)
    elif query.data == "my_status":
        await my_status_callback(query)
    elif query.data == "subscribe":
        await subscribe_callback(query)
    elif query.data == "verify_subscription":
        await verify_subscription_callback(query)
    elif query.data.startswith("type_"):
        await handle_job_type(query)
    elif query.data.startswith("next_job_"):
        await handle_next_job(query, context)
    elif query.data.startswith("save_job_"):
        await handle_save_job(query)
    elif query.data == "start":
        await start_callback(query)

# ============================================================================
# SUBSCRIPTION CHECK
# ============================================================================

async def subscription_required(query):
    """Show message when user is not subscribed"""
    channel_link = f"https://t.me/{CHANNEL_USERNAME}"
    
    text = f"""
🔒 *Channel Subscription Required*

You must join our channel to use this bot!

📢 *Why?*
• Get job notifications
• Receive updates on new features
• Join our community

👉 Join here: @{CHANNEL_USERNAME}
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
        [InlineKeyboardButton("✅ I'm Subscribed", callback_data="verify_subscription")],
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def verify_subscription_callback(query):
    """Verify subscription after user joins"""
    user_id = query.from_user.id
    
    if await is_user_subscribed(user_id):
        # User is now subscribed
        text = """
✅ *Great! You're Subscribed!*

Welcome to the job bot community! 🎉

Now you can access all features:
• Search jobs by type
• Filter by category
• View unlimited listings

Let's get started!
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Find Jobs", callback_data="find_jobs")],
            [InlineKeyboardButton("← Back", callback_data="start")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # User still not subscribed
        text = """
❌ *You're not subscribed yet!*

Please join the channel first, then click "I'm Subscribed" again.
        """
        
        channel_link = f"https://t.me/{CHANNEL_USERNAME}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ I'm Subscribed", callback_data="verify_subscription")],
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# FIND JOBS
# ============================================================================

async def find_jobs_callback(query):
    """Handle 'Find Jobs' button - show user level selection"""
    text = "👤 *Select Your Level:*\n\nWhat's your professional level?"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Intern", callback_data="level_intern")],
        [InlineKeyboardButton("🟢 Junior (0-2 yrs)", callback_data="level_junior")],
        [InlineKeyboardButton("🔵 Mid-Level (2-5 yrs)", callback_data="level_midlevel")],
        [InlineKeyboardButton("🟠 Senior (5+ yrs)", callback_data="level_senior")],
        [InlineKeyboardButton("⭐ Lead/Manager", callback_data="level_lead")],
        [InlineKeyboardButton("💎 Director/C-Level", callback_data="level_director")],
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# USER LEVEL SELECTION
# ============================================================================

async def handle_level_selection(query, context):
    """Handle user level selection"""
    level = query.data.replace("level_", "")
    
    # Store level in context
    context.user_data['level'] = level
    
    logger.info(f"👤 User {query.from_user.id} selected level: {level}")
    
    # Show job category selection
    text = "💼 *Select Job Category:*\n\nWhich industry are you interested in?"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Technology", callback_data="category_technology")],
        [InlineKeyboardButton("💰 Finance", callback_data="category_finance")],
        [InlineKeyboardButton("🛠️ Services", callback_data="category_services")],
        [InlineKeyboardButton("← Back", callback_data="find_jobs")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# BUSINESS TYPE SELECTION (Removed) & JOB TYPE SELECTION (Merged with Category)
# ============================================================================

async def handle_business_type(query):
    """Handle business type selection"""
    business_type = query.data.replace("business_", "")
    
    # Store business type in context
    user_id = query.from_user.id
    if not hasattr(query.bot, 'user_filters'):
        query.bot.user_filters = {}
    query.bot.user_filters[user_id] = {"business": business_type}
    
    text = "🔎 *Select Job Type:*\n\nWhat type of role are you looking for?"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Remote", callback_data=f"type_remote_{business_type}")],
        [InlineKeyboardButton("🏢 Full-Time", callback_data=f"type_fulltime_{business_type}")],
        [InlineKeyboardButton("⏰ Part-Time", callback_data=f"type_parttime_{business_type}")],
        [InlineKeyboardButton("📚 Internship", callback_data=f"type_internship_{business_type}")],
        [InlineKeyboardButton("← Back", callback_data="find_jobs")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# JOB TYPE SELECTION
# ============================================================================

async def handle_job_type(query):
    """Handle job type selection (kept for backward compatibility)"""
    # Parse callback data: type_remote_startup or type_remote
    parts = query.data.split("_")
    job_type = parts[1]  # remote, fulltime, etc.
    business_type = parts[2] if len(parts) > 2 else "any"
    
    text = "💼 *Select Job Category:*\n\nWhat type of job are you interested in?"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Software/Developer", callback_data=f"category_software_{job_type}_{business_type}")],
        [InlineKeyboardButton("🎨 Design", callback_data=f"category_design_{job_type}_{business_type}")],
        [InlineKeyboardButton("📊 Data Science", callback_data=f"category_data_{job_type}_{business_type}")],
        [InlineKeyboardButton("📱 Mobile", callback_data=f"category_mobile_{job_type}_{business_type}")],
        [InlineKeyboardButton("🔧 DevOps", callback_data=f"category_devops_{job_type}_{business_type}")],
        [InlineKeyboardButton("← Back", callback_data="find_jobs")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# JOB CATEGORY SELECTION & DISPLAY
# ============================================================================

async def handle_job_category(query, context):
    """Handle job category selection and fetch jobs"""
    # Parse callback data: category_technology or category_healthcare_remote_startup
    parts = query.data.split("_")
    category = parts[1]  # technology, healthcare, finance, services, etc.
    
    logger.info(f"🔎 User {query.from_user.id} searching category: {category}")
    
    # Show loading message
    await query.edit_message_text(
        text="⏳ *Fetching jobs...*\n\nPlease wait while we search for jobs.",
        parse_mode="Markdown"
    )
    
    # Map category name to proper format for API
    category_map = {
        "technology": "Technology",
        "finance": "Finance",
        "services": "Services",
        "software": "Technology",
        "design": "Technology",
        "data": "Technology",
        "mobile": "Technology",
        "devops": "Technology"
    }
    
    category_name = category_map.get(category.lower(), "Technology")
    
    # Store category in context for later use (load more jobs)
    context.user_data['category'] = category_name
    
    # Initialize pagination offset for this new category search
    context.user_data['page_offset'] = 0
    
    # Fetch jobs
    jobs = await job_scraper.search_jobs(category_name, offset=0)
    
    logger.info(f"📊 Returned {len(jobs)} jobs for category={category_name}")
    
    if not jobs:
        text = "❌ *No jobs found*\n\nTry a different category or check back later."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back", callback_data="find_jobs")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return
    
    # Store jobs in user context data (fixed from query.bot.user_jobs)
    context.user_data['jobs'] = jobs
    context.user_data['current_index'] = 0
    
    # Show first job
    await show_job(query, jobs, 0)

async def show_job(query, jobs, job_index):
    """Display a single job"""
    
    if job_index >= len(jobs):
        # Check if we should show "Load More" button
        if job_index == len(jobs) and job_index >= 10:
            text = "✅ *You've viewed 10 jobs!*\n\nLoad more to see additional listings."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Load More 10 Jobs", callback_data="load_more_jobs")],
                [InlineKeyboardButton("🔄 Start Over", callback_data="find_jobs")],
                [InlineKeyboardButton("🏠 Home", callback_data="start")]
            ])
        else:
            text = "✅ *You've reached the end!*\n\nNo more jobs to show."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Start Over", callback_data="find_jobs")],
                [InlineKeyboardButton("← Back", callback_data="start")]
            ])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return
    
    job = jobs[job_index]
    
    # Safely format the job message
    try:
        text = f"""
💼 *{job.get('title', 'N/A')}*

🏢 Company: {job.get('company', 'N/A')}
📍 Location: {job.get('location', 'Remote')}
💼 Type: {job.get('type', 'N/A')}
📰 Source: {job.get('source', 'Unknown')}
👤 Level: {job.get('level', 'N/A')}

📝 Description:
{job.get('description', 'No description available')}

🔗 [Apply Here]({job.get('url', '#')})
        """
    except Exception as e:
        logger.error(f"❌ Error formatting job display: {e}")
        text = f"❌ Error displaying job. Please try another job."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("� Interested", callback_data=f"save_job_{job_index}")],
        [InlineKeyboardButton("➡️ Next ({}/{})".format(job_index + 1, len(jobs)), callback_data=f"next_job_{job_index}")],
        [InlineKeyboardButton("🏠 Home", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_next_job(query, context):
    """Show next job"""
    user_id = query.from_user.id
    job_index = int(query.data.split("_")[2])
    
    # Get jobs from context (fixed from query.bot.user_jobs)
    if 'jobs' not in context.user_data:
        await query.edit_message_text("❌ Job session expired. Please search again.", parse_mode="Markdown")
        return
    
    jobs = context.user_data['jobs']
    await show_job(query, jobs, job_index + 1)

async def handle_load_more_jobs(query, context):
    """Load 10 more jobs with pagination"""
    # Get the stored category from context
    if 'category' not in context.user_data:
        await query.edit_message_text("❌ Job session expired. Please search again.", parse_mode="Markdown")
        return
    
    category = context.user_data['category']
    
    # Get current pagination offset and increment it
    current_offset = context.user_data.get('page_offset', 0)
    next_offset = current_offset + 1
    
    # Show loading message
    await query.edit_message_text(
        text="⏳ *Loading more jobs...*\n\nPlease wait while we fetch additional jobs.",
        parse_mode="Markdown"
    )
    
    logger.info(f"📥 User {query.from_user.id} loading more jobs for category: {category} (offset={next_offset})")
    
    # Fetch more jobs with new offset
    more_jobs = await job_scraper.search_jobs(category, offset=next_offset)
    
    if more_jobs:
        # Get existing jobs
        existing_jobs = context.user_data.get('jobs', [])
        current_count = len(existing_jobs)
        
        # Append new jobs (avoid duplicates by checking URLs)
        existing_urls = {job.get('url', '') for job in existing_jobs}
        new_jobs_added = 0
        
        for job in more_jobs:
            if job.get('url', '') not in existing_urls and new_jobs_added < 20:
                existing_jobs.append(job)
                existing_urls.add(job.get('url', ''))
                new_jobs_added += 1
        
        context.user_data['jobs'] = existing_jobs
        # Update pagination offset
        context.user_data['page_offset'] = next_offset
        
        logger.info(f"📊 Added {new_jobs_added} new jobs. Total now: {len(existing_jobs)}")
        
        # Show the next job
        await show_job(query, existing_jobs, current_count)
    else:
        text = "❌ *No more jobs available*\n\nTry a different category or check back later."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back", callback_data="find_jobs")],
            [InlineKeyboardButton("🏠 Home", callback_data="start")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_save_job(query):
    """Save job to user profile"""
    user_id = query.from_user.id
    increment_viewed(user_id)
    
    text = "✅ *Job Saved!*\n\nWe'll remember this job. Check your saved jobs anytime."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Next Job", callback_data="find_jobs")],
        [InlineKeyboardButton("🏠 Home", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# OTHER CALLBACKS
# ============================================================================

async def help_info_callback(query):
    """Handle 'Help' button"""
    text = """
📖 *How to Use This Bot:*

1. Click *🔎 Find Jobs*
2. Select job type
3. Choose category
4. Get job listings!

💡 *Tips:*
• Free tier: 5 searches, 30 jobs/day
• Premium: Unlimited access
• Use wisely to stay within limits!
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def my_status_callback(query):
    """Handle 'My Status' button"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        text = "❌ User not found."
    else:
        user_id, username, first_name, is_prem, premium_until, searches, viewed, last_search, created_at = user
        premium_status = "🎉 *Premium (Active)*" if is_premium(user_id) else "❌ *Free Tier*"
        
        text = f"""
📊 *Your Account Status:*

👤 Name: {first_name}
🆔 User ID: {user_id}
💳 {premium_status}

📈 *Today's Usage:*
• Searches: {searches}/5
• Jobs Viewed: {viewed}/30

⏰ Created: {created_at[:10]}
        """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Subscribe Now", callback_data="subscribe")],
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def subscribe_callback(query):
    """Handle 'Subscribe' button"""
    text = """
💳 *To Unlock Premium ($2.99/month):*

1. Pay via our secure link: [Payment Link]
2. Take a screenshot of receipt
3. Send screenshot + User ID to: @JobBotSupport

Your User ID: `{user_id}`

🎉 Your account will be activated within a few hours!
    """.format(user_id=query.from_user.id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Back", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def start_callback(query):
    """Handle 'Back to Start' button"""
    text = """
👋 Welcome to *Remote Jobs Bot*!

🌟 Powered by RemoteOK - The #1 Remote Jobs Platform

Find 20+ quality remote jobs for:
• 💻 Technology
• 💰 Finance
• 🛠️ Services

✅ All jobs are REMOTE!
✅ Load More button for unlimited results!

Click below to get started:
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Find Jobs", callback_data="find_jobs")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help_info")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============================================================================
# MAIN - START BOT
# ============================================================================

def main():
    """Start the bot"""
    logger.info("🚀 Bot Starting Up...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Add button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot Ready! Polling for messages...")
    
    # Start polling
    application.run_polling()

if __name__ == '__main__':
    keep_alive()  # <-- Add this line
    main()
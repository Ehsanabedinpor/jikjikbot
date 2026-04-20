"""
Configuration file for Jik Jik Bot
"""
from os import getenv

import dotenv, os

dotenv.load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'YourBotUsername')  # set BOT_USERNAME in .env

# Bale API endpoints
BALE_API_BASE_URL = 'https://tapi.bale.ai/bot'
BALE_FILE_BASE_URL = 'https://tapi.bale.ai/file/bot'

# Database
DATABASE_PATH = "jik_jik_bot.db"

# Point System
JIK_JIK_POINTS = 10
JIK_JIK_COOLDOWN = 3* 60  # 3 minutes in seconds

# Purchase Costs
EGG_COST_1 = 500
EGG_COST_2 = 1000
NAMING_COST = 1500

# Attack Costs
BREAK_EGG_COST = 1000
KILL_ANIMAL_COST = 6000

# Unlock Thresholds
AUTO_JIK_UNLOCK_10MIN = 3000
AUTO_JIK_UNLOCK_5MIN = 9000
TICTACTOE_UNLOCK = 6000
BREEDING_UNLOCK = 30000

# Auto Jik Jik Intervals
AUTO_JIK_INTERVAL_10MIN = 10 * 60
AUTO_JIK_INTERVAL_5MIN = 5 * 60

# Minimum group members
MIN_GROUP_MEMBERS = 3

# Admin IDs
ADMIN_IDS = [123456789]

# Message texts
MESSAGES = {
    "welcome": """
🏠 *Welcome to Jik Jik Bot!*

Earn points by typing "Jik Jik" and unlock amazing features!

📊 *Your Stats:*
• Points: {points}
• Eggs: {eggs}
• Chickens: {chickens}
• Roosters: {roosters}

💡 *Quick Commands:*
• Type "Jik Jik" → Earn 30 points
• /buy - Purchase items
• /eggs - View your eggs
• /animals - View your animals
• /tictactoe - Play Tic Tac Toe
• /pay - Buy points with real money
• /help - All commands

⭐ *Milestones:*
• 3000 pts: Auto Jik Jik (10 min)
• 6000 pts: Tic Tac Toe game
• 9000 pts: Auto Jik Jik (5 min)
• 30000 pts: Breeding unlocked
""",
    "help": """
📚 *Help Menu*

*دستورات:*
/start - راه اندازی مجدد بات
/profile - مشاهده پروفایل
/help - نمایش این پیام

*دریافت امتیاز:*
Simply type "Jik Jik" to earn 30 points!
(7 minute cooldown between uses)

*Purchases:*
/buy - Open purchase menu
/eggs - View/manage eggs
/animals - View/name animals

*Games:*
/tictactoe <bet> - Start a game (open invite)
/tictactoe <bet> @username - Challenge a specific user

*Payment:*
/pay - Buy points with real money

*Admin:*
/broadcast < @ehsanabedin  @parisaw_pr > - Send message to all users (admin only)
/stats - View bot statistics (admin only)
""",
    "not_enough_points": "❌ You don't have enough points! You need {needed} points but have {have} points.",
    "cooldown": "⏳ Please wait {remaining} seconds before using Jik Jik again!",
    "jik_jik_success": "✅ *Jik Jik!* +30 points!\n\nYour points: {points}",
    "auto_jik_unlocked": "🎉 *Congratulations!* You've unlocked Auto Jik Jik!\n\nYour Jik Jik will be automatically credited every 10 minutes!",
}

PAYMENT_PACKAGES = {
    'pay_1000': {
        'name': '1,000 Points',
        'points': 1000,
        'price_toman': 5000,
        'price_rial': 5000,
        'label': '💎 1,000 Points',
    },
    'pay_5000': {
        'name': '5,000 Points',
        'points': 5000,
        'price_toman': 10000,
        'price_rial': 10000,
        'label': '💎 5,000 Points',
    },
    'pay_egg': {
        'name': '1 Egg',
        'eggs': 1,
        'price_toman': 15000,
        'price_rial': 150000,
        'label': '🥚 1 Egg',
    },
    'pay_2eggs': {
        'name': '2 Eggs',
        'eggs': 2,
        'price_toman': 28000,
        'price_rial': 280000,
        'label': '🥚🥚 2 Eggs',
    },
}

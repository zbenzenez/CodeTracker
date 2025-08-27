import asyncio
import schedule
import time
import logging
from datetime import datetime, timezone
import os
from server import github_client, leetcode_scraper, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self):
        self.running = False
        
    async def check_and_notify_user(self, username: str, platform: str):
        """Check platform status and send notification if needed"""
        try:
            logger.info(f"Checking {platform} status for {username}")
            
            if platform == "github":
                status = await github_client.check_commits_today(username)
                if not status.has_commits_today:
                    logger.info(f"🔔 NOTIFICATION: {username} hasn't made any GitHub commits today!")
                    # Here you would send actual notification (email, push, etc.)
                    return {
                        "type": "github_reminder",
                        "message": f"Hey {username}! You haven't made any commits today. Time to code! 💻",
                        "status": "pending"
                    }
            
            elif platform == "leetcode":
                status = await leetcode_scraper.get_potd_status(username)
                if not status.potd_solved:
                    logger.info(f"🔔 NOTIFICATION: {username} hasn't solved today's LeetCode POTD!")
                    # Here you would send actual notification
                    return {
                        "type": "leetcode_reminder", 
                        "message": f"Hey {username}! Today's LeetCode POTD '{status.potd_title}' is waiting for you! 🧠",
                        "status": "pending"
                    }
            
            return {"status": "completed"}
            
        except Exception as e:
            logger.error(f"Error checking {platform} for {username}: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def process_triggers(self):
        """Process all active triggers"""
        try:
            current_time = datetime.now().strftime("%H:%M")
            
            # Get all active triggers for current time
            triggers = await db.triggers.find({
                "trigger_time": current_time,
                "enabled": True
            }).to_list(1000)
            
            logger.info(f"Found {len(triggers)} triggers for {current_time}")
            
            for trigger in triggers:
                username = trigger['username']
                platform = trigger['platform']
                
                # Check and notify
                result = await self.check_and_notify_user(username, platform)
                
                # Log the notification
                notification_log = {
                    "trigger_id": trigger['id'],
                    "username": username,
                    "platform": platform,
                    "checked_at": datetime.now(timezone.utc),
                    "result": result
                }
                
                await db.notification_logs.insert_one(notification_log)
                
        except Exception as e:
            logger.error(f"Error processing triggers: {str(e)}")

    def start_scheduler(self):
        """Start the notification scheduler"""
        logger.info("🚀 Starting notification scheduler...")
        
        # Schedule to run every minute
        schedule.every().minute.do(lambda: asyncio.run(self.process_triggers()))
        
        self.running = True
        
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds

    def stop_scheduler(self):
        """Stop the notification scheduler"""
        logger.info("⏹️ Stopping notification scheduler...")
        self.running = False

# CLI interface
if __name__ == "__main__":
    import sys
    
    scheduler = NotificationScheduler()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - check notifications for the configured user
        async def test_notifications():
            username = os.environ.get('GITHUB_USERNAME', 'NK-NiteshKumar')
            print(f"\n🧪 Testing notifications for {username}...")
            
            # Test GitHub
            github_result = await scheduler.check_and_notify_user(username, "github")
            print(f"GitHub: {github_result}")
            
            # Test LeetCode
            leetcode_result = await scheduler.check_and_notify_user(username, "leetcode")
            print(f"LeetCode: {leetcode_result}")
            
        asyncio.run(test_notifications())
    else:
        # Normal mode - run scheduler
        try:
            scheduler.start_scheduler()
        except KeyboardInterrupt:
            scheduler.stop_scheduler()
            logger.info("Scheduler stopped by user")
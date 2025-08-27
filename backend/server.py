from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
import requests
from bs4 import BeautifulSoup
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# GitHub Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_USERNAME = os.environ.get('GITHUB_USERNAME', '')
GITHUB_API_BASE = "https://api.github.com"

# Create the main app without a prefix
app = FastAPI(
    title="Reminder App API",
    description="Track GitHub commits and LeetCode POTD with notifications",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class PlatformStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str  # "github" or "leetcode"
    username: str
    completed_today: bool
    details: Dict[str, Any] = {}
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    date: str  # YYYY-MM-DD format

class NotificationTrigger(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str
    username: str
    trigger_time: str  # HH:MM format like "23:45"
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CommitInfo(BaseModel):
    sha: str
    message: str
    author: str
    repository: str
    committed_date: datetime
    url: str

class GitHubStatus(BaseModel):
    username: str
    has_commits_today: bool
    commit_count: int
    commits: List[CommitInfo]
    check_timestamp: datetime

class LeetCodeStatus(BaseModel):
    username: str
    potd_solved: bool
    potd_title: str
    potd_difficulty: str
    potd_date: str
    user_status: Optional[str] = None
    check_timestamp: datetime

# GitHub API Client
class GitHubAPIClient:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.base_url = GITHUB_API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def get_user_events(self, username: str) -> List[Dict[str, Any]]:
        """Fetch recent user events from GitHub API"""
        events = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                url = f"{self.base_url}/users/{username}/events"
                params = {"page": 1, "per_page": 100}
                
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail="GitHub user not found")
                elif response.status_code == 403:
                    raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded")
                elif response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid GitHub token")
                elif response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="GitHub API error")
                
                events = response.json()
                return events
            except httpx.RequestError as e:
                raise HTTPException(status_code=500, detail=f"GitHub API connection error: {str(e)}")
    
    async def check_commits_today(self, username: str) -> GitHubStatus:
        """Check if user has made any commits today"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_commits = []
        
        try:
            events = await self.get_user_events(username)
            
            # Process push events for today
            for event in events:
                if event.get("type") != "PushEvent":
                    continue
                    
                event_date = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                if event_date < today_start:
                    continue
                    
                # Extract commit information from push event
                payload = event.get("payload", {})
                commits = payload.get("commits", [])
                repo_name = event.get("repo", {}).get("name", "")
                
                for commit in commits:
                    commit_info = CommitInfo(
                        sha=commit["sha"],
                        message=commit["message"],
                        author=commit["author"]["name"],
                        repository=repo_name,
                        committed_date=event_date,
                        url=f"https://github.com/{repo_name}/commit/{commit['sha']}"
                    )
                    today_commits.append(commit_info)
            
            return GitHubStatus(
                username=username,
                has_commits_today=len(today_commits) > 0,
                commit_count=len(today_commits),
                commits=today_commits,
                check_timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logging.error(f"Error checking GitHub commits for {username}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking GitHub commits: {str(e)}")

# LeetCode Scraper
class LeetCodeScraper:
    def __init__(self):
        self.base_url = "https://leetcode.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_daily_challenge(self) -> Dict[str, Any]:
        """Get today's Problem of the Day"""
        try:
            url = f"{self.base_url}/graphql"
            query = """
            query questionOfToday {
                activeDailyCodingChallengeQuestion {
                    date
                    userStatus
                    link
                    question {
                        acRate
                        difficulty
                        freqBar
                        frontendQuestionId: questionFrontendId
                        isFavor
                        paidOnly: isPaidOnly
                        status
                        title
                        titleSlug
                        hasVideoSolution
                        hasSolution
                        topicTags {
                            name
                            id
                            slug
                        }
                    }
                }
            }
            """
            
            response = self.session.post(url, json={'query': query})
            
            if response.status_code != 200:
                raise Exception(f"LeetCode API returned status {response.status_code}")
            
            data = response.json()
            
            if 'data' not in data or not data['data'] or not data['data']['activeDailyCodingChallengeQuestion']:
                raise Exception("No daily challenge data found")
            
            challenge = data['data']['activeDailyCodingChallengeQuestion']
            question = challenge['question']
            
            return {
                'date': challenge['date'],
                'userStatus': challenge.get('userStatus', 'NotStart'),
                'title': question['title'],
                'difficulty': question['difficulty'],
                'titleSlug': question['titleSlug'],
                'link': challenge['link'],
                'frontendQuestionId': question['frontendQuestionId']
            }
        except Exception as e:
            logging.error(f"Error fetching LeetCode daily challenge: {str(e)}")
            raise Exception(f"Failed to fetch LeetCode POTD: {str(e)}")
    
    def check_user_submission(self, username: str, problem_slug: str) -> bool:
        """Check if user has solved specific problem"""
        try:
            # This is a simplified check - in reality, you'd need to be logged in
            # For now, we'll return False as we can't check user-specific data without login
            return False
        except Exception as e:
            logging.error(f"Error checking user submission for {username}: {str(e)}")
            return False
    
    async def get_potd_status(self, username: str) -> LeetCodeStatus:
        """Get POTD status for user"""
        try:
            potd_data = self.get_daily_challenge()
            
            # For now, we can't check if user solved it without authentication
            # This would require the user to provide LeetCode credentials
            potd_solved = False  # Would need actual user session to check this
            
            return LeetCodeStatus(
                username=username,
                potd_solved=potd_solved,
                potd_title=potd_data['title'],
                potd_difficulty=potd_data['difficulty'],
                potd_date=potd_data['date'],
                user_status=potd_data.get('userStatus'),
                check_timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logging.error(f"Error getting LeetCode POTD status for {username}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking LeetCode POTD: {str(e)}")

# Initialize clients
github_client = GitHubAPIClient()
leetcode_scraper = LeetCodeScraper()

# Routes
@api_router.get("/")
async def root():
    return {"message": "Reminder App API", "status": "active"}

@api_router.get("/github/check/{username}", response_model=GitHubStatus)
async def check_github_commits(username: str):
    """Check GitHub commits for today"""
    try:
        status = await github_client.check_commits_today(username)
        
        # Store status in database
        status_dict = status.dict()
        status_dict['platform'] = 'github'
        status_dict['completed_today'] = status.has_commits_today
        status_dict['date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        await db.platform_status.insert_one(status_dict)
        
        return status
    except Exception as e:
        logging.error(f"Error in check_github_commits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/leetcode/check/{username}", response_model=LeetCodeStatus)
async def check_leetcode_potd(username: str):
    """Check LeetCode POTD status"""
    try:
        status = await leetcode_scraper.get_potd_status(username)
        
        # Store status in database
        status_dict = status.dict()
        status_dict['platform'] = 'leetcode'
        status_dict['completed_today'] = status.potd_solved
        status_dict['date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        await db.platform_status.insert_one(status_dict)
        
        return status
    except Exception as e:
        logging.error(f"Error in check_leetcode_potd: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/dashboard/{username}")
async def get_dashboard(username: str):
    """Get complete dashboard status for user"""
    try:
        # Check GitHub
        github_status = await github_client.check_commits_today(username)
        
        # Check LeetCode
        leetcode_status = await leetcode_scraper.get_potd_status(username)
        
        return {
            "username": username,
            "github": github_status.dict(),
            "leetcode": leetcode_status.dict(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logging.error(f"Error in get_dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/triggers", response_model=NotificationTrigger)
async def create_trigger(trigger: NotificationTrigger):
    """Create a new notification trigger"""
    trigger_dict = trigger.dict()
    result = await db.triggers.insert_one(trigger_dict)
    return trigger

@api_router.get("/triggers/{username}", response_model=List[NotificationTrigger])
async def get_user_triggers(username: str):
    """Get all triggers for a user"""
    triggers = await db.triggers.find({"username": username}).to_list(1000)
    return [NotificationTrigger(**trigger) for trigger in triggers]

@api_router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str):
    """Delete a notification trigger"""
    result = await db.triggers.delete_one({"id": trigger_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"message": "Trigger deleted successfully"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "github_token_configured": bool(GITHUB_TOKEN),
        "github_username": GITHUB_USERNAME
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
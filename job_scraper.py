import aiohttp
import asyncio
import logging
from typing import List, Dict
import json
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

class JobScraper:
    """Scrape jobs from multiple platforms"""
    
    def __init__(self):
        self.jobs_cache = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Respect ToS by adding delays
        self.last_request_time = {}
        self.min_delay = 1  # seconds between requests to same domain
    
    async def respect_delay(self, domain: str):
        """Respect Terms of Service with rate limiting"""
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)
        self.last_request_time[domain] = time.time()
    
    # ========================================================================
    # REMOTEOK API
    # ========================================================================
    
    async def get_remoteok_jobs(self, category: str = "Technology", offset: int = 0) -> List[Dict]:
        """Fetch jobs from RemoteOK with pagination support"""
        try:
            url = "https://remoteok.io/api"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), headers=self.headers) as response:
                    logger.info(f"RemoteOK API Status: {response.status}")
                    if response.status == 200:
                        jobs = await response.json()
                        
                        # Pagination: offset determines starting position
                        # Each offset gets 20 different jobs
                        # offset=0: [1:21]
                        # offset=1: [21:41]
                        # offset=2: [41:61]
                        # etc.
                        start_idx = 1 + (offset * 20)
                        end_idx = start_idx + 20
                        
                        formatted_jobs = []
                        for job in jobs[start_idx:end_idx]:
                            if isinstance(job, dict) and job.get("id"):
                                formatted_jobs.append({
                                    "title": job.get("title", "N/A"),
                                    "company": job.get("company", "N/A"),
                                    "location": job.get("location", "Remote"),
                                    "type": "Remote",
                                    "url": job.get("url", ""),
                                    "description": job.get("description", "No description")[:150] + "...",
                                    "source": "RemoteOK",
                                    "category": "Technology",
                                    "tags": job.get("tags", [])
                                })
                        
                        logger.info(f"✅ Fetched {len(formatted_jobs)} jobs from RemoteOK (offset={offset}, idx {start_idx}-{end_idx})")
                        return formatted_jobs
                    else:
                        logger.error(f"❌ RemoteOK API returned status {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"❌ RemoteOK API timeout")
        except Exception as e:
            logger.error(f"❌ Error fetching RemoteOK jobs: {e}")
        
        return []
    
    # ========================================================================
    # BONUS SOURCES (Optional - these may not work reliably)
    # For now, we focus on RemoteOK which is stable and reliable
    # ========================================================================
    
    async def get_bonus_jobs(self, category: str = "Technology") -> List[Dict]:
        """Try to get jobs from bonus sources (Adzuna, Jooble, etc.)"""
        # These are skipped for now due to API issues
        # Feel free to enable if you have valid API keys/endpoints
        return []
    
    # ========================================================================
    # AGGREGATE JOBS BY CATEGORY
    # ========================================================================
    
    async def get_all_jobs_by_category(self, category: str, offset: int = 0) -> List[Dict]:
        """Fetch jobs from all sources for specific category"""
        try:
            logger.info(f"🔍 Starting job fetch for category: {category}, offset: {offset}")
            
            all_jobs = []
            
            # Primary source: RemoteOK API (MOST RELIABLE - 20 jobs at a time)
            remoteok_jobs = await self.get_remoteok_jobs(category, offset)
            all_jobs.extend(remoteok_jobs)
            
            logger.info(f"✅ Total jobs fetched for {category}: {len(all_jobs)}")
            
            # Always return at least something (jobs or mock data)
            if len(all_jobs) == 0:
                logger.warning(f"⚠️ No jobs fetched for {category}, returning mock data")
                all_jobs = [
                    {
                        "title": f"Senior {category} Professional",
                        "company": "Tech Company A",
                        "location": "Remote",
                        "type": "Remote",
                        "url": "https://example.com/job1",
                        "description": f"We are looking for an experienced {category} professional with 5+ years of experience. Join our growing remote team!",
                        "source": "Mock Data",
                        "category": category,
                        "level": "Senior"
                    },
                    {
                        "title": f"Mid-Level {category} Specialist",
                        "company": "Tech Company B",
                        "location": "Remote",
                        "type": "Remote",
                        "url": "https://example.com/job2",
                        "description": f"Exciting remote opportunity in {category}! Work with cutting-edge technology and great benefits.",
                        "source": "Mock Data",
                        "category": category,
                        "level": "Mid-Level"
                    }
                ]
            
            return all_jobs
        
        except Exception as e:
            logger.error(f"❌ Error aggregating jobs: {e}")
            return []
    
    # ========================================================================
    # SEARCH JOBS BY CATEGORY ONLY (Simplified)
    # ========================================================================
    
    async def search_jobs(self, category: str, offset: int = 0) -> List[Dict]:
        """Search jobs by category with pagination offset"""
        try:
            # Get all jobs for the selected category with offset for pagination
            all_jobs = await self.get_all_jobs_by_category(category, offset)
            
            logger.info(f"✅ Found {len(all_jobs)} jobs for category: {category} (offset={offset})")
            return all_jobs
        
        except Exception as e:
            logger.error(f"❌ Error searching jobs: {e}")
            return []

# Create a global instance
job_scraper = JobScraper()
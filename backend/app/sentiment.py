"""
ASCENT — Sentiment Analysis Module

Collects real student opinions and reviews from two public
sources (PaGaLGuY forums and YouTube video comments), scores
them using VADER (a lexicon-based sentiment analysis tool),
and computes:

1. GATE Exam Difficulty Score (per year) — how hard students
   found a particular GATE cycle, used to contextualise
   cutoff score predictions.

2. NIT Quality Score (per institute) — student sentiment
   about placements, campus life, and faculty, broken into
   sub-scores and an overall score, used as one of the five
   factors in the recommendation engine.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()

# ── VADER analyser with custom lexicon additions ──────────
# Base VADER lexicon is tuned for general English social
# media. We extend it with Indian internet slang and emojis
# commonly seen in GATE/NIT discussion posts, which the
# default lexicon does not recognise.

analyser = SentimentIntensityAnalyzer()

custom_lexicon = {
    "🔥": 2.5,
    "📈": 1.8,
    "op": 2.0,
    "mast": 2.0,
    "badhiya": 2.0,
    "solid": 2.2,
    "worth it": 2.0,
    "waste": -2.5,
    "bekar": -2.0,
    "ganda": -2.0,
    "chalu": -1.0,
    "top notch": 3.0,
    "underrated": 1.5,
    "overrated": -1.5,
}
analyser.lexicon.update(custom_lexicon)


def get_sentiment_score(text: str) -> float:
    """Returns VADER compound score: -1 (negative) to +1 (positive)."""
    scores = analyser.polarity_scores(text)
    return scores["compound"]


# ── Noise filtering ────────────────────────────────────────
# GATE/NIT discussion threads are dominated by students
# asking "will I get in with this rank/percentile" — these
# carry no real sentiment about exam difficulty or NIT
# quality and pollute the average if left in. We filter
# them out before scoring.

NOISE_PATTERNS = [
    r'\bpercentile\b',
    r'\brank\b',
    r'\bcutoff\b',
    r'\bcut off\b',
    r'\bair\b',
    r'\bmilega\b',
    r'\bmilegi\b',
    r'\bmil sakta\b',
    r'\bpossible hai\b',
    r'\bews\b.*\bhomestate\b',
    r'^\d+\.?\d*\s*(percentile|rank)',
    r'\bkya\b.*\?$',
]


def is_noise_post(text: str) -> bool:
    """Returns True if a post looks like a rank/cutoff query
    rather than a genuine opinion about difficulty or quality."""
    text_lower = text.lower().strip()

    if len(text_lower) < 25:
        return True

    digit_ratio = sum(c.isdigit() for c in text_lower) / max(len(text_lower), 1)
    if digit_ratio > 0.15:
        return True

    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


def filter_opinion_posts(posts: list) -> list:
    """Keep only posts likely to contain a real opinion."""
    return [p for p in posts if not is_noise_post(p)]


# ── PaGaLGuY scraper ─────────────────────────────────────────
# Public discussion forum, no login required to read.
# Scraped respectfully with a delay between requests.

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}


def search_pagalguy(query: str, max_results: int = 20):
    """Search PaGaLGuY for a query and return thread URLs."""
    search_url = f"https://www.pagalguy.com/search?q={query.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/threads/" in href or "/discussions/" in href:
                if href not in links:
                    links.append(href)
            if len(links) >= max_results:
                break
        return links
    except Exception as e:
        print(f"Error searching PaGaLGuY for '{query}': {e}")
        return []


def scrape_pagalguy_thread(url: str):
    """Scrape post text blocks from a single PaGaLGuY thread page."""
    if not url.startswith("http"):
        url = "https://www.pagalguy.com" + url

    try:
        time.sleep(2)  # respectful delay between requests
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        posts = []
        for tag in soup.find_all(["p", "div"], class_=True):
            text = tag.get_text(strip=True)
            if len(text) > 40:
                posts.append(text)

        return posts[:10]
    except Exception as e:
        print(f"Error scraping thread {url}: {e}")
        return []


def fetch_pagalguy_posts(query: str, max_threads: int = 10):
    """Search PaGaLGuY, scrape each matching thread found."""
    thread_links = search_pagalguy(query, max_threads)
    all_posts = []
    for link in thread_links:
        posts = scrape_pagalguy_thread(link)
        all_posts.extend(posts)
    return all_posts


# ── YouTube Data API ──────────────────────────────────────────
# Official Google API. Free tier: 10,000 units/day,
# ~100 units per search call. Quota resets daily.

_youtube_quota_exhausted = False


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    return build("youtube", "v3", developerKey=api_key)


def search_youtube_videos(query: str, max_results: int = 5):
    """Search YouTube for videos matching query. Returns video IDs.
    Stops attempting further calls once daily quota is exhausted."""
    global _youtube_quota_exhausted

    if _youtube_quota_exhausted:
        return []

    youtube = get_youtube_client()
    try:
        request = youtube.search().list(
            q=query,
            part="id",
            type="video",
            maxResults=max_results,
            relevanceLanguage="en"
        )
        response = request.execute()
        return [
            item["id"]["videoId"]
            for item in response.get("items", [])
        ]
    except Exception as e:
        error_str = str(e)
        if "quotaExceeded" in error_str or "rateLimitExceeded" in error_str:
            if not _youtube_quota_exhausted:
                print("  ⚠️ YouTube daily quota exhausted — "
                      "skipping YouTube for remaining NITs this run "
                      "(falling back to PaGaLGuY only). Quota resets daily.")
            _youtube_quota_exhausted = True
            return []
        elif "commentsDisabled" not in error_str:
            print(f"  YouTube search error for '{query}': {error_str[:120]}")
        return []


def fetch_youtube_comments(video_id: str, max_comments: int = 50):
    """Fetch top-level comments from a YouTube video.
    Silently skips videos with comments disabled or on quota exhaustion."""
    global _youtube_quota_exhausted

    if _youtube_quota_exhausted:
        return []

    youtube = get_youtube_client()
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_comments,
            textFormat="plainText",
            order="relevance"
        )
        response = request.execute()
        for item in response.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)
    except Exception as e:
        error_str = str(e)
        if "quotaExceeded" in error_str or "rateLimitExceeded" in error_str:
            _youtube_quota_exhausted = True
        elif "commentsDisabled" not in error_str:
            print(f"  Comment fetch error for video {video_id}: {error_str[:120]}")
    return comments


def fetch_youtube_posts(query: str, max_videos: int = 5):
    """Search YouTube, fetch comments from each video found."""
    video_ids = search_youtube_videos(query, max_videos)
    all_comments = []
    for vid in video_ids:
        comments = fetch_youtube_comments(vid)
        all_comments.extend(comments)
        time.sleep(0.5)
    return all_comments


# ── Combined fetch: GATE difficulty ───────────────────────────

def fetch_gate_difficulty_posts(year: int):
    """Combine PaGaLGuY + YouTube posts discussing a GATE year's
    difficulty. Tags each post with its source for transparency."""
    queries = [
        f"GATE {year} paper analysis difficulty",
        f"GATE {year} exam review students reaction",
        f"GATE CSE {year} was it tough or easy"
    ]

    all_posts = []
    for q in queries:
        for p in fetch_pagalguy_posts(q, max_threads=4):
            all_posts.append({"text": p, "source": "PaGaLGuY"})
        for p in fetch_youtube_posts(q, max_videos=3):
            all_posts.append({"text": p, "source": "YouTube"})

    filtered = [p for p in all_posts if not is_noise_post(p["text"])]

    print(f"Fetched {len(all_posts)} raw posts for GATE {year}, "
          f"{len(filtered)} kept after noise filtering")
    return filtered


# ── Combined fetch: NIT reviews ─────────────────────────────────

def fetch_nit_review_posts(nit_name: str):
    """Combine PaGaLGuY + YouTube posts discussing a specific
    NIT's placements, campus, and faculty. Tags source for
    transparency."""
    queries = [
        f"{nit_name} hostel life experience",
        f"{nit_name} campus tour vlog",
        f"{nit_name} alumni experience",
        f"{nit_name} MTech placement companies",
        f"{nit_name} faculty teaching quality",
        f"studying at {nit_name}"
    ]

    all_posts = []
    for q in queries:
        for p in fetch_pagalguy_posts(q, max_threads=4):
            all_posts.append({"text": p, "source": "PaGaLGuY"})
        for p in fetch_youtube_posts(q, max_videos=2):
            all_posts.append({"text": p, "source": "YouTube"})

    filtered = [p for p in all_posts if not is_noise_post(p["text"])]

    print(f"Fetched {len(all_posts)} raw posts for {nit_name}, "
          f"{len(filtered)} kept after noise filtering")
    return filtered


# ── Score calculation: GATE difficulty ────────────────────────

def calculate_gate_difficulty(year: int) -> dict:
    """
    Returns a difficulty score (0-10) for a GATE year, derived
    from average VADER sentiment across collected posts.
    10 = very hard, 0 = very easy.
    """
    posts = fetch_gate_difficulty_posts(year)

    if not posts:
        return {
            "year": year,
            "difficulty_score": 5.0,
            "label": "Moderate",
            "posts_analysed": 0,
            "source": "default",
            "sample_posts": []
        }

    scores = [get_sentiment_score(p["text"]) for p in posts]
    avg_sentiment = sum(scores) / len(scores)

    # Negative sentiment about the paper = harder exam;
    # positive sentiment = easier exam. Map -1..+1 sentiment
    # to a 0..10 difficulty scale (inverted).
    difficulty = round((1 - avg_sentiment) / 2 * 10, 1)
    difficulty = max(0.0, min(10.0, difficulty))

    if difficulty >= 8:
        label = "Very Hard"
    elif difficulty >= 6.5:
        label = "Hard"
    elif difficulty >= 5:
        label = "Moderately Hard"
    elif difficulty >= 3.5:
        label = "Moderate"
    else:
        label = "Easy"

    sample_posts = [
        {
            "text": post["text"][:300],
            "source": post["source"],
            "sentiment_score": round(scores[i], 3)
        }
        for i, post in enumerate(posts[:15])
    ]

    return {
        "year": year,
        "difficulty_score": difficulty,
        "label": label,
        "posts_analysed": len(posts),
        "avg_sentiment": round(avg_sentiment, 3),
        "source": "PaGaLGuY + YouTube VADER",
        "sample_posts": sample_posts
    }


# ── Score calculation: NIT quality ────────────────────────────

def calculate_nit_quality(nit_name: str, nit_code: str) -> dict:
    """
    Returns a quality score (0-10) for a NIT, broken into
    placement, campus, and faculty sub-scores, derived from
    VADER sentiment on topic-categorised posts.
    """
    posts = fetch_nit_review_posts(nit_name)

    if not posts:
        return {
            "nit_code": nit_code,
            "nit_name": nit_name,
            "overall_score": 6.0,
            "placement_score": 6.0,
            "campus_score": 6.0,
            "faculty_score": 6.0,
            "posts_analysed": 0,
            "label": "Average",
            "source": "default",
            "sample_posts": []
        }

    placement_posts, campus_posts, faculty_posts = [], [], []

    for post in posts:
        p_lower = post["text"].lower()
        if any(w in p_lower for w in
               ["placement", "job", "company", "recruit", "package", "lpa"]):
            placement_posts.append(post)
        elif any(w in p_lower for w in
                 ["campus", "hostel", "infrastructure", "facility", "lab"]):
            campus_posts.append(post)
        elif any(w in p_lower for w in
                 ["faculty", "professor", "teacher", "research", "prof"]):
            faculty_posts.append(post)

    def avg_score(post_list, fallback):
        target = post_list if post_list else fallback
        if not target:
            return 6.0
        scores = [get_sentiment_score(p["text"]) for p in target]
        avg = sum(scores) / len(scores)
        return round((avg + 1) / 2 * 10, 1)  # map -1..+1 to 0..10

    placement = avg_score(placement_posts, posts)
    campus    = avg_score(campus_posts, posts)
    faculty   = avg_score(faculty_posts, posts)
    overall   = round(placement * 0.5 + campus * 0.3 + faculty * 0.2, 1)

    if overall >= 8:
        label = "Excellent"
    elif overall >= 7:
        label = "Good"
    elif overall >= 5:
        label = "Average"
    else:
        label = "Poor"

    sample_posts = [
        {
            "text": post["text"][:300],
            "source": post["source"],
            "sentiment_score": round(get_sentiment_score(post["text"]), 3)
        }
        for post in posts[:15]
    ]

    return {
        "nit_code": nit_code,
        "nit_name": nit_name,
        "overall_score": overall,
        "placement_score": placement,
        "campus_score": campus,
        "faculty_score": faculty,
        "posts_analysed": len(posts),
        "label": label,
        "source": "PaGaLGuY + YouTube VADER",
        "sample_posts": sample_posts
    }
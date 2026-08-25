import os
import time
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()

# ── VADER analyser ────────────────────────────────────────

analyser = SentimentIntensityAnalyzer()

analyser = SentimentIntensityAnalyzer()

# Extend lexicon with Indian internet slang + emojis
# not well covered by default VADER lexicon
custom_lexicon = {
    "🔥": 2.5,
    "📈": 1.8,
    "op": 2.0,          # "overpowered" = excellent (slang)
    "mast": 2.0,         # Hindi slang: great
    "badhiya": 2.0,       # Hindi slang: good
    "solid": 2.2,
    "worth it": 2.0,
    "waste": -2.5,
    "bekar": -2.0,        # Hindi slang: useless
    "ganda": -2.0,        # Hindi slang: bad
    "chalu": -1.0,        # Hindi slang: mediocre/fake
    "top notch": 3.0,
    "underrated": 1.5,
    "overrated": -1.5,
}
analyser.lexicon.update(custom_lexicon)

def get_sentiment_score(text: str) -> float:
    """Returns compound score: -1 (negative) to +1 (positive)"""
    scores = analyser.polarity_scores(text)
    return scores["compound"]

import re

# ── Filter out noise: rank/cutoff query posts ─────────────

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
    """
    Returns True if post looks like an admission
    rank/cutoff query rather than a genuine opinion.
    """
    text_lower = text.lower().strip()

    # Too short to have real sentiment
    if len(text_lower) < 25:
        return True

    # Mostly digits (rank numbers)
    digit_ratio = sum(c.isdigit() for c in text_lower) / max(len(text_lower), 1)
    if digit_ratio > 0.15:
        return True

    # Matches known noise patterns
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


def filter_opinion_posts(posts: list) -> list:
    """Keep only posts likely to contain real opinions."""
    return [p for p in posts if not is_noise_post(p)]

# ── PaGaLGuY scraper ──────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

def search_pagalguy(query: str, max_results: int = 20):
    """
    Search PaGaLGuY for a query and return thread URLs.
    """
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
    """
    Scrape post text from a single PaGaLGuY thread page.
    """
    if not url.startswith("http"):
        url = "https://www.pagalguy.com" + url

    try:
        time.sleep(2)  # respectful delay
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        posts = []
        # Generic selectors — forum posts usually in <p> or
        # message-body style divs
        for tag in soup.find_all(["p", "div"], class_=True):
            text = tag.get_text(strip=True)
            if len(text) > 40:  # skip short/nav text
                posts.append(text)

        return posts[:10]  # limit per thread
    except Exception as e:
        print(f"Error scraping thread {url}: {e}")
        return []


def fetch_pagalguy_posts(query: str, max_threads: int = 10):
    """
    Full pipeline: search PaGaLGuY, scrape each thread found.
    """
    thread_links = search_pagalguy(query, max_threads)
    all_posts = []
    for link in thread_links:
        posts = scrape_pagalguy_thread(link)
        all_posts.extend(posts)
    return all_posts


# ── YouTube Data API ──────────────────────────────────────

def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    return build("youtube", "v3", developerKey=api_key)


def search_youtube_videos(query: str, max_results: int = 5):
    """
    Search YouTube for videos matching query.
    Returns list of video IDs.
    """
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
        print(f"Error searching YouTube for '{query}': {e}")
        return []


def fetch_youtube_comments(video_id: str, max_comments: int = 50):
    """
    Fetch top-level comments from a YouTube video.
    """
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
        print(f"Error fetching comments for video {video_id}: {e}")
    return comments


def fetch_youtube_posts(query: str, max_videos: int = 5):
    """
    Full pipeline: search YouTube, fetch comments from each video.
    """
    video_ids = search_youtube_videos(query, max_videos)
    all_comments = []
    for vid in video_ids:
        comments = fetch_youtube_comments(vid)
        all_comments.extend(comments)
        time.sleep(0.5)
    return all_comments


# ── Combined fetch: GATE difficulty ───────────────────────

def fetch_gate_difficulty_posts(year: int):
    """
    Combine PaGaLGuY + YouTube for GATE difficulty posts.
    """
    queries = [
        f"GATE {year} paper analysis difficulty",
        f"GATE {year} exam review students reaction",
        f"GATE CSE {year} was it tough or easy"
    ]

    all_posts = []

    for q in queries:
        pagalguy_posts = fetch_pagalguy_posts(q, max_threads=4)
        for p in pagalguy_posts:
            all_posts.append({"text": p, "source": "PaGaLGuY"})

        youtube_posts = fetch_youtube_posts(q, max_videos=3)
        for p in youtube_posts:
            all_posts.append({"text": p, "source": "YouTube"})

    filtered = [
        p for p in all_posts
        if not is_noise_post(p["text"])
    ]

    print(f"Fetched {len(all_posts)} raw posts for GATE {year}, "
          f"{len(filtered)} kept after noise filtering")
    return filtered


# ── Combined fetch: NIT reviews ───────────────────────────

def fetch_nit_review_posts(nit_name: str):
    """
    Combine PaGaLGuY + YouTube for NIT review posts.
    Targets genuine opinions, not admission queries.
    """
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
        pagalguy_posts = fetch_pagalguy_posts(q, max_threads=4)
        for p in pagalguy_posts:
            all_posts.append({"text": p, "source": "PaGaLGuY"})

        youtube_posts = fetch_youtube_posts(q, max_videos=2)
        for p in youtube_posts:
            all_posts.append({"text": p, "source": "YouTube"})

    # Filter out noise (rank/cutoff queries)
    filtered = [
        p for p in all_posts
        if not is_noise_post(p["text"])
    ]

    print(f"Fetched {len(all_posts)} raw posts for {nit_name}, "
          f"{len(filtered)} kept after noise filtering")
    return filtered


# ── Calculate GATE difficulty score ──────────────────────

def calculate_gate_difficulty(year: int) -> dict:
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

    sample_posts = []
    for i, post in enumerate(posts[:15]):
        sample_posts.append({
            "text": post["text"][:300],
            "source": post["source"],
            "sentiment_score": round(scores[i], 3)
        })

    return {
        "year": year,
        "difficulty_score": difficulty,
        "label": label,
        "posts_analysed": len(posts),
        "avg_sentiment": round(avg_sentiment, 3),
        "source": "PaGaLGuY + YouTube VADER",
        "sample_posts": sample_posts
    }

# ── Calculate NIT quality score ───────────────────────────

def calculate_nit_quality(nit_name: str, nit_code: str) -> dict:
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
        return round((avg + 1) / 2 * 10, 1)

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

    sample_posts = []
    for post in posts[:15]:
        sample_posts.append({
            "text": post["text"][:300],
            "source": post["source"],
            "sentiment_score": round(get_sentiment_score(post["text"]), 3)
        })

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
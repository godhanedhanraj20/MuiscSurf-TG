import json
from math import ceil
import re
from typing import Optional
from surftg import LOGGER
from surftg.helper.utilis import clean_file_name
from surftg.config import Telegram
import os
from functools import lru_cache

# Your API key for TMDB
API_KEY = Telegram.TMDB_API
TMDB_LANGUAGE = Telegram.TMDB_LANGUAGE

# Compile regex patterns for better performance
CHANNEL_PATTERN = re.compile(r'@[\w_]+')
HASHTAG_PATTERN = re.compile(r'#\w+')
INDUSTRY_PREFIX_PATTERN = re.compile(r'^(Sandalwood|Tollywood|Bollywood|Kollywood|Mollywood|Dhollywood|Marathi|Punjabi|Bhojpuri|Gujarati|Bengali)\s+', re.IGNORECASE)
WEBSITE_PREFIX_PATTERN = re.compile(r'^(kannadaflix|tamilrockers|tamilmv|moviesda|isaimini|filmyzilla|filmywap|moviesflix|bolly4u|worldfree4u|9xmovies|filmyhit|skymovieshd|cinemavilla|tamilblasters|malayalammovies|teluguflix|hindiflix|marathiflix|southflix|indianflix|desiflix|regionalflix|newmovies|latestmovies|freshmovies|hotmovies|coolmovies|megamovies|ultramovies|primemovies|elitemovies|goldmovies|silvermovies|platinummovies|premiummovies|vipflix|maxflix|ultraflix|superflix|megaflix|primeflix|eliteflix|goldflix|silverflix|platinumflix|premiumflix)\s+', re.IGNORECASE)
MKV_PREFIX_PATTERN = re.compile(r'^(mkvcinemas|mkvmovies|mkvking|mkvhub|mkvrockers|mkvzone|mkvworld|mkvfree|mkvmp4|mkvhd|mkvfull|mkvcinema|mkvmovie|mkvkingdom)\s+', re.IGNORECASE)
FILE_EXT_PATTERN = re.compile(r'\.(mkv|mp4|avi|mov|wmv|flv|webm|ts|m2ts|vob|mpg|mpeg|m4v|3gp|webp)$', re.IGNORECASE)
QUALITY_PATTERN = re.compile(r'\b(1080p|720p|480p|360p|240p|144p|2160p|4K|UHD|HD|SD|HDR|HDR10\+|DV|REMUX|BDREMUX|WEBDL|WEB-DL|WEBRip|BRRip|BluRay|Blu-Ray|DVDRip|DVDScr|CAMRip|HDTC|HDTS|HDCAM|PreDVDRip|TVRip|PROPER|REPACK|EXTENDED|UNRATED|THEATRICAL|DIRECTORS\.CUT|UNCUT|IMAX)\b', re.IGNORECASE)
RELEASE_GROUP_PATTERN = re.compile(r'\[(YTS|YIFY|RARBG|ETRG|EVO|AMZN|NF|HMAX|ATVP|SUNNXT|DSNP|ZEE5|VOOT|SONY|HOTSTAR|PRIME|FUM|ION10|EMBER|SPARKS|DEFLATE|CMRG|NTG|SMURF|MZABI|GHOSTS|APEX|SIGMA|CONVOY|FLUX|CAKES)\]', re.IGNORECASE)
CODEC_PATTERN = re.compile(r'\b(x264|x265|HEVC|h264|h265|VP9|AV1|AVC|AAC|AC3|DTS|DDP5\.1|DDP7\.1|TrueHD|ATMOS|DTS-HD|DTS-X|EAC3|FLAC|MP3|OGG|OPUS)\b', re.IGNORECASE)
LANGUAGE_PATTERN = re.compile(r'\[(Kannada|Hindi|English|Telugu|Tamil|Malayalam|Marathi|Bengali|Gujarati|Punjabi|Bhojpuri|Multi|Dual|Triple)\s*(Audio|Dubbed|Sub|Subs|Subtitle|Subtitles|AAC|Clean|Original|OST)?\]', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'[\(\[\{](\d{4})[\)\]\}]')
STANDALONE_YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
SEASON_EPISODE_PATTERN = re.compile(r'[Ss](?:eason)?\s*\d+\s*[Ee](?:pisode)?\s*\d+', re.IGNORECASE)
SEASON_PATTERN = re.compile(r'[Ss](?:eason)?\s*\d+', re.IGNORECASE)
EPISODE_PATTERN = re.compile(r'[Ee](?:pisode)?\s*\d+', re.IGNORECASE)
SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s-]')
DOT_UNDERSCORE_PATTERN = re.compile(r'[._]')
END_NUMBERS_PATTERN = re.compile(r'\s+\d+$')
HYPHEN_SPACE_PATTERN = re.compile(r'\s+-\s+')

@lru_cache(maxsize=1024)
def clean_title(title: str) -> str:
    """Clean and normalize a title for better matching"""
    # Remove channel names and prefixes
    title = CHANNEL_PATTERN.sub('', title)
    title = HASHTAG_PATTERN.sub('', title)
    title = INDUSTRY_PREFIX_PATTERN.sub('', title)
    title = WEBSITE_PREFIX_PATTERN.sub('', title)
    title = MKV_PREFIX_PATTERN.sub('', title)
    
    # Remove file extensions and quality indicators
    title = FILE_EXT_PATTERN.sub('', title)
    title = QUALITY_PATTERN.sub('', title)
    title = RELEASE_GROUP_PATTERN.sub('', title)
    title = CODEC_PATTERN.sub('', title)
    title = LANGUAGE_PATTERN.sub('', title)
    
    # Remove years and season/episode info
    title = YEAR_PATTERN.sub('', title)
    title = STANDALONE_YEAR_PATTERN.sub('', title)
    title = SEASON_EPISODE_PATTERN.sub('', title)
    title = SEASON_PATTERN.sub('', title)
    title = EPISODE_PATTERN.sub('', title)
    
    # Clean special characters
    title = SPECIAL_CHARS_PATTERN.sub(' ', title)
    title = DOT_UNDERSCORE_PATTERN.sub(' ', title)
    
    # Normalize spaces and hyphens
    title = ' '.join(title.split())
    title = HYPHEN_SPACE_PATTERN.sub('-', title)
    title = END_NUMBERS_PATTERN.sub('', title)
    
    return title.strip()

def extract_year(title: str) -> Optional[int]:
    """Extract year from title if present"""
    # Look for year in parentheses
    year_match = re.search(r'\((\d{4})\)', title)
    if year_match:
        return int(year_match.group(1))
    
    # Look for year at the end
    year_match = re.search(r'(\d{4})$', title)
    if year_match:
        return int(year_match.group(1))
    
    return None

@lru_cache(maxsize=1024)
def clean_file_name(file_name: str) -> str:
    """Clean file name for better matching"""
    # Remove file extension
    file_name = os.path.splitext(file_name)[0]
    
    # Remove prefixes and patterns
    file_name = CHANNEL_PATTERN.sub('', file_name)
    file_name = HASHTAG_PATTERN.sub('', file_name)
    file_name = INDUSTRY_PREFIX_PATTERN.sub('', file_name)
    file_name = WEBSITE_PREFIX_PATTERN.sub('', file_name)
    file_name = MKV_PREFIX_PATTERN.sub('', file_name)
    
    # Remove brackets and quality info
    file_name = re.sub(r'\[.*?\]', '', file_name)
    file_name = re.sub(r'\(.*?\)', '', file_name)
    file_name = re.sub(r'\{.*?\}', '', file_name)
    file_name = QUALITY_PATTERN.sub('', file_name)
    file_name = LANGUAGE_PATTERN.sub('', file_name)
    file_name = CODEC_PATTERN.sub('', file_name)
    
    # Clean special characters
    file_name = SPECIAL_CHARS_PATTERN.sub(' ', file_name)
    file_name = DOT_UNDERSCORE_PATTERN.sub(' ', file_name)
    
    # Normalize spaces and hyphens
    file_name = ' '.join(file_name.split())
    file_name = HYPHEN_SPACE_PATTERN.sub('-', file_name)
    
    return file_name.strip()

# Initialize the TMDBClient
class TMDBClient:
    def __init__(self, client):
        self.client = client
        self.api_key = API_KEY
        self.language = TMDB_LANGUAGE
        self._cache = {}  # Simple in-memory cache for API responses

    @lru_cache(maxsize=1024)
    def get_episode_details(self, tmdb_id: int, episode_number: int, season_number: int = 1) -> dict:
        """Get the details of a specific episode from the API"""
        cache_key = f"episode_{tmdb_id}_{season_number}_{episode_number}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}"
        try:
            response = self.client.get(url, params={'api_key': self.api_key, "language": self.language})
            if response.status_code == 200:
                result = response.json()
                self._cache[cache_key] = result
                return result
        except Exception as e:
            LOGGER.error(f"Error fetching episode details: {str(e)}")
        return {}

    @lru_cache(maxsize=1024)
    def find_media_id(self, title: str, data_type: str, use_api: bool = True, year: Optional[int] = None, adult: bool = False) -> Optional[int]:
        """Get TMDB ID for a title with improved search accuracy"""
        cache_key = f"media_{title}_{data_type}_{year}_{adult}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Clean and prepare the title
        original_title = title
        title = clean_title(title)
        
        if not title:
            LOGGER.warn("The parsed title returned an empty string. Skipping...")
            LOGGER.info("Original Title: %s", original_title)
            return None

        if use_api:
            LOGGER.info("Trying search using API for '%s'", title)
            type_name = "tv" if data_type == "series" else "movie"

            def search_tmdb(query_year, query_title=None):
                params = {
                    "query": query_title or title,
                    "include_adult": adult,
                    "page": 1,
                    "language": self.language,
                    "api_key": self.api_key,
                }
                if query_year:
                    params["primary_release_year"] = query_year

                try:
                    resp = self.client.get(
                        f"https://api.themoviedb.org/3/search/{type_name}", params=params)
                    return resp
                except Exception as e:
                    LOGGER.error(f"API request failed: {str(e)}")
                    return None

            # First attempt: Search with year and original title
            resp = search_tmdb(year)
            if resp and resp.status_code == 200:
                results = resp.json().get("results", [])
                
                # If no results with year, try without year
                if not results and year:
                    LOGGER.warn(f"No results found for '{title}' with year {year}. Retrying without year.")
                    resp = search_tmdb(None)
                    if resp and resp.status_code == 200:
                        results = resp.json().get("results", [])

                # If still no results, try with cleaned title
                if not results:
                    LOGGER.warn(f"No results found for '{title}'. Trying with cleaned title.")
                    resp = search_tmdb(None, clean_title(title))
                    if resp and resp.status_code == 200:
                        results = resp.json().get("results", [])

                if results:
                    # Score results based on title match and year
                    scored_results = []
                    for result in results:
                        score = 0
                        result_title = result.get("title" if type_name == "movie" else "name", "").lower()
                        original_title_lower = original_title.lower()
                        cleaned_title_lower = title.lower()
                        
                        # Exact match bonus
                        if result_title == cleaned_title_lower:
                            score += 100
                        # Partial match score
                        elif cleaned_title_lower in result_title:
                            score += 50
                        # Check if result title is in original title (handles prefixes)
                        elif result_title in original_title_lower:
                            score += 40
                        # Check if cleaned title is in result title
                        elif cleaned_title_lower in result_title:
                            score += 30
                        
                        # Year match bonus
                        if year:
                            release_date = result.get("release_date" if type_name == "movie" else "first_air_date", "")
                            if release_date and release_date.startswith(str(year)):
                                score += 30
                        
                        # Popularity bonus
                        score += result.get("popularity", 0) / 10
                        
                        scored_results.append((score, result))

                    # Sort by score and get the best match
                    scored_results.sort(reverse=True, key=lambda x: x[0])
                    if scored_results:
                        best_match = scored_results[0][1]
                        LOGGER.debug(f"Best match for '{title}': {best_match.get('title' if type_name == 'movie' else 'name')} (score: {scored_results[0][0]})")
                        result_id = best_match["id"]
                        self._cache[cache_key] = result_id
                        return result_id

            else:
                LOGGER.warn(f"API search failed for '{title}' - The API said '{resp.json().get('errors', 'No error message provided')}' with status code {resp.status_code}")
        return None

    @lru_cache(maxsize=1024)
    def get_details(self, tmdb_id: int, data_type: str) -> dict:
        """Get the details of a movie/series from the API"""
        cache_key = f"details_{tmdb_id}_{data_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        type_name = "tv" if data_type == "series" else "movie"
        url = f"https://api.themoviedb.org/3/{type_name}/{tmdb_id}"
        if type_name == "tv":
            params = {
                "include_image_language": self.language,
                "append_to_response": "credits,images,external_ids,videos,reviews,content_ratings",
                "api_key": self.api_key,
                "language": self.language
            }
        else:
            params = {
                "include_image_language": self.language,
                "append_to_response": "credits,images,external_ids,videos,reviews",
                "api_key": self.api_key,
                "language": self.language
            }
        try:
            response = self.client.get(url, params=params).json()
            self._cache[cache_key] = response
            return response
        except Exception as e:
            LOGGER.error(f"Error fetching details: {str(e)}")
            return {}

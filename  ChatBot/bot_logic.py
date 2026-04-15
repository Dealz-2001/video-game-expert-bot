"""
Title: Final Bot Logic for Video Game Expert Bot (Fully Upgraded)
Author: Camden Konopka, Benjamin Dealy and Fionn Darcy
Description:
A full-featured video game knowledge bot with:
- CSV database loading & updating
- Alias + fuzzy title matching
- Genre, platform, publisher, release date, and sales queries
- DLC detection
- Franchise grouping
- Platform-exclusive searching
- Publisher-exclusive searching
- Multi-genre filtering
- Platform + genre filtering
- Sales-based ranking
- Release-year range filtering
- "Games like X" similarity engine
- Heuristic recommendation engine ("ML-style" recommendations)
- Admin mode for adding new games
- Logging of recognized/unrecognized inputs
"""

import os
import pandas as pd
import csv
import time
import datetime
import re
from thefuzz import process, fuzz

# ==============================
# CONFIGURATION & GLOBAL STATE
# ==============================

# File paths for database and logging
# DB_FILE: stores all game data in CSV format
# LOG_RECOGNIZED: logs when user queries are successfully matched
# LOG_UNRECOGNIZED: logs when user queries don't match any games
DB_FILE = 'games_database.csv'
LOG_RECOGNIZED = 'recognized_inputs.csv'
LOG_UNRECOGNIZED = 'unrecognized_inputs.csv'
# Admin password required to add new games to the database
ADMIN_PASSWORD = "ExpertBot2024"

# Session state maintains conversation context for "Did you mean?" flows
# last_suggestion: stores the fuzzy-matched game title offered to user
# original_query: stores the original user input that triggered the suggestion
session_state = {"last_suggestion": None, "original_query": None}

# ==============================
# DATABASE INITIALIZATION
# ==============================

def initialize_database():
    """
    Create default games_database.csv if it doesn't exist with sample game data.
    This ensures the bot has a functional database on first run.
    Includes 8 sample games with complete metadata.
    """
    if not os.path.exists(DB_FILE):
        data = {
            'Title': ['Minecraft', 'Elden Ring', 'The Witcher 3', 'Valorant', 'CS2', 'Grand Theft Auto V', 'Stardew Valley', 'Cyberpunk 2077'],
            'Aliases': ['mc', 'er', 'tw3, witcher 3', 'val', 'counter strike 2', 'gtav, gta v, gta5', 'sv', 'cp2077, cp77'],
            'Description': [
                'A sandbox game about building and exploring.', 'An open-world action RPG.',
                'A story-driven open-world RPG.', 'A 5v5 tactical shooter.',
                'A premier tactical shooter.', 'An expansive open-world action game.',
                'A cozy farming simulation game.', 'An open-world adventure RPG.'
            ],
            'Genre': ['Sandbox', 'Action RPG', 'RPG', 'Tactical Shooter', 'FPS', 'Action', 'Simulation', 'RPG'],
            'Platform': [
                'PC, Xbox, PlayStation, Switch',
                'PC, Xbox, PlayStation',
                'PC, Xbox, PlayStation, Switch',
                'PC',
                'PC',
                'PC, Xbox, PlayStation',
                'PC, Switch, PlayStation, Xbox',
                'PC, Xbox, PlayStation'
            ],
            'Publisher': ['Mojang Studios', 'Bandai Namco', 'CD Projekt', 'Riot Games', 'Valve', 'Rockstar Games', 'ConcernedApe', 'CD Projekt'],
            'Release date': ['Nov 18, 2011', 'Feb 25, 2022', 'May 19, 2015', 'Jun 2, 2020', 'Sep 27, 2023', 'Sep 17, 2013', 'Feb 26, 2016', 'Dec 10, 2020'],
            'Sales': ['350 million', '30 million', '50 million', 'Free-to-play', 'Free-to-play', '200 million', '30 million', '25 million']
        }
        pd.DataFrame(data).to_csv(DB_FILE, index=False)

def load_game_data():
    """
    Load all games from CSV file and convert to list of dictionaries.
    Each dictionary represents one game with keys: Title, Aliases, Description, etc.
    Returns empty list if CSV file cannot be read.
    """
    try:
        df = pd.read_csv(DB_FILE)
        return df.to_dict('records')
    except:
        return []

# Initialize database (creates it if missing) and load game records into memory
initialize_database()
game_records = load_game_data()

# ==============================
# LOGGING & CSV UPDATE HELPERS
# ==============================

def log_input(filename, user_text, status):
    """
    Append user input to specified log file with timestamp.
    Creates CSV headers if file doesn't exist yet.
    Useful for tracking bot usage patterns and improving responses.
    
    Args:
        filename: Path to log CSV file (LOG_RECOGNIZED or LOG_UNRECOGNIZED)
        user_text: The user's query text
        status: Status label (e.g., "Recognized", "Rejected Suggestion")
    """
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Add header row if file is new
        if not file_exists:
            writer.writerow(['Timestamp', 'Input', 'Status'])
        # Append new row with current timestamp and user data
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), user_text, status])

def add_game_to_csv(title, aliases, desc, genre, platform, publisher, date, sales):
    """
    Add a new game to the database via CSV file.
    After adding, reloads all game_records from file to sync changes in memory.
    Intended for use by admin users who authenticate with password.
    
    Args:
        title: Game title
        aliases: Comma-separated alternative names/abbreviations
        desc: Short game description
        genre: Genre category
        platform: Available platforms (comma-separated)
        publisher: Publishing company name
        date: Release date string
        sales: Sales figures or "Free-to-play"
    
    Returns:
        Success message confirming game was added
    """
    global game_records
    with open(DB_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([title, aliases, desc, genre, platform, publisher, date, sales])
    # Reload records from file to ensure in-memory state matches disk
    game_records = load_game_data()
    return f"Success! Added '{title}' to database."

# ==============================
# PARSING & SCORING HELPERS
# ==============================

def parse_sales(sales_str):
    """
    Convert human-readable sales strings to numeric millions for comparison.
    Handles formats like '200 million', '4 billion', 'Free-to-play'.
    Used for sorting games by popularity/profitability.
    
    Examples:
        '350 million' -> 350.0
        '4 billion' -> 4000.0
        'Free-to-play' -> 0.0
    
    Returns:
        Float value in millions (0.0 if non-numeric or free-to-play)
    """
    s = str(sales_str).lower()
    # Extract first numeric value (integer or decimal)
    m = re.search(r'(\d+(\.\d+)?)', s)
    if not m:
        return 0.0
    val = float(m.group(1))
    # Scale billion values to millions
    if "billion" in s:
        val *= 1000.0
    return val

# ==============================
# FEATURE HELPERS
# ==============================

def is_dlc(game):
    """
    Determine if a game is DLC/expansion content.
    Checks title and description for keywords like 'dlc', 'expansion', 'pack'.
    Used to answer queries like "Is this DLC?"
    
    Args:
        game: Dictionary representing a game record
    
    Returns:
        True if game appears to be DLC/expansion, False otherwise
    """
    title = str(game.get('Title', '')).lower()
    desc = str(game.get('Description', '')).lower()
    dlc_keywords = ["dlc", "expansion", "pack", "season", "story expansion"]
    return any(k in title or k in desc for k in dlc_keywords)

def get_franchise_key(title):
    """
    Extract franchise base name from game title.
    Handles titles with colons (e.g., "Witcher 3: Wild Hunt") -> "Witcher 3".
    Falls back to first word if title is malformed.
    
    Args:
        title: Full game title string
    
    Returns:
        Franchise base name (typically first part before colon or first word)
    """
    base = title.split(":")[0].strip()
    if not base:
        base = title.split()[0]
    return base

def get_franchise_games(game, all_games):
    """
    Find all other games in same franchise by matching franchise key prefix.
    Used to answer queries like "What other games in this franchise?"
    
    Args:
        game: Dictionary of the reference game
        all_games: List of all game records to search
    
    Returns:
        List of game titles that share the same franchise prefix
    """
    key = get_franchise_key(str(game['Title']))
    return [g['Title'] for g in all_games if g is not game and str(g['Title']).startswith(key)]

def is_exclusive_to_platform(platform_str, target):
    """
    Check if a game is exclusive to only one specific platform.
    A game is exclusive only if it's ONLY on that platform (not on others).
    
    Args:
        platform_str: Platforms string from game record (comma-separated)
        target: Platform to check exclusivity for ('pc', 'xbox', 'playstation', 'switch', 'mobile')
    
    Returns:
        True only if game is available ONLY on target platform
    """
    p = platform_str.lower()
    has_pc = "pc" in p
    has_xbox = "xbox" in p
    has_playstation = "ps" in p or "playstation" in p
    has_switch = "switch" in p
    has_mobile = "mobile" in p

    # Returns True only if platform is available on target AND NOT others
    if target == "pc":
        return has_pc and not (has_xbox or has_playstation or has_switch or has_mobile)
    if target == "playstation":
        return has_playstation and not (has_pc or has_xbox or has_switch or has_mobile)
    if target == "xbox":
        return has_xbox and not (has_pc or has_playstation or has_switch or has_mobile)
    if target == "switch":
        return has_switch and not (has_pc or has_xbox or has_playstation or has_mobile)
    if target == "mobile":
        return has_mobile and not (has_pc or has_xbox or has_playstation or has_switch)
    return False

def is_publisher_exclusive(game, target_pub):
    """
    Check if a game is published by a specific publisher (case-insensitive).
    Used to find all games from a particular company.
    
    Args:
        game: Game record dictionary
        target_pub: Publisher name to check against
    
    Returns:
        True if game's publisher matches target (case-insensitive)
    """
    return str(game.get('Publisher', '')).lower() == target_pub.lower()

def matches_all_genres(game, genre_words):
    """
    Check if a game's genre contains ALL specified words.
    Strict matching for multi-genre filters (e.g., "action rpg").
    
    Args:
        game: Game record dictionary
        genre_words: List of genre keywords to match
    
    Returns:
        True only if game's genre text contains all words
    """
    genre_text = str(game['Genre']).lower()
    return all(word in genre_text for word in genre_words)

def matches_platform_and_genre(game, platform_word, genre_word):
    """
    Check if a game is available on specified platform AND matches genre.
    Used for combined platform+genre searches.
    
    Args:
        game: Game record dictionary
        platform_word: Platform to check (e.g., 'pc', 'xbox')
        genre_word: Genre to check (e.g., 'action', 'rpg')
    
    Returns:
        True if game is on platform AND has genre
    """
    return platform_word in str(game['Platform']).lower() and genre_word in str(game['Genre']).lower()

def similarity_score(base_game, other_game):
    """
    Calculate how similar two games are based on multiple factors.
    Higher score = more similar. Used for "Games like X" recommendations.
    
    Scoring breakdown:
    - Shared genre words: 2.0 points each
    - Same publisher: 1.5 points
    - Shared platforms: 0.5 points each
    - Sales popularity: 0 to N points (sales / 200)
    
    Args:
        base_game: Reference game to compare against
        other_game: Game to score for similarity
    
    Returns:
        Float score indicating overall similarity
    """
    score = 0.0
    # Split genres into words for comparison
    base_genre = str(base_game['Genre']).lower().split()
    other_genre = str(other_game['Genre']).lower().split()

    # Award points for each shared genre word
    shared_genres = set(base_genre) & set(other_genre)
    score += 2.0 * len(shared_genres)

    # Award points if same publisher
    if str(base_game['Publisher']).lower() == str(other_game['Publisher']).lower():
        score += 1.5

    # Award points for each shared platform
    base_plats = set([p.strip().lower() for p in str(base_game['Platform']).split(",")])
    other_plats = set([p.strip().lower() for p in str(other_game['Platform']).split(",")])
    shared_plats = base_plats & other_plats
    score += 0.5 * len(shared_plats)

    # Award points based on other game's sales popularity
    score += parse_sales(other_game['Sales']) / 200.0

    return score

def get_similar_games(game, all_games, top_n=10):
    """
    Find games similar to a given game using similarity scoring.
    Returns top N most similar games sorted by score descending.
    
    Args:
        game: Reference game to find similarities for
        all_games: List of all games to search
        top_n: Maximum number of similar games to return (default 10)
    
    Returns:
        List of top N similar game titles (empty if none found)
    """
    scored = []
    for g in all_games:
        if g is game:
            continue
        s = similarity_score(game, g)
        if s > 0:
            scored.append((g, s))
    # Sort by score descending and return top N titles
    scored.sort(key=lambda x: x[1], reverse=True)
    return [g['Title'] for g, _ in scored[:top_n]]

def recommend_games_from_preferences(msg, all_games, top_n=10):
    """
    Heuristic recommendation engine that scores games based on user message.
    Extracts genre and platform keywords from message, scores games accordingly.
    Combines keyword matching with sales popularity for recommendations.
    
    Scoring logic:
    - +2.0 points for each desired genre mentioned in game
    - +1.5 points for each desired platform available
    - +sales/200 points for sales popularity
    
    Args:
        msg: User message containing preferences
        all_games: List of all games to score and recommend
        top_n: Maximum number of recommendations (default 10)
    
    Returns:
        List of top N recommended game titles
    """
    msg = msg.lower()
    # Define known genre and platform keywords to search for
    genre_keywords = ["action", "rpg", "shooter", "fps", "strategy", "horror", "survival", "simulation",
                      "sandbox", "platformer", "racing", "sports", "tactical", "co-op", "adventure"]
    platform_keywords = ["pc", "xbox", "playstation", "ps4", "ps5", "switch", "nintendo", "mobile"]

    # Extract user preferences mentioned in message
    desired_genres = [g for g in genre_keywords if g in msg]
    desired_platforms = [p for p in platform_keywords if p in msg]

    # Score each game based on preference matches
    scored = []
    for g in all_games:
        score = 0.0
        genre_text = str(g['Genre']).lower()
        plat_text = str(g['Platform']).lower()

        # Award points for matching each desired genre
        for dg in desired_genres:
            if dg in genre_text:
                score += 2.0

        # Award points for matching each desired platform
        for dp in desired_platforms:
            if dp in plat_text:
                score += 1.5

        # Award points based on sales popularity
        score += parse_sales(g['Sales']) / 200.0

        if score > 0:
            scored.append((g, score))

    # Return top N games sorted by score (highest first)
    scored.sort(key=lambda x: x[1], reverse=True)
    return [g['Title'] for g, _ in scored[:top_n]]

# ==============================
# MAIN RESPONSE LOGIC
# ==============================

def get_response(user_message):
    """
    Main bot response function that processes user input and returns appropriate response.
    Uses a cascading series of checks in priority order:
    
    A. "Did you mean?" flow - handles user confirmation/rejection of suggestions
    B. Admin commands - adds new games to database (password-protected)
    C. Small talk - responds to greetings and polite phrases
    D. Global utilities - time, help, recommendations
    D.1-D.2. Platform and publisher exclusivity searches
    E. Title + alias searches - exact game matches and their features
    F. Year/date range searches - games released in specific periods
    F.5-F.7. Genre filtering - category-based searches
    G. Fuzzy matching - attempts to correct misspelled game names
    H. Fallback - returns "I don't know" message
    """
    global session_state, game_records
    raw_msg = user_message.strip()
    msg = raw_msg.lower()

    # ============ A. "Did you mean?" flow ============
    # Handles user response to fuzzy match suggestions from previous query
    if session_state["last_suggestion"]:
        suggestion = session_state["last_suggestion"]
        orig_query = session_state["original_query"]

        # If user confirms suggestion (yes/yeah/yep/sure), search for that game
        if any(word in msg for word in ["yes", "yeah", "yep", "sure"]):
            session_state = {"last_suggestion": None, "original_query": None}
            # Recursively call get_response with suggested game name
            return get_response(f"{suggestion} {orig_query}")

        # If user rejects suggestion (no/nope/nah), log and give feedback
        if any(word in msg for word in ["no", "nope", "nah"]):
            session_state = {"last_suggestion": None, "original_query": None}
            log_input(LOG_UNRECOGNIZED, orig_query, "Rejected Suggestion")
            return "Okay, I've noted that. I'll try to learn that game soon!"

    # ============ B. Admin commands ============
    # Allows authenticated users to add new games (requires password)
    if msg.startswith("admin:"):
        try:
            # Parse password and command from message
            auth_part, cmd_part = raw_msg.split(" ", 1)
            # Verify password matches and command starts with "add game:"
            if auth_part.split(":")[-1] == ADMIN_PASSWORD and cmd_part.lower().startswith("add game:"):
                # Extract and split game fields (8 comma-separated values)
                parts = [p.strip() for p in cmd_part[9:].split(",")]
                if len(parts) == 8:
                    log_input(LOG_RECOGNIZED, raw_msg, "Admin Add")
                    return add_game_to_csv(*parts)
            return "Access Denied or Invalid Format."
        except:
            return "Format: admin:PASSWORD add game: Title, Aliases, Desc, Genre, Platform, Pub, Date, Sales"

        # ============ C. Small talk ============
    # Responds only when the message STARTS with a greeting
    GENERAL_RESPONSES = {
        "hi": "Hello! What game would you like to know about.",
        "hello": "Hey there. Ask me about any video game.",
        "how are you": "I'm running smoothly and ready to talk games.",
        "thanks": "You're welcome.",
        "thank you": "Happy to help."
    }

    # Only trigger small talk if the message BEGINS with the greeting
    for key, reply in GENERAL_RESPONSES.items():
        if msg.startswith(key):
            return reply


    # ============ D. Global utilities ============
    # Handle time request
    if "time" in msg:
        return f"The current time is {time.strftime('%H:%M')}."

    # Handle help request
    if "help" in msg:
        return "You can ask about games, genres, platforms, publishers, DLC, franchises, years, or say 'recommend me some [genre] games'."

        # ============ D.-1 List all franchises (NEW FEATURE) ============
    # Allows the bot to answer:
    # "list all franchises", "what franchises do you know", "show franchises"
    if "list franchises" in msg or "what franchises" in msg or "franchises" in msg:
        # Build a dictionary mapping franchise keys to all titles in that franchise
        franchise_map = {}

        for g in game_records:
            key = get_franchise_key(g['Title'])
            franchise_map.setdefault(key, []).append(g['Title'])

        # Format output nicely
        lines = []
        for key, titles in franchise_map.items():
            if len(titles) > 1:
                lines.append(f"{key}: {', '.join(titles)}")
            else:
                lines.append(f"{key}: {titles[0]}")

        return "Here are the franchises I know:\n" + "\n".join(lines)


        # ============ D.0 Top-selling games by genre  ============
    # Handles queries like "top selling action games" or "best selling rpgs"
    if "top selling" in msg and any(g in msg for g in ["action", "rpg", "shooter", "fps", "strategy", "horror",
                                                       "survival", "simulation", "sandbox", "platformer",
                                                       "racing", "sports", "tactical", "adventure"]):
        # Detect which genre the user asked for
        genre_word = None
        for g in ["action", "rpg", "shooter", "fps", "strategy", "horror", "survival",
                  "simulation", "sandbox", "platformer", "racing", "sports", "tactical", "adventure"]:
            if g in msg:
                genre_word = g
                break

        # Filter games by genre
        matches = [g for g in game_records if genre_word in g['Genre'].lower()]

        if matches:
            matches.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
            top = [f"{g['Title']} ({g['Sales']})" for g in matches[:10]]
            return f"Top-selling {genre_word.title()} games:\n" + "\n".join(top)
     
      # ============ D.1 Top-selling franchises ============
    if "top selling franchises" in msg or "best franchises" in msg:
        # Build franchise → total sales map
        franchise_sales = {}

        for g in game_records:
            key = get_franchise_key(g['Title'])
            franchise_sales.setdefault(key, 0)
            franchise_sales[key] += parse_sales(g['Sales'])

        # Sort franchises by total sales
        sorted_franchises = sorted(franchise_sales.items(), key=lambda x: x[1], reverse=True)

        # Format top 10
        top = [f"{name} ({sales:.1f} million total)" for name, sales in sorted_franchises[:10]]

        return "Top-selling franchises:\n" + "\n".join(top)


    # ============ D.2 Global franchise listing  ============
    # Allows the bot to answer questions like:
    # "What franchises do you know?" or "List franchises"
    if "franchises" in msg or "list franchises" in msg or "what franchises" in msg:
        # Build a dictionary mapping franchise keys to all titles in that franchise
        franchise_map = {}

        for g in game_records:
            key = get_franchise_key(g['Title'])
            franchise_map.setdefault(key, []).append(g['Title'])

        # Format the output nicely
        formatted = []
        for key, titles in franchise_map.items():
            if len(titles) > 1:
                formatted.append(f"{key}: {', '.join(titles)}")
            else:
                formatted.append(f"{key}: {titles[0]}")

        return "Here are the franchises I know:\n" + "\n".join(formatted)
       
    # ============ D.3 Top-selling games  ============
    # Allows the bot to answer questions like:
    # "What are the top selling games?" or "Show best sellers"
    if "top selling" in msg or "best selling" in msg or "top games" in msg or "best games" in msg:
        # Sort all games by numeric sales value (highest first)
        sorted_games = sorted(game_records, key=lambda g: parse_sales(g['Sales']), reverse=True)

        # Take the top 10 best sellers
        top_titles = [f"{g['Title']} ({g['Sales']})" for g in sorted_games[:10]]

        return (
            "Here are the top-selling games I know:\n"
            + "\n".join(top_titles)
        )



    # ============ D.4 Recommendation queries ============
    # Heuristic ML-style recommendations based on user preferences
    if "recommend" in msg or "suggest" in msg:
        # Try to recommend based on detected preferences (genre/platform)
        recs = recommend_games_from_preferences(msg, game_records, top_n=10)
        if recs:
            return (
                f"Based on what you asked for, here are some games I recommend: "
                f"{', '.join(recs)}."
            )
        # Fallback: show top-selling games if no preference detected
        sorted_by_sales = sorted(game_records, key=lambda g: parse_sales(g['Sales']), reverse=True)
        top = [g['Title'] for g in sorted_by_sales[:10]]
        return (
            "I couldn't detect a specific genre or platform, so here are some of the biggest hits: "
            f"{', '.join(top)}."
        )

    
    # ============ D.5 Publisher-exclusive search ============
    # Find all games from a specific publisher
    known_publishers = list({g['Publisher'] for g in game_records})
    if "exclusive" in msg and "publisher" in msg:
        # Check if any known publisher is mentioned in the message
        for pub in known_publishers:
            if pub.lower() in msg:
                matches_games = [g for g in game_records if is_publisher_exclusive(g, pub)]
                if matches_games:
                    # Sort by sales and return top 20
                    matches_games.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
                    titles = [g['Title'] for g in matches_games[:20]]
                    return (
                        f"I found {len(matches_games)} games exclusively published by {pub}. "
                        f"Some examples include: {', '.join(titles)}."
                    )

    # ============ E. Title + alias search ============
    # Exact match for known game titles and their aliases
    for game in game_records:
        title = game['Title'].lower()
        # Parse aliases (comma-separated) into list
        aliases = [a.strip().lower() for a in str(game.get('Aliases', '')).split(',')]

        found = False
        # Check if game title matches message using word boundary regex
        if re.search(rf'\b{re.escape(title)}\b', msg):
            found = True
        else:
            # Check if any alias matches
            for alias in aliases:
                if alias and re.search(rf'\b{re.escape(alias)}\b', msg):
                    found = True
                    break

        if found:
            # ---- E.1 "Games like X" / similarity search ----
            # User asking for similar games
            if any(k in msg for k in ["like this", "like that", "like it", "like this game", "similar", "games like", "like "+title]):
                sims = get_similar_games(game, game_records, top_n=10)
                if sims:
                    return (
                        f"If you like {game['Title']}, you might also enjoy: "
                        f"{', '.join(sims)}."
                    )

            # ---- E.2 DLC detection ----
            # User asking if game is DLC
            if any(k in msg for k in ["dlc", "expansion", "add-on", "addon", "pack"]):
                if is_dlc(game):
                    return f"Yes — '{game['Title']}' is DLC or an expansion."
                else:
                    return f"'{game['Title']}' is a main game, not DLC."

            # ---- E.3 Franchise grouping ----
            # User asking about other games in same franchise/series
            if any(k in msg for k in ["franchise", "series", "other games", "same series"]):
                related = get_franchise_games(game, game_records)
                if related:
                    return (
                        f"'{game['Title']}' is part of the {get_franchise_key(game['Title'])} franchise. "
                        f"Other entries include: {', '.join(related[:20])}."
                    )
                else:
                    return f"I couldn't find other games in the same franchise."

            # ---- E.4 Platform information ----
            # User asking what platforms game is available on
            if any(k in msg for k in ["platform", "play on", "available on", "console"]):
                return f"You can play {game['Title']} on: {game['Platform']}."

            # ---- E.5 Publisher information ----
            # User asking who published the game
            if "publisher" in msg or "published" in msg:
                return f"{game['Title']} was published by {game['Publisher']}."

            # ---- E.6 Release date information ----
            # User asking when game was released
            if any(k in msg for k in ["released", "when", "date", "year"]):
                return f"{game['Title']} released on {game['Release date']}."

            # ---- E.7 Sales information ----
            # User asking about game sales figures
            if any(k in msg for k in ["sales", "sold", "many"]):
                return f"{game['Title']} has sold {game['Sales']}."

            # ---- E.8 Default: return all information ----
            # If no specific query type detected, return full game info
            return (
                f"{game['Title']}: {game['Description']} "
                f"(Genre: {game['Genre']}, Platforms: {game['Platform']}, Sales: {game['Sales']})"
            )

    # ============ F. Year / year-range search ============
    # Find games released in specific years or year ranges
    year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', msg)
    if year_matches:
        years_int = sorted({int(y) for y in year_matches})
        # Check for year range (e.g., "between 2020 and 2023")
        if len(years_int) >= 2 and any(w in msg for w in ["between", "from", "to", "-"]):
            start, end = years_int[0], years_int[-1]
            matches_games = []
            # Find games released within range
            for g in game_records:
                rd = str(g['Release date'])
                m = re.search(r'(19\d{2}|20\d{2})', rd)
                if m:
                    y = int(m.group(1))
                    if start <= y <= end:
                        matches_games.append(g)
            if matches_games:
                # Sort by sales and return top 20
                matches_games.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
                titles = [g['Title'] for g in matches_games[:20]]
                return (
                    f"Between {start} and {end}, I found {len(matches_games)} games. "
                    f"Some of the bigger ones are: {', '.join(titles)}."
                )
        else:
            # Single year search
            year = years_int[0]
            matches_games = []
            # Find games released in this year
            for g in game_records:
                if str(year) in str(g['Release date']):
                    matches_games.append(g)
            if matches_games:
                # Sort by sales and return top 20
                matches_games.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
                titles = [g['Title'] for g in matches_games[:20]]
                return (
                    f"I found {len(matches_games)} games released in {year}. "
                    f"Some of them are: {', '.join(titles)}."
                )

    # ============ F.5 Multi-genre filtering ============
    # Find games matching multiple genre keywords simultaneously
    genre_words = [w for w in msg.split() if len(w) > 3]
    multi_matches = [
        g for g in game_records
        if genre_words and matches_all_genres(g, genre_words)
    ]
    if multi_matches and len(genre_words) > 1:
        # Sort by sales and return top 20
        multi_matches.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
        titles = [g['Title'] for g in multi_matches[:20]]
        return (
            f"I found {len(multi_matches)} games that match all of these genres: "
            f"{', '.join(genre_words)}. "
            f"Here are some examples: {', '.join(titles)}."
        )

    # ============ F.6 Platform + genre filtering ============
    # Find games on specific platform with specific genre
    platforms = ["pc", "xbox", "playstation", "ps4", "ps5", "switch", "nintendo"]
    genres = ["action", "rpg", "shooter", "fps", "strategy", "horror", "survival", "simulation",
              "sandbox", "platformer", "racing", "sports", "tactical", "adventure"]

    # Check all platform/genre combinations mentioned in message
    for p in platforms:
        if p in msg:
            for g_word in genres:
                if g_word in msg:
                    matches_games = [
                        x for x in game_records
                        if matches_platform_and_genre(x, p, g_word)
                    ]
                    if matches_games:
                        # Sort by sales and return top 20
                        matches_games.sort(key=lambda x: parse_sales(x['Sales']), reverse=True)
                        titles = [x['Title'] for x in matches_games[:20]]
                        return (
                            f"I found {len(matches_games)} {p.title()} {g_word.title()} games. "
                            f"Some notable ones include: {', '.join(titles)}."
                        )

    # ============ F.7 Partial-genre search ============
    # Find games matching any single genre keyword mentioned
    for word in msg.split():
        if len(word) < 4:
            continue
        # Check if word appears in any game's genre field
        matches_games = [g for g in game_records if word in g['Genre'].lower()]
        if matches_games:
            # Sort by sales and return top 20
            matches_games.sort(key=lambda g: parse_sales(g['Sales']), reverse=True)
            titles = [g['Title'] for g in matches_games[:20]]
            return (
                f"I found {len(matches_games)} games related to '{word}'. "
                f"Here are some examples: {', '.join(titles)}."
            )

    # ============ G. Fuzzy matching fallback ============
    # Attempt to correct misspelled or close game names using fuzzy matching
    all_titles = [g['Title'] for g in game_records]
    # Use partial_ratio scorer to match partial strings
    best_match, score = process.extractOne(msg, all_titles, scorer=fuzz.partial_ratio)

    # Only suggest if match quality is reasonably high (>75%)
    if score > 75:
        # Store suggestion state for "Did you mean?" flow (section A)
        session_state["last_suggestion"] = best_match
        session_state["original_query"] = raw_msg
        return f"I couldn't find an exact match for '{raw_msg}'. Did you mean {best_match}."

    # ============ H. Final fallback ============
    # User input not recognized by any of the above patterns
    return "I'm sorry, I don't know about that game or category yet."

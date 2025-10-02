"""Search utilities for fuzzy matching."""

from typing import List, Tuple
from rdtui.models.torrent import TorrentRow


def simple_fuzzy_score(query: str, text: str) -> int:
    """
    Simple fuzzy matching score without external dependencies.
    
    Returns a score from 0-100 based on:
    - Exact match: 100
    - Contains query: 80
    - All characters present in order: 60
    - Partial match: 40
    - No match: 0
    """
    query = query.lower()
    text = text.lower()
    
    # Exact match
    if query == text:
        return 100
    
    # Contains query
    if query in text:
        # Bonus for match at start
        if text.startswith(query):
            return 95
        return 80
    
    # Check if all characters from query appear in order in text
    query_idx = 0
    for char in text:
        if query_idx < len(query) and char == query[query_idx]:
            query_idx += 1
    
    if query_idx == len(query):
        # All characters found in order
        return 60
    
    # Check how many characters match
    matches = sum(1 for c in query if c in text)
    if matches > 0:
        return int(40 * (matches / len(query)))
    
    return 0


def fuzzy_search(
    query: str, 
    items: List[TorrentRow], 
    threshold: int = 40
) -> List[Tuple[int, TorrentRow]]:
    """
    Search items using fuzzy matching.
    
    Args:
        query: Search query string
        items: List of TorrentRow objects to search
        threshold: Minimum score to include (0-100)
    
    Returns:
        List of (score, item) tuples, sorted by score descending
    """
    if not query.strip():
        # Empty query - return all with max score
        return [(100, item) for item in items]
    
    results = []
    for item in items:
        score = simple_fuzzy_score(query, item.filename)
        if score >= threshold:
            results.append((score, item))
    
    # Sort by score descending
    results.sort(reverse=True, key=lambda x: x[0])
    
    return results


def highlight_match(query: str, text: str, max_length: int = 50) -> str:
    """
    Highlight matching parts of text (for display).
    
    Args:
        query: Search query
        text: Text to highlight
        max_length: Maximum length of result
    
    Returns:
        Text with matching parts marked (for Rich Text formatting)
    """
    if not query:
        return text[:max_length]
    
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Find the position of the match
    pos = text_lower.find(query_lower)
    
    if pos >= 0:
        # Match found - show context around it
        start = max(0, pos - 10)
        end = min(len(text), pos + len(query) + 30)
        
        result = text[start:end]
        if start > 0:
            result = "..." + result
        if end < len(text):
            result = result + "..."
        
        return result
    
    # No direct match - just truncate
    return text[:max_length] + ("..." if len(text) > max_length else "")


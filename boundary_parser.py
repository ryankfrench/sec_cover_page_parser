"""
Boundary Parser - A utility for parsing text boundaries and word groups.

This module provides functionality to parse text files by identifying and analyzing
groups of words separated by whitespace. It determines the location and boundaries
of these word groups within the document, which can then be used for pattern matching
and content extraction.

The parser works by:
1. Identifying word groups based on whitespace separation
2. Determining the boundaries and positions of these groups
3. Creating a mapping between normalized positions (after tab expansion) and original positions
4. Enabling precise matching of word groups across the document

This approach is particularly useful for:
- Finding related content across different parts of a document
- Matching labels with their corresponding values
- Extracting structured data from formatted text
- Analyzing document layout and content organization

The module handles both space and tab-based formatting, normalizing positions
to ensure consistent boundary detection regardless of the original formatting.
"""

import re
from typing import List, Dict, Tuple, Optional, Union

class ContentGroup:
    """
    A class representing a group of content within a text document.
    
    This class stores information about a contiguous group of text, including
    its content, line number, and character positions within that line.
    
    Attributes:
        content (str): The actual text content of the group
        line (int): The line number where this content appears
        char_start (int): The starting character position within the line
        char_end (int): The ending character position within the line
    """
    
    def __init__(self, content: str, line_start: int, char_start: int, char_end: int, line_end: int = None):
        """
        Initialize a new ContentGroup instance.
        
        Args:
            content: The text content of the group
            line: The line number where this content appears
            start_char: The starting character position within the line
            end_char: The ending character position within the line
        """
        self.content = content
        self.line_start = line_start
        self.char_start = char_start
        self.char_end = char_end
        self.line_end = line_end or line_start
    
    def __str__(self) -> str:
        """Return a string representation of the ContentGroup."""
        return f"ContentGroup(content='{self.content}', lines=({self.line_start}, {self.line_end}), pos=({self.char_start}, {self.char_end}))"
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the ContentGroup."""
        return self.__str__()
    

def boundary_distance(group1: ContentGroup, group2: ContentGroup) -> float:
    """
    Calculate the distance between two ContentGroups based on their boundaries.
    Words that share a boundary (adjacent horizontally or vertically) have distance 1.
    Words that are separated by one word have distance 2, and so on.
    
    Args:
        group1: First ContentGroup
        group2: Second ContentGroup
        
    Returns:
        float: The boundary distance between the groups
    """
    # If groups overlap, distance is 0
    if (group1.line_start <= group2.line_end and group1.line_end >= group2.line_start and
        group1.char_start <= group2.char_end and group1.char_end >= group2.char_start):
        return 0.0
        
    # Calculate vertical distance
    if group1.line_end < group2.line_start:
        # group1 is above group2
        vertical_dist = group2.line_start - group1.line_end
    elif group2.line_end < group1.line_start:
        # group2 is above group1
        vertical_dist = group1.line_start - group2.line_end
    else:
        # Groups overlap vertically
        vertical_dist = 0
        
    # Calculate horizontal distance
    if group1.char_end < group2.char_start:
        # group1 is to the left of group2
        horizontal_dist = group2.char_start - group1.char_end
    elif group2.char_end < group1.char_start:
        # group2 is to the left of group1
        horizontal_dist = group1.char_start - group2.char_end
    else:
        # Groups overlap horizontally
        horizontal_dist = 0
        
    # If either distance is 0, we only need to count the other
    if vertical_dist == 0:
        return float(horizontal_dist)
    if horizontal_dist == 0:
        return float(vertical_dist)
        
    # If both distances are non-zero, we need to count both
    # This means we need to go around a corner
    return float(vertical_dist + horizontal_dist)

def find_pattern_match(text: str, patterns: List[str], start_line: int = 1, start_char: int = 0) -> Tuple[Optional[ContentGroup], int]:
    """
    Find the best matching pattern in the text starting from a given position.
    
    Args:
        text: The text to search in
        patterns: List of regex patterns to try matching
        start_line: Line number to start searching from (1-based)
        start_char: Character position to start searching from
        
    Returns:
        Tuple of (ContentGroup if match found, index of last matched pattern)
    """
    # Expand tabs in text
    expanded_text = text.expandtabs(tabsize=8)
    lines = expanded_text.split('\n')
    
    # Adjust text to start from specified position
    start_text = '\n'.join(lines[start_line-1:])
    if start_line == 1:
        start_text = start_text[start_char:]
    
    # Start with all patterns and remove until we find a match
    current_pattern_idx = len(patterns)
    while current_pattern_idx > 0:
        current_pattern = r'\s+'.join(patterns[:current_pattern_idx])
        matches = list(re.finditer(current_pattern, start_text, re.I))
        
        if matches:
            # Get the first match
            first_match = matches[0]
            match_start = first_match.start()
            match_end = first_match.end()
            
            # Calculate line and character positions
            if start_line == 1:
                match_start += start_char
                match_end += start_char
            
            # Count newlines before the match to determine line number
            line_start = start_line + start_text[:match_start].count('\n')
            line_end = line_start
            
            # Get the specific line containing the match
            target_line = lines[line_start - 1]  # -1 because line_start is 1-based
            
            # Calculate character positions within the line
            if line_start == start_line:
                char_start = match_start - start_char
            else:
                char_start = match_start - start_text[:match_start].rfind('\n') - 1
            
            char_end = char_start + (match_end - match_start)
            
            # Create ContentGroup for the match
            label = ContentGroup(
                target_line[char_start:char_end],
                line_start,
                char_start,
                char_end,
                line_end
            )
            
            return label, current_pattern_idx - 1
            
        current_pattern_idx -= 1
    
    return None, 0

def find_pattern_positions(text: str, pattern: str, flags: int = 0) -> List[Dict[str, Union[str, int]]]:
    """
    Find all occurrences of a pattern in text and return their positions.
    
    Args:
        text: The text to search in
        pattern: The regex pattern to search for
        flags: Optional regex flags
        
    Returns:
        List of dictionaries containing the match and its position information
    """
    lines = text.split('\n')
    positions = []
    
    for i, line in enumerate(lines):
        for match in re.finditer(pattern, line, flags):
            # char_pos is now just the position within the current line
            char_pos = match.start()
            positions.append({
                'value': match.group(),
                'line': i,
                'char_pos': char_pos
            })
    
    return positions

def find_label(text: str, label_word_patterns: List[str], label_start: str = '(', label_end: str = ')') -> Optional[ContentGroup]:
    """
    Find a label in the text by matching patterns sequentially.
    
    Args:
        text: The text to search in
        label_word_patterns: List of regex patterns for each word in the label
        label_start: Optional string that must appear at the start of the label
        label_end: Optional string that must appear at the end of the label
        
    Returns:
        ContentGroup containing the matched label if found, None otherwise
    """
    # Create patterns for each word, with special handling for first and last
    patterns = []
    for i, word_pattern in enumerate(label_word_patterns):
        if i == 0:
            # First word pattern includes label_start if provided
            pattern = (f'(?:{re.escape(label_start)})?' if label_start else '') + r'\s*' + word_pattern
            patterns.append(pattern)
        elif i == len(label_word_patterns) - 1:
            # Last word pattern includes label_end if provided
            pattern = word_pattern + r'\s*' + (re.escape(label_end) + r'?' if label_end else '')
            patterns.append(pattern)
        else:
            pattern = word_pattern
            patterns.append(pattern)
    
    # Start with first pattern match
    first_label, first_idx = find_pattern_match(text, patterns)
    if not first_label:
        return None
        
    # If we matched all patterns, return the result
    if first_idx == len(patterns) - 1:
        return first_label
        
    # Continue matching remaining patterns
    remaining_patterns = patterns[first_idx + 1:]
    current_label = first_label
    current_line = current_label.line_start
    current_char = current_label.char_end
    
    while remaining_patterns:
        next_label, next_idx = find_pattern_match(text, remaining_patterns, current_line, current_char)
        if not next_label:
            break
            
        # Update the current label with the new match
        current_label.content += " " + next_label.content
        current_label.char_start = min(current_label.char_start, next_label.char_start)
        current_label.char_end = max(current_label.char_end, next_label.char_end)
        current_label.line_end = next_label.line_end
        
        # Update position for next search
        current_line = next_label.line_end
        current_char = next_label.char_end
        
        # Update remaining patterns
        remaining_patterns = remaining_patterns[next_idx + 1:]
        
        # If we matched all remaining patterns, we're done
        if not remaining_patterns:
            return current_label
    
    return current_label

def find_value_by_label(text: str, label_word_patterns: List[str], value_pattern: str, 
                       label_start: str = '(', label_end: str = ')',
                       line_search_limit: Optional[Union[List[int], Tuple[int, int]]] = None,
                       ) -> Optional[str]:
    """
    Find a value based on its proximity to a label in the text.
    Handles labels that may be split across multiple lines.
    
    Args:
        text: The text to search in
        label_word_patterns: List of regex patterns for each word in the label, in order
        value_pattern: Regex pattern to match the value
        label_start: Optional string that must appear at the start of the label (e.g. '(')
        label_end: Optional string that must appear at the end of the label (e.g. ')')
        line_search_limit: Optional tuple or list (lines_above, lines_below) specifying the max number
                          of lines to search above and below the label. If None, searches the entire text.
    Returns:
        The value that is closest to a matching label, or None if no match found
    """
    lines = text.expandtabs(tabsize=8).split('\n')

    label = find_label(text, label_word_patterns)
    if not label:
        return None

    # Create a limited search window around the label
    if line_search_limit is not None:
        if not isinstance(line_search_limit, (list, tuple)) or len(line_search_limit) != 2:
            raise ValueError("line_search_limit must be a tuple or list of two integers: (lines_above, lines_below)")
        lines_above, lines_below = line_search_limit
        start_line = max(0, label.line_start - lines_above)
        end_line = min(len(lines), label.line_end + lines_below)
        search_lines = lines[start_line:end_line]
    else:
        start_line = 0
        end_line = len(lines)
        search_lines = lines
    
    # Find all values within the search window
    value_positions = []
    for i, line in enumerate(search_lines):
        for match in re.finditer(value_pattern, line, re.I):
            value = match.group().strip()
            # Skip if the value matches the label text
            if value in label.content:
                continue
            value_pos = ContentGroup(value, start_line + i, match.start(), match.end())
            value_positions.append(value_pos)
    
    if not value_positions:
        return None
    
    # Calculate distances from each value to the label
    best_distance = float('inf')
    best_value = None
    
    #Need to update distance to just be line distance since things have been converted to a single column. May be a problem with date since it's horizontal
    for value_pos in value_positions:
        # distance = abs(current_line_idx - value_pos['line'])
        # distance = exponential_vertical_distance(
        #     value_pos['line'], value_pos['char_pos'],
        #     current_line_idx, label_center_pos
        # )

        distance = boundary_distance(label, value_pos)
        
        if distance < best_distance:
            best_distance = distance
            best_value = value_pos.content
    
    return best_value.strip() if best_value else None


def parse_content(text: str, tabsize: int = 8) -> List[ContentGroup]:
    """
    Parse the given text into a list of ContentGroup objects.
    
    This function processes the input text to identify and extract contiguous
    groups of text separated by whitespace. Each group is represented as a
    ContentGroup object, which contains the text content, line number, and
    character positions within that line.
    """

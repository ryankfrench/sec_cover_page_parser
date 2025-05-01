"""
Column Parser - A utility for parsing text with columnar layout.

This module provides functionality to parse text files that have content arranged in
visual columns, even when those columns are created using a mix of spaces and tabs.
It handles ASCII text with complex formatting by analyzing the visual (normalized)
layout and determining column boundaries based on the gaps between content across 
multiple lines.

The parser operates in two passes per text section (chunk):
1. First pass establishes column boundaries based on consistent gaps between content.
2. Second pass extracts content from each line using those boundaries.

This approach is particularly useful for parsing:
- SEC filings with tables 
- Log files with columnar data
- ASCII reports and text tables
- Any text with visual alignment but inconsistent delimiters
"""

import re
from typing import List, Dict, Tuple, Optional

def get_norm_to_orig_map(line: str, tabsize: int = 4) -> Dict[int, int]:
    """
    Creates a mapping from indices in the tab-expanded line to the original line indices.
    
    This is necessary because when tabs are expanded to spaces, the character positions
    in the normalized (expanded) line no longer directly correspond to the original line.
    This function builds a dictionary that translates between the two coordinate systems.
    
    Args:
        line: The original line containing tabs and other characters
        tabsize: The number of spaces each tab character should be expanded to
                (or more accurately, how many spaces to insert until the next tab stop)
    
    Returns:
        A dictionary where keys are indices in the normalized line and values are 
        the corresponding indices in the original line.
        
    Example:
        If line = "a\\tb" and tabsize = 4, the expanded form would be "a   b"
        The mapping would be {0:0, 1:1, 2:1, 3:1, 4:2}
        This indicates that position 0 in normalized maps to 0 in original,
        positions 1-3 in normalized all map back to position 1 (the tab) in the original,
        and position 4 in normalized maps to position 2 in the original.
    """
    mapping = {}
    orig_idx = 0
    norm_idx = 0
    for char in line:
        if char == '\t':
            spaces_to_add = tabsize - (norm_idx % tabsize)
            for i in range(spaces_to_add):
                mapping[norm_idx + i] = orig_idx # Map all expanded spaces to the tab's original index
            norm_idx += spaces_to_add
            orig_idx += 1
        else:
            mapping[norm_idx] = orig_idx # Map the character's index
            norm_idx += 1
            orig_idx += 1
    mapping[norm_idx] = orig_idx # Map the index after the last character
    return mapping

def get_norm_pos(line: str, orig_index: int, tabsize: int = 4) -> int:
    """
    Calculates the normalized horizontal position (ASCII column) for an original index.
    
    For a given position in the original line, this function determines what column
    that position would appear at visually, accounting for tab expansion.
    
    Args:
        line: The original line containing tabs and other characters
        orig_index: The index in the original line to convert
        tabsize: The number of spaces each tab character should be expanded to
                (or more accurately, how many spaces to insert until the next tab stop)
    
    Returns:
        The corresponding column position in the visually normalized line
        
    Raises:
        IndexError: If the orig_index is outside the bounds of the line length
        
    Example:
        If line = "a\\tb" and tabsize = 4, for orig_index = 1 (the tab position),
        the function would return 1 (the visual column where the tab starts).
    """
    norm_pos = 0
    for i, char in enumerate(line):
        if i == orig_index:
            return norm_pos
        if char == '\t':
            spaces_to_add = tabsize - (norm_pos % tabsize)
            norm_pos += spaces_to_add
        else:
            norm_pos += 1
    # If orig_index is len(line), it refers to the position *after* the last character
    if orig_index == len(line):
        return norm_pos
    # Should be unreachable if orig_index is valid
    raise IndexError(f"Original index {orig_index} out of bounds for line length {len(line)}")

def map_norm_slice_to_orig(norm_start: int, norm_end: int, norm_to_orig_map: Dict[int, int], max_norm_idx: int, max_orig_idx: int) -> Optional[Tuple[int, int]]:
    """
    Maps a normalized slice [norm_start, norm_end) back to original line indices.
    
    Given a range of positions in the normalized (tab-expanded) line, this function
    determines the corresponding start and end positions in the original line.
    This is needed when we've calculated column boundaries in the normalized space
    and need to extract the actual text from the original line.
    
    Args:
        norm_start: The starting index in the normalized line
        norm_end: The ending index (exclusive) in the normalized line
        norm_to_orig_map: The mapping dictionary from get_norm_to_orig_map()
        max_norm_idx: The maximum valid index in the normalized line
        max_orig_idx: The maximum valid index in the original line
    
    Returns:
        A tuple (orig_start, orig_end) representing indices in the original line,
        or None if the mapping results in an invalid range.
        
    Example:
        If normalized slice [4, 8) needs to be mapped back to the original line,
        this function might return (2, 4) indicating the corresponding positions.
    """
    orig_start = None
    found_start = False
    # Find first original index mapped from a norm index >= norm_start
    for i in range(norm_start, max_norm_idx + 1):
        temp_orig = norm_to_orig_map.get(i)
        if temp_orig is not None:
            # Ensure we don't map to an earlier original index if multiple norm indices map to the same tab
            if not found_start or temp_orig > orig_start:
                 orig_start = temp_orig
                 found_start = True
            # If the found original index corresponds to a norm index *past* our target start,
            # and we already found *an* start, we use the one we found.
            if i >= norm_start and found_start:
                break
    # If no mapping found at or after norm_start, it means norm_start is beyond content
    if not found_start:
         orig_start = max_orig_idx

    orig_end = None
    found_end = False
    # Find first original index mapped from a norm index >= norm_end
    for i in range(norm_end, max_norm_idx + 1):
        temp_orig = norm_to_orig_map.get(i)
        if temp_orig is not None:
            if not found_end or temp_orig > orig_end:
                 orig_end = temp_orig
                 found_end = True
            if i >= norm_end and found_end:
                break
    # If no mapping found at or after norm_end, use the end of the original line
    if not found_end:
        orig_end = max_orig_idx

    # Clip to ensure validity, although mapping should respect bounds if correct
    orig_start_clipped = max(0, min(max_orig_idx, orig_start))
    orig_end_clipped = max(0, min(max_orig_idx, orig_end))

    # Return only if it represents a valid span (start < end)
    if orig_start_clipped < orig_end_clipped:
        return (orig_start_clipped, orig_end_clipped)
    else:
        return None

def parse_columns(text: str, tabsize: int = 8) -> List[Dict[str, str]]:
    """
    Parse text with columns using a sequential line processing approach.
    
    This function analyzes text to identify columnar structure and extract content
    from each column. It works by:
    
    1. Processing each line sequentially to identify and update boundary estimates.
    2. When a line doesn't fit current boundary estimates, the estimates are reset.
    3. Content is extracted for each line based on the current boundary estimates.
    
    The column detection is based on the visual appearance of the text after tab 
    expansion, similar to how a human would perceive columns when viewing the text.
    The parser groups text separated by multiple spaces into distinct columns.
    
    Args:
        text: The input text that may contain multiple columns
        tabsize: The tab width used for normalization and position calculation
                (default is 8, which is the standard for many systems)
    
    Returns:
        A list of dictionaries, each representing a parsed line. Each dictionary
        contains keys 'col1', 'col2', etc., with the content of each column.
        Empty columns may be omitted.
    """
    lines = text.split('\n')
    all_results = []
    
    # Current state variables
    boundary_estimates: Dict[int, Tuple[int, int]] = {}
    cut_points = []
    max_cols_seen = 0
    
    # Process each line sequentially
    for line_num, line in enumerate(lines):
        # Skip blank lines (but don't reset boundaries)
        if not line.strip():
            continue
        
        # Prepare line metadata for processing
        normalized_line = line.expandtabs(tabsize)
        norm_to_orig_map = get_norm_to_orig_map(line, tabsize)
        max_orig_idx = len(line)
        max_norm_idx = len(normalized_line)
        
        # Find content groups in this line
        matches = list(re.finditer(r'[^\s]+([\s][^\s]+)*', line))
        if not matches:
            continue
            
        # Get normalized extents of each content group
        norm_extents = []
        for m in matches:
            try:
                start_pos = get_norm_pos(line, m.start(), tabsize)
                end_pos = get_norm_pos(line, m.end(), tabsize)
                norm_extents.append((start_pos, end_pos))
            except IndexError as e:
                print(f"Warning: Error getting norm pos for match {m.span()} on line {line_num}: {e}")
                continue
        
        if len(norm_extents) != len(matches):
            continue

        # Check if current line's content violates existing boundaries
        reset_boundaries = False
        
        # We'll no longer reset just because the number of content groups doesn't match
        # Instead, we'll check if each content group fits within the defined column structure
        
        # Only check for violations if we have established cut points
        if cut_points:
            for i, (start, end) in enumerate(norm_extents):
                # Check if this content group spans across a column boundary
                spans_boundary = False
                for cut_point in cut_points:
                    if start < cut_point < end:
                        # Content spans across a boundary - this is a violation
                        spans_boundary = True
                        break
                
                if spans_boundary:
                    reset_boundaries = True
                    break
                
                # Check if content fits within any defined column
                fits_in_column = False
                
                # First column: from start of line to first cut point
                if start >= 0 and (len(cut_points) == 0 or end <= cut_points[0]):
                    fits_in_column = True
                
                # Middle columns: between adjacent cut points
                for j in range(len(cut_points) - 1):
                    if start >= cut_points[j] and end <= cut_points[j+1]:
                        fits_in_column = True
                        break
                
                # Last column: after last cut point to end of line
                if len(cut_points) > 0 and start >= cut_points[-1]:
                    fits_in_column = True
                
                # If content doesn't fit in any column, we need to reset
                if not fits_in_column:
                    reset_boundaries = True
                    break
        
        # Reset if needed
        if reset_boundaries:
            boundary_estimates = {}
            cut_points = []
            max_cols_seen = len(norm_extents)  # Set based on current line
        
        # Update boundary estimates based on current line's content
        num_cols = len(norm_extents)
        max_cols_seen = max(max_cols_seen, num_cols)
        
        # Update boundary estimates based on gaps between content groups
        for i in range(num_cols - 1):
            gap_norm_start = norm_extents[i][1]      # End of content in column i
            gap_norm_end = norm_extents[i+1][0]      # Start of content in column i+1
            
            # Skip if there's no gap or the content blocks overlap
            if gap_norm_start >= gap_norm_end:
                continue
                
            # Get current estimate for this gap or use default (widest possible)
            current_min_start, current_max_end = boundary_estimates.get(i, (0, float('inf')))
            
            # Refine the boundary estimate by narrowing the range
            new_min_start = max(current_min_start, gap_norm_start)
            new_max_end = min(current_max_end, gap_norm_end)
            
            # Only update if the new estimate is valid (start < end)
            if new_min_start < new_max_end:
                boundary_estimates[i] = (new_min_start, new_max_end)
        
        # Recalculate cut points based on updated boundary estimates
        # (only if they've changed or been reset)
        if not cut_points or reset_boundaries:
            cut_points = []
            if max_cols_seen > 1:
                for i in range(max_cols_seen - 1):
                    estimate = boundary_estimates.get(i)
                    if estimate:
                        min_start, max_end = estimate
                        if min_start < max_end:
                            # Choose midpoint of the valid gap as the column boundary
                            cut = min_start + (max_end - min_start) // 2
                            # Ensure cut points increase monotonically
                            if not cut_points or cut > cut_points[-1]:
                                cut_points.append(cut)
                            else:
                                # If cut points don't increase, stop adding boundaries
                                print(f"Warning: Calculated cut point {cut} for gap {i} not > previous {cut_points[-1]} on line {line_num}. Stopping boundary definition.")
                                break
                        else:
                            # Gap estimate collapsed (contradictory evidence across lines)
                            print(f"Warning: Boundary estimate for gap {i} collapsed ({min_start}, {max_end}) on line {line_num}. Cannot place boundary.")
                            break
                    else:
                        # No estimate for this gap index
                        break
        
        # Extract content based on current cut points
        columns = {}
        
        # If we have cut points, try to fit each content group into the appropriate column
        if cut_points:
            # First determine which column each content group belongs to
            for i, (start, end) in enumerate(norm_extents):
                content_match = matches[i]
                content = content_match.group().strip()
                
                if not content:
                    continue
                
                # Figure out which column this content belongs to
                column_idx = 0  # Default to first column
                
                # Check each column boundary
                for j, cut_point in enumerate(cut_points):
                    # If content starts after this cut point, it belongs to the next column
                    if start >= cut_point:
                        column_idx = j + 1
                    else:
                        break
                
                # Add content to the appropriate column (1-indexed)
                column_key = f'col{column_idx + 1}'
                columns[column_key] = content
        else:
            # No cut points yet (first line or after reset)
            # Just assign each content group to sequential columns
            for i, match in enumerate(matches):
                content = match.group().strip()
                if content:
                    columns[f'col{i+1}'] = content
        
        # Add parsed line if it has content
        if columns:
            all_results.append(columns)
    
    return all_results

def basic_example():
    """
    A basic example demonstrating the column parser with a mixed-format text.
    
    This example shows a document with:
    1. A title line (single column)
    2. A blank line (used as chunk separator)
    3. A block of text with 3 columns aligned with tabs and spaces
    4. Followed by regular text in a single column
    
    The function prints the parsed result for each line.
    """
    # Example with mixed spaces and tabs
    example_text = """                   My document title

      This is a\t\t   This is a\t\t This is also
   sentence in\t\t sentence in\t\t  a sentence in
       column 1\t\t column2\t\t   column 3
     (column 1\t\t (column 2\t\t(column 3
        title)\t\t  title)\t\t  title)
Now the doucment goes back to a regular document
where writing is in a single column or paragraph like usual"""

    parsed_columns = parse_columns(example_text)
    for line_data in parsed_columns:
        print(line_data)

def cover_page_example():
    """
    An example parsing an SEC filing cover page with tabular data.
    
    This example reads a real SEC filing text and extracts columnar data
    from the cover page section. The function reads the file, extracts a 
    specific range of lines, and prints the parsed column structure.
    """
    path = '/home/rfrench/projects/sec_cover_page_parser/test_filings/1018724/0000891020-98-001352/0000891020-98-001352.txt'
    with open(path, 'r') as f:
        text = f.read()

    # Extract just a portion of the file for demonstration
    lines = text.split('\n')
    text = '\n'.join(lines[:104])
    parsed_columns = parse_columns(text)
    for line_data in parsed_columns:
        print(line_data) 

# Example usage
if __name__ == "__main__":
    basic_example()
    # cover_page_example()
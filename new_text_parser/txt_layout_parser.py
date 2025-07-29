
import re
from enum import Enum, auto
from typing import List, Dict, Tuple
import column_parser
from .document_section import DocumentSection
from nlp_text_search import nlp_text_search
from nlp_text_search.nlp_text_search import NLPTextSearch
import time


class DocumentSectionType(Enum):
    TITLE = auto()
    SUBTITLE = auto()
    LABELLED_CONTENT = auto()
    PARAGRAPH = auto()
    TABLE = auto()
    SECTION_HEADER = auto()
    FOOTER = auto()
    HEADER = auto()
    LIST = auto()

class TextLayoutParser:
    def __init__(self):
        pass

    def parse_document(self, content: str) -> List[DocumentSection]:
        vertical_sections = self.parse_vertical_boundaries(content)
        sections = [subsections for section in vertical_sections for subsections in self.parse_horizontal_boundaries(section)]
        return sections
    
    def assign_columns(self, boundary_estimates: List[Tuple[int, int]], horizontal_boundaries: List[Tuple[int, int]]) -> List[int]:
        """
        Assign each content group to the most appropriate column based on boundary estimates.
        
        This function takes the current boundary estimates (which define column ranges)
        and horizontal boundaries (content group positions) and determines which column
        each content group belongs to.
        
        Args:
            boundary_estimates: List of (start, end) tuples defining column boundaries
            horizontal_boundaries: List of (start, end) tuples for content group positions
            
        Returns:
            List of column indices (0-indexed) for each content group
        """
        if not boundary_estimates:
            # No existing columns, assign sequential columns
            return list(range(len(horizontal_boundaries)))
        
        column_assignments = []
        
        for start, end in horizontal_boundaries:
            best_column = 0  # Default to first column
            
            # Check each column boundary to find the best fit
            for col_idx, (col_start, col_end) in enumerate(boundary_estimates):
                min_start = 0 if col_idx == 0 else boundary_estimates[col_idx - 1][1]
                max_end = float('inf') if col_idx == len(boundary_estimates) - 1 else boundary_estimates[col_idx + 1][0]
                
                if start >= min_start and end <= max_end:
                    best_column = col_idx
                    break
            
            column_assignments.append(best_column)
        
        return column_assignments
    
    def update_vertical_subsection(self, vertical_subsection: List[DocumentSection], column_index: int, 
                                 content: str, line_num: int, char_start: int, char_end: int) -> DocumentSection:
        """
        Update or create a DocumentSection within a vertical subsection.
        
        This method either updates an existing DocumentSection at the specified column index
        or creates a new one if it doesn't exist. It handles appending content and updating
        metadata like character boundaries and line numbers.
        
        Args:
            vertical_subsection: List of DocumentSection objects representing columns
            column_index: Index of the column to update
            content: Content to add to the section
            line_num: Current line number
            char_start: Starting character position
            char_end: Ending character position
            
        Returns:
            Updated DocumentSection object
        """
        # Ensure the vertical_subsection list is large enough
        while len(vertical_subsection) <= column_index:
            vertical_subsection.append(None)
        
        if vertical_subsection[column_index] is None:
            # Create a new DocumentSection
            new_section = DocumentSection(
                content=content,
                line_start=line_num,
                char_start=char_start,
                char_end=char_end,
                line_end=line_num
            )
            vertical_subsection[column_index] = new_section
        else:
            # Update existing DocumentSection
            existing_section = vertical_subsection[column_index]
            existing_section.content += content
            existing_section.char_start = min(existing_section.char_start, char_start)
            existing_section.char_end = max(existing_section.char_end, char_end)
            existing_section.line_end = line_num
        
        return vertical_subsection[column_index]
    
    def parse_horizontal_boundaries(self, section: DocumentSection, tabsize: int = 8) -> List[DocumentSection]:
        """
        Splits a given DocumentSection into sub-sections based on horizontal (column) boundaries. It does this by processing
        each line from top to bottom. The horizontal boundaries for each group of words separated
        by 3 or more white spaces. It then attempts to fit each word grouping into an existing column. If there is
        a violation, a new vertical section is started and the boundary estimates are reset.

        Potential extension: Instead of resetting due to violation, we could try to create a new column if possible. 
        Then, in the case of a violation, we go back and look at all previous column entries and determine if the 
        most recent line is the violating line or if a previous line was incorrectly included. 

        Args:
            section (DocumentSection): The document section to be split into columns.
            tabsize (int, optional): The number of spaces to expand tabs to. Defaults to 8.

        Returns:
            List[DocumentSection]: A list of DocumentSection objects, each representing a horizontal subsection (column) of the original section.

        This method analyzes the content of the given section line by line, estimates column boundaries based on whitespace and content alignment,
        and segments the section into multiple DocumentSections corresponding to these columns. It is useful for parsing multi-column text layouts,
        such as tables or documents with side-by-side content.
        """
        lines = section.content.split('\n')
        all_results = []
        
        # Current state variables
        boundary_estimates: List[Tuple[int, int]] = []              # note this could be reset if a new vert subsection is created.
        vertical_subsections: List[List[DocumentSection]] = []
        
        for line_num, line in enumerate(lines):
            # Find content groups in this line
            # matches = list(re.finditer(r'[^\s]+(?:\s{1,2}[^\s]+)*', line.expandtabs(tabsize)))
            # this new regex will split on two spaces as long as it doesnt happen in the middle of a sentence.
            matches = list(re.finditer(r'[^\s]+(?:(?:\s{1}|(?<=\w[.!?])\s{2}(?=[A-Z]))[^\s]+)*', line.expandtabs(tabsize)))

            # Get the character position boundaries for each content group (column)
            horizontal_boundaries = [m.span() for m in matches]

            if len(horizontal_boundaries) > len(boundary_estimates):
                # We need to reset the boundary estimates if the number of columns has increased.
                # it's not possible to increase the number from 1 to any because all will fit in 1.
                # decreasing could be ok.
                boundary_estimates = horizontal_boundaries
                vertical_subsections.append([])
                prefix = ""

            column_assignments = self.assign_columns(boundary_estimates, horizontal_boundaries)

            prefix = "\n"
            if len(set(column_assignments)) != len(horizontal_boundaries):
                # violation, create a new vertical subsection because multiple data has been assigned to the same column.
                boundary_estimates = horizontal_boundaries
                vertical_subsections.append([])
                prefix = ""

            for i, (start, end) in enumerate(horizontal_boundaries):
                column_index = column_assignments[i]
                vertical_subsections[-1][column_index] = self.update_vertical_subsection(vertical_subsections[-1], column_index, f"{prefix}{matches[i].group().strip()}", line_num + section.line_start, start, end)
            
        return vertical_subsections

    def parse_vertical_boundaries(self, content: str) -> List[DocumentSection]:
        sections = []
        lines = content.split('\n')
        section = None
        section_start = None
        section_end = None
        for i in range(len(lines)):
            if lines[i].strip() != '':
                if section_start is None:
                    section_start = i
                    section_end = i
                else:
                    section_end = i
            else:
                if section_start is not None:
                    section = DocumentSection(
                        content='\n'.join(lines[section_start:(section_end + 1)]),
                        line_start=section_start + 1,
                        char_start=0,
                        char_end=max([len(lines[j]) for j in range(section_start, section_end + 1)]),
                        line_end=section_end + 1
                    )
                    sections.append(section)
                    section_start = None
                    section_end = None
        
        # If there is an unfinished section when the end of file is reached, close it.
        if section_start is not None:
            section_end = i
            section = DocumentSection(
                content='\n'.join(lines[section_start:(section_end + 1)]),
                line_start=section_start + 1,
                char_start=0,
                char_end=max([len(lines[j]) for j in range(section_start, section_end + 1)]),
                line_end=section_end + 1
            )
            sections.append(section)
        
        return sections

    def extract_titles(self, content: str) -> List[str]:
        pass

    def assess_section_type(self, content: str) -> DocumentSectionType:
        pass

    def search_terms_original(self, parsed_document: List[List[DocumentSection]], search_terms: Dict[str, str]) -> Dict[str, str]:
        """
        Original approach: Process each section individually
        """
        results = {}
        for key, term in search_terms.items():
            max_score = 0
            best_match = None
            for vert_section in parsed_document:
                for section in vert_section:
                    result = nlp_text_search.find_best_match(term, section.content)
                    if result is not None:
                        score = result[3]
                        if score > max_score:
                            max_score = score
                            best_match = result[0]
            results[key] = best_match
        return results

    def search_terms_optimized(self, parsed_document: List[List[DocumentSection]], search_terms: Dict[str, str]) -> Dict[str, str]:
        """
        Optimized approach: Use NLPTextSearch batch processing with generic mapper
        """
        searcher = NLPTextSearch()
        
        # Use the generalized batch search method with a content mapper
        results = searcher.batch_search_nested_objects(
            nested_objects=parsed_document,
            search_terms=search_terms,
            content_mapper=lambda section: section.content if section else "",
            threshold=0.7,
            batch_size=50
        )
        
        return results

    def compare_search_performance(self, parsed_document: List[List[DocumentSection]], search_terms: Dict[str, str], runs: int = 3) -> Dict[str, float]:
        """
        Compare performance between original and optimized search methods
        """
        print("Comparing search performance...")
        
        # Warm up (exclude from timing)
        self.search_terms_original(parsed_document, {"test": "test"})
        self.search_terms_optimized(parsed_document, {"test": "test"})
        
        # Time original method
        original_times = []
        for i in range(runs):
            start_time = time.time()
            results_original = self.search_terms_original(parsed_document, search_terms)
            end_time = time.time()
            original_times.append(end_time - start_time)
            print(f"Original method run {i+1}: {end_time - start_time:.4f}s")
        
        # Time optimized method  
        optimized_times = []
        for i in range(runs):
            start_time = time.time()
            results_optimized = self.search_terms_optimized(parsed_document, search_terms)
            end_time = time.time()
            optimized_times.append(end_time - start_time)
            print(f"Optimized method run {i+1}: {end_time - start_time:.4f}s")
        
        # Calculate averages
        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        speedup = avg_original / avg_optimized if avg_optimized > 0 else 0
        
        print(f"\nPerformance Results:")
        print(f"Original method average: {avg_original:.4f}s")
        print(f"Optimized method average: {avg_optimized:.4f}s")
        print(f"Speedup: {speedup:.2f}x")
        
        # Verify results are the same
        results_match = results_original == results_optimized
        print(f"Results match: {results_match}")
        if not results_match:
            print("Warning: Results differ between methods!")
            print("Original:", results_original)
            print("Optimized:", results_optimized)
        
        return {
            'original_avg': avg_original,
            'optimized_avg': avg_optimized,
            'speedup': speedup,
            'results_match': results_match
        }

def main(text: str):
    # remove header
    if '<SEC-HEADER>' in text:
            header_start = text.find('<SEC-HEADER>')
            header_end = text.find('</SEC-HEADER>')
            if header_end != -1:
                text = text[:header_start] + text[header_end + len('</SEC-HEADER>'):]
    # Extract just a portion of the file for demonstration
    lines = text.split('\n')
    text = '\n'.join(lines[:104])
    #parsed_columns = column_parser.parse_columns(text)
    txt_layout_parser = TextLayoutParser()
    parsed_document = txt_layout_parser.parse_document(text)

    search_terms = {
        "name": "(Exact Name of Registrant as Specified in Charter)",
        "date": "Date of Report",
        "irs_no":"(IRS Employer Identification No.)",
        "address": "(Address of Executive Offices including zip code)",
        "zip": "(Zip Code)",
        "state_of_incorporation": "(State or Other Jurisdiction of Incorporation)",
        "commission_file_number": "(Commission File Number)",
    }

    # Run performance comparison
    performance_results = txt_layout_parser.compare_search_performance(parsed_document, search_terms)
    
    # Use the optimized method for final results
    results = txt_layout_parser.search_terms_optimized(parsed_document, search_terms)
    
    print("\nFinal Results:")
    for key, value in results.items():
        print(f"{key}: {value}")

    

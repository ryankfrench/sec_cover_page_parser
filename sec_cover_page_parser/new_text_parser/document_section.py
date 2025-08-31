

class DocumentSection:
    """
    A class representing a section of a text document with related content.
    
    This class stores information about a contiguous group of text, including
    its content, line number, and character positions within that line.
    
    Attributes:
        content (str): The actual text content of the section
        line (int): The line number where this content appears
        char_start (int): The starting character position within the line
        char_end (int): The ending character position within the line
    """
    
    def __init__(self, content: str, line_start: int, char_start: int, char_end: int, line_end: int = None):
        """
        Initialize a new DocumentSection instance.
        
        Args:
            content: The text content of the document section
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
        """Return a string representation of the DocumentSection."""
        return f"DocumnetSection(content='{self.content}', lines=({self.line_start}, {self.line_end}), pos=({self.char_start}, {self.char_end}))"
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the DocumentSection."""
        return self.__str__()
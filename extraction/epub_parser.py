"""EPUB Parser for extracting content from EPUB files.

This module handles:
- Reading and parsing EPUB files (ZIP-based format)
- Extracting text content from chapters
- Parsing glossaries and definitions
- Handling metadata and structure
"""

import zipfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from lxml import etree
import re
from dataclasses import dataclass
from loguru import logger


@dataclass
class ContentItem:
    """Represents a piece of extracted content."""
    title: str
    text: str
    content_type: str  # 'chapter', 'glossary', 'definition', 'section'
    metadata: Dict = None


@dataclass
class EPUBMetadata:
    """Metadata extracted from EPUB."""
    title: str
    author: str
    language: str
    date: str
    description: str


class EPUBParser:
    """Main parser for EPUB files."""

    def __init__(self, epub_path: str):
        """Initialize the EPUB parser.
        
        Args:
            epub_path: Path to the EPUB file
        """
        self.epub_path = Path(epub_path)
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")
        
        self.zip_file = None
        self.metadata = None
        self.content_items = []
        self.namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
        }

    def parse(self) -> Tuple[EPUBMetadata, List[ContentItem]]:
        """Parse the EPUB file and extract all content.
        
        Returns:
            Tuple of (metadata, content_items)
        """
        try:
            with zipfile.ZipFile(self.epub_path, 'r') as zf:
                self.zip_file = zf
                
                # Extract metadata
                self.metadata = self._extract_metadata()
                logger.info(f"Extracted metadata: {self.metadata.title} by {self.metadata.author}")
                
                # Extract content
                self.content_items = self._extract_content()
                logger.info(f"Extracted {len(self.content_items)} content items")
                
                return self.metadata, self.content_items
        except Exception as e:
            logger.error(f"Error parsing EPUB: {e}")
            raise

    def _extract_metadata(self) -> EPUBMetadata:
        """Extract metadata from the EPUB package."""
        try:
            # Find package.opf (usually in root or META-INF)
            package_path = self._find_package_path()
            if not package_path:
                logger.warning("Could not find package.opf")
                return EPUBMetadata(title="Unknown", author="Unknown", 
                                   language="en", date="", description="")
            
            with self.zip_file.open(package_path) as f:
                tree = etree.parse(f)
                root = tree.getroot()
                
                # Extract metadata
                title = root.findtext('{%s}title' % self.namespaces['dc'], 'Unknown')
                author = root.findtext('{%s}creator' % self.namespaces['dc'], 'Unknown')
                language = root.findtext('{%s}language' % self.namespaces['dc'], 'en')
                date = root.findtext('{%s}date' % self.namespaces['dc'], '')
                description = root.findtext('{%s}description' % self.namespaces['dc'], '')
                
                return EPUBMetadata(
                    title=title,
                    author=author,
                    language=language,
                    date=date,
                    description=description
                )
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return EPUBMetadata(title="Unknown", author="Unknown",
                               language="en", date="", description="")

    def _find_package_path(self) -> Optional[str]:
        """Find the package.opf file in the EPUB."""
        try:
            # Check container.xml first
            with self.zip_file.open('META-INF/container.xml') as f:
                tree = etree.parse(f)
                root = tree.getroot()
                
                # Find rootfile element
                for elem in root.iter('{*}rootfile'):
                    return elem.get('full-path')
        except:
            pass
        
        # Fallback: search for package.opf
        for name in self.zip_file.namelist():
            if name.endswith('package.opf') or name.endswith('content.opf'):
                return name
        
        return None

    def _extract_content(self) -> List[ContentItem]:
        """Extract all content from the EPUB."""
        content_items = []
        
        try:
            package_path = self._find_package_path()
            if not package_path:
                return content_items
            
            # Get spine (reading order)
            with self.zip_file.open(package_path) as f:
                tree = etree.parse(f)
                root = tree.getroot()
                
                spine = root.find('{%s}spine' % self.namespaces['opf'])
                if spine is None:
                    return content_items
                
                # Get manifest for ID -> href mapping
                manifest = root.find('{%s}manifest' % self.namespaces['opf'])
                id_to_href = {}
                if manifest is not None:
                    for item in manifest.findall('{%s}item' % self.namespaces['opf']):
                        item_id = item.get('id')
                        href = item.get('href')
                        if item_id and href:
                            id_to_href[item_id] = href
                
                # Extract content from spine items
                base_dir = str(Path(package_path).parent)
                for itemref in spine.findall('{%s}itemref' % self.namespaces['opf']):
                    item_id = itemref.get('idref')
                    if item_id in id_to_href:
                        href = id_to_href[item_id]
                        
                        # Skip non-HTML content
                        if not (href.endswith('.html') or href.endswith('.xhtml')):
                            continue
                        
                        # Construct full path
                        if base_dir and base_dir != '.':
                            full_path = f"{base_dir}/{href}"
                        else:
                            full_path = href
                        
                        try:
                            content = self._extract_html_content(full_path)
                            if content:
                                content_items.append(content)
                        except Exception as e:
                            logger.warning(f"Error extracting content from {full_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
        
        return content_items

    def _extract_html_content(self, file_path: str) -> Optional[ContentItem]:
        """Extract text content from an HTML/XHTML file within the EPUB."""
        try:
            with self.zip_file.open(file_path) as f:
                html_content = f.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract title
                title = "Unknown"
                if soup.h1:
                    title = soup.h1.get_text(strip=True)
                elif soup.title:
                    title = soup.title.get_text(strip=True)
                
                # Extract text
                text = soup.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                
                if text.strip():
                    return ContentItem(
                        title=title,
                        text=text,
                        content_type='chapter',
                        metadata={'source': file_path}
                    )
        except Exception as e:
            logger.warning(f"Error extracting HTML content from {file_path}: {e}")
        
        return None

    def get_glossary(self) -> List[Dict[str, str]]:
        """Extract glossary entries if they exist.
        
        Returns:
            List of glossary entries with 'term' and 'definition' keys
        """
        glossary = []
        
        for item in self.content_items:
            if 'glossary' in item.title.lower():
                # Simple glossary parsing: look for term: definition patterns
                entries = self._parse_glossary_text(item.text)
                glossary.extend(entries)
        
        return glossary

    def _parse_glossary_text(self, text: str) -> List[Dict[str, str]]:
        """Parse glossary text to extract term-definition pairs."""
        entries = []
        
        # Look for patterns like "Term: definition" or "Term - definition"
        # This is a simple heuristic and can be enhanced
        lines = text.split('.')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    term = parts[0].strip()
                    definition = parts[1].strip()
                    
                    # Filter out very short terms (likely not real glossary entries)
                    if 5 <= len(term) <= 100 and len(definition) > 10:
                        entries.append({
                            'term': term,
                            'definition': definition
                        })
        
        return entries

    def summary(self) -> Dict:
        """Return a summary of the parsed EPUB."""
        return {
            'title': self.metadata.title if self.metadata else 'Unknown',
            'author': self.metadata.author if self.metadata else 'Unknown',
            'content_items': len(self.content_items),
            'total_text_length': sum(len(item.text) for item in self.content_items),
            'chapters': [item.title for item in self.content_items]
        }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python epub_parser.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    parser = EPUBParser(epub_file)
    
    metadata, content = parser.parse()
    summary = parser.summary()
    
    print(f"\nEPUB Summary:")
    print(f"Title: {summary['title']}")
    print(f"Author: {summary['author']}")
    print(f"Content Items: {summary['content_items']}")
    print(f"Total Text Length: {summary['total_text_length']} characters")
    print(f"\nFirst 3 Chapters:")
    for chapter in summary['chapters'][:3]:
        print(f"  - {chapter}")

"""
PDF Loader Service - Handles PDF file uploads and extraction
Extracts text from PDFs using PyMuPDF
"""
import fitz  # PyMuPDF
import io
from typing import Optional


class PDFLoadError(Exception):
    """Custom exception for PDF loading errors"""
    pass


class PDFLoader:
    """Service for loading and processing PDF files"""
    
    def __init__(self):
        """Initialize PDF loader"""
        pass
    
    async def load_pdf_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """
        Load and extract text from PDF file bytes
        
        Args:
            file_bytes: PDF file content as bytes
            filename: Name of the PDF file (for error reporting)
        
        Returns:
            Extracted text content from the PDF
            
        Raises:
            PDFLoadError: If PDF is invalid or corrupted
        """
        try:
            # Open PDF from bytes
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            
            if pdf_document.page_count == 0:
                raise PDFLoadError(f"PDF '{filename}' has no pages")
            
            # Extract text from all pages
            extracted_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            pdf_document.close()
            
            if not extracted_text.strip():
                raise PDFLoadError(f"PDF '{filename}' contains no readable text")
            
            return extracted_text
            
        except fitz.FileError as e:
            raise PDFLoadError(f"Invalid or corrupted PDF file: {filename}. Error: {str(e)}")
        except Exception as e:
            raise PDFLoadError(f"Error processing PDF '{filename}': {str(e)}")
    
    async def load_pdf_from_file(self, file_path: str) -> str:
        """
        Load and extract text from PDF file path
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Extracted text content from the PDF
            
        Raises:
            PDFLoadError: If PDF is invalid or corrupted
        """
        try:
            pdf_document = fitz.open(file_path)
            
            if pdf_document.page_count == 0:
                raise PDFLoadError(f"PDF '{file_path}' has no pages")
            
            # Extract text from all pages
            extracted_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            pdf_document.close()
            
            if not extracted_text.strip():
                raise PDFLoadError(f"PDF '{file_path}' contains no readable text")
            
            return extracted_text
            
        except fitz.FileError as e:
            raise PDFLoadError(f"Invalid or corrupted PDF file: {file_path}. Error: {str(e)}")
        except Exception as e:
            raise PDFLoadError(f"Error processing PDF '{file_path}': {str(e)}")

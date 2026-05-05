"""
Pathshala AI - FastAPI Backend
Bilingual AI tutor for rural primary education in Nepal
"""
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.pdf_loader import PDFLoader, PDFLoadError
from services.chunker import Chunker
from models.schemas import TextbookUploadResponse

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Pathshala AI",
    description="Bilingual AI tutor for rural primary education in Nepal",
    version="0.1.0"
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for chunks (temporary)
textbook_chunks_store = {}  # {upload_id: {filename, chunks: [...], total_chars}}

# Initialize services
pdf_loader = PDFLoader()
chunker = Chunker(chunk_size=512, chunk_overlap=64)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pathshala-ai-backend",
        "version": "0.1.0"
    }


@app.post("/upload-textbook", response_model=TextbookUploadResponse)
async def upload_textbook(file: UploadFile = File(...)):
    """
    Upload and process a textbook PDF
    
    Args:
        file: PDF file to upload
    
    Returns:
        Upload response with chunks information
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )
        
        # Extract text from PDF
        extracted_text = await pdf_loader.load_pdf_from_bytes(file_bytes, file.filename)
        
        # Split into chunks
        chunks = chunker.chunk_text(extracted_text)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No readable content found in PDF"
            )
        
        # Generate upload ID and store chunks
        upload_id = str(uuid.uuid4())
        textbook_chunks_store[upload_id] = {
            "filename": file.filename,
            "chunks": chunks,
            "total_chars": len(extracted_text)
        }
        
        return TextbookUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            status="success",
            num_chunks=len(chunks),
            total_characters=len(extracted_text),
            message=f"Successfully processed {file.filename} into {len(chunks)} chunks"
        )
    
    except PDFLoadError as e:
        raise HTTPException(
            status_code=400,
            detail=f"PDF processing error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/textbooks/{upload_id}/preview")
async def get_textbook_preview(upload_id: str, chunk_count: int = 5):
    """
    Get a preview of uploaded textbook chunks
    
    Args:
        upload_id: Upload ID
        chunk_count: Number of chunks to preview
    
    Returns:
        Preview of chunks
    """
    if upload_id not in textbook_chunks_store:
        raise HTTPException(
            status_code=404,
            detail="Textbook not found"
        )
    
    textbook_data = textbook_chunks_store[upload_id]
    chunks = textbook_data["chunks"][:chunk_count]
    
    return {
        "upload_id": upload_id,
        "filename": textbook_data["filename"],
        "total_chunks": len(textbook_data["chunks"]),
        "preview_chunks": chunk_count,
        "chunks": chunks
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV", "development") == "development"
    )

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Document
from app.services.document_service import process_and_store_document
import os

router = APIRouter()

@router.get("")
async def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }
        for doc in docs
    ]

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = file.filename.split('.')[-1].lower() if file.filename else ""
    if ext not in ["txt", "pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Only .txt, .pdf, .docx files are supported")
        
    try:
        content = await file.read()
        doc = await process_and_store_document(db, content, file.filename)
        return {
            "id": doc.id,
            "filename": doc.filename,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    db.delete(doc)
    db.commit()
    return {"success": True}

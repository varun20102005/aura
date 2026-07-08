import logging
from sqlalchemy.orm import Session
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from ..models.core import Claim, ClaimDocument, ClaimEmbedding

logger = logging.getLogger(__name__)

# Global model loader to avoid reloading on every request
_model = None

def get_model():
    global _model
    if _model is None and SentenceTransformer is not None:
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_claim_embedding(db: Session, claim_id: int):
    """
    Generates an embedding for a claim using normalized text and stores it in the DB.
    """
    model = get_model()
    if not model:
        logger.warning("SentenceTransformer is not installed. Skipping embedding generation.")
        return

    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return
        
    doc = db.query(ClaimDocument).filter_by(claim_id=claim.id).first()
    
    # Normalize text: Combine structural fields with OCR text
    components = [
        f"Procedure: {claim.procedure_code}",
        f"Provider: {claim.provider_ref}",
        f"Patient: {claim.patient_ref}",
        f"Amount: {claim.billed_amount}"
    ]
    if doc and doc.ocr_text:
        components.append(f"Document Text: {doc.ocr_text}")
        
    normalized_text = " | ".join(components)
    
    logger.info(f"Generating embedding for claim {claim_id}...")
    # Encode returns a numpy array. We convert to list for pgvector.
    vector = model.encode(normalized_text).tolist()
    
    embedding_record = ClaimEmbedding(
        claim_id=claim.id,
        embedding=vector,
        model_version='all-MiniLM-L6-v2'
    )
    db.add(embedding_record)
    db.commit()
    logger.info(f"Successfully saved embedding for claim {claim_id}.")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base, Claim, ClaimDocument, ProcedureValidationFlag
from app.services.validation_service import run_procedure_validation

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.create_all(bind=engine, tables=tables)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_invalid_code_rule(test_db):
    claim = Claim(procedure_code="UNKNOWN_999", provider_ref="PRV1")
    test_db.add(claim)
    test_db.commit()
    
    run_procedure_validation(test_db, claim.id)
    
    flags = test_db.query(ProcedureValidationFlag).filter_by(claim_id=claim.id).all()
    assert len(flags) == 1
    assert flags[0].flag_type == "invalid_code"

def test_description_mismatch_rule(test_db):
    # '99213' has keyword 'outpatient', 'low complexity' in our stub reference
    claim = Claim(procedure_code="99213", provider_ref="PRV1")
    test_db.add(claim)
    test_db.commit()
    
    doc = ClaimDocument(claim_id=claim.id, file_path="dummy.pdf", ocr_text="Patient admitted to ER. High complexity case.")
    test_db.add(doc)
    test_db.commit()
    
    run_procedure_validation(test_db, claim.id)
    
    flags = test_db.query(ProcedureValidationFlag).filter_by(claim_id=claim.id).all()
    # Should flag description_mismatch
    mismatch = [f for f in flags if f.flag_type == "description_mismatch"]
    assert len(mismatch) == 1

def test_rare_combination_rule(test_db):
    # Create >10 historical claims for PRV_RARE
    for i in range(15):
        test_db.add(Claim(procedure_code="99213", provider_ref="PRV_RARE"))
        
    # Now create one claim with a rare code '11111'
    rare_claim = Claim(procedure_code="11111", provider_ref="PRV_RARE")
    test_db.add(rare_claim)
    test_db.commit()
    
    run_procedure_validation(test_db, rare_claim.id)
    
    flags = test_db.query(ProcedureValidationFlag).filter_by(claim_id=rare_claim.id).all()
    rare_flag = [f for f in flags if f.flag_type == "rare_combination"]
    assert len(rare_flag) == 1
    
def test_get_validation_flags_endpoint(client, officer_token, test_db):
    # This just ensures endpoint exists and works with RBAC
    response = client.get("/claims/999/procedure-validation", headers={"Authorization": f"Bearer {officer_token}"})
    assert response.status_code == 200
    assert response.json() == []

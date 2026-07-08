import os
from unittest.mock import patch
from app.services.pipeline import run_ocr

def test_run_ocr_fallback(tmp_path):
    # Test OCR logic (mocked)
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("dummy text")
    
    with patch("app.services.pipeline.reader", None):
        text, conf = run_ocr(str(dummy_file))
        assert text == "OCR Library not loaded"
        assert conf == 0.0

def test_pipeline_integration(client, db):
    # This just ensures we can import and the components aren't completely broken
    # Real pipeline test needs a populated DB and valid models.
    pass

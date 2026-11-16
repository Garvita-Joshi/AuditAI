"""
AuditAI — Dual-engine OCR: PaddleOCR (primary) with pytesseract fallback.

The engine automatically detects which OCR library is available and falls back
gracefully. A module-level singleton `ocr_engine` is provided for reuse.
"""
import logging
import os
from pathlib import Path
import shutil
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)


class OcrEngine:
    """
    Dual-engine OCR that tries PaddleOCR first and falls back to pytesseract.

    Usage:
        from backend.app.ocr.engine import ocr_engine
        text, confidence, method = ocr_engine.extract_text(preprocessed_image)
    """

    def __init__(self):
        from backend.app.config import OCR_PRIMARY_ENGINE, TESSERACT_CMD
        self._paddle_ocr = None
        self._paddle_available = False
        self._tesseract_available = False
        self._rapid_ocr = None
        self._rapid_attempted = False

        # Try to initialize PaddleOCR
        try:
            if OCR_PRIMARY_ENGINE != 'paddleocr':
                raise ImportError('PaddleOCR is not the configured primary engine')
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
            )
            self._paddle_available = True
            logger.info("PaddleOCR initialized successfully.")
        except Exception as e:
            logger.warning("PaddleOCR not available: %s. Will use pytesseract.", e)

        # Check if pytesseract is available
        try:
            import pytesseract  # noqa: F401
            candidates = [
                Path(TESSERACT_CMD),
                Path("/opt/homebrew/bin/tesseract"),
                Path("/usr/local/bin/tesseract"),
                Path(shutil.which("tesseract") or ""),
                Path(os.getenv('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR/tesseract.exe',
                Path(os.getenv('LOCALAPPDATA', '')) / 'Programs/Tesseract-OCR/tesseract.exe'
            ]
            executable = next((str(p) for p in candidates if p and p.is_file()), None) or shutil.which(TESSERACT_CMD)
            if executable:
                pytesseract.pytesseract.tesseract_cmd = executable
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
                logger.info("Tesseract initialized successfully at %s", executable)
            else:
                logger.warning('Tesseract executable not found; set TESSERACT_CMD.')
        except Exception as e:
            logger.warning("pytesseract not available: %s", e)

    def extract_text(self, image: np.ndarray) -> Tuple[str, float, str]:
        """
        Extract text from a preprocessed image with engine prioritization.

        Args:
            image: Preprocessed numpy array (grayscale or BGR).

        Returns:
            Tuple of (raw_text, confidence_0_to_1, method_used).
            method_used is one of 'tesseract', 'rapidocr', 'paddleocr', or 'failed'.
        """
        if image is None or image.size == 0:
            return ("", 0.0, "failed")

        from backend.app.config import OCR_PRIMARY_ENGINE

        # Primary Option: Tesseract (High accuracy with --psm 6 and contrast enhancement)
        if (OCR_PRIMARY_ENGINE == "tesseract" or not self._rapid_attempted) and self._tesseract_available:
            try:
                text, confidence = self._extract_tesseract(image)
                if text and len(text.strip()) > 5:
                    return (text, confidence, "tesseract")
            except Exception as e:
                logger.warning("Primary Tesseract extraction failed: %s", e)

        # Fallback 1: RapidOCR (Bundled CPU models)
        if not self._rapid_attempted:
            self._rapid_attempted = True
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
            except Exception as exc:
                logger.warning('RapidOCR unavailable: %s', exc)

        if self._rapid_ocr is not None:
            try:
                result, _ = self._rapid_ocr(image)
                if result:
                    extracted = '\n'.join(str(row[1]) for row in result)
                    if extracted.strip():
                        return (extracted, float(np.mean([float(row[2]) for row in result])), 'rapidocr')
            except Exception as exc:
                logger.warning('RapidOCR failed: %s', exc)

        # Fallback 2: PaddleOCR if configured
        if self._paddle_available:
            try:
                text, confidence = self._extract_paddle(image)
                if text.strip():
                    return (text, confidence, "paddleocr")
                logger.info("PaddleOCR returned empty text, falling back.")
            except Exception as e:
                logger.warning("PaddleOCR extraction failed: %s", e)

        # Fallback 3: Tesseract if not already tried
        if self._tesseract_available:
            try:
                text, confidence = self._extract_tesseract(image)
                if text.strip():
                    return (text, confidence, "tesseract")
            except Exception as e:
                logger.warning("Tesseract extraction failed: %s", e)

        return ("", 0.0, "failed")

    def _extract_tesseract(self, image: np.ndarray, config: str = "--psm 6") -> Tuple[str, float]:
        """
        Run pytesseract with optimized page segmentation and error-tolerant parsing.
        """
        import pytesseract

        # Pass 1: Try --psm 6 (Uniform block of text / receipt table)
        raw_text = pytesseract.image_to_string(image, config=config).strip()

        # Pass 2: If very short text extracted, try --psm 4 (Single column variable text)
        if len(raw_text) < 20 and config != "--psm 4":
            alt_text = pytesseract.image_to_string(image, config="--psm 4").strip()
            if len(alt_text) > len(raw_text):
                raw_text = alt_text
                config = "--psm 4"

        # Calculate word confidence
        try:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, config=config
            )
            confidences = [float(c) for c in data.get("conf", []) if float(c) > 0]
            avg_confidence = (
                sum(confidences) / len(confidences) / 100.0
                if confidences
                else (0.85 if raw_text else 0.0)
            )
        except Exception:
            avg_confidence = 0.85 if raw_text else 0.0

        return (raw_text, avg_confidence)

        return (raw_text, avg_confidence)


# Module-level singleton for reuse across the application
ocr_engine = OcrEngine()

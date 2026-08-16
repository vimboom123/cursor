from __future__ import annotations

from typing import Protocol


class OCREngine(Protocol):
    def recognize(self, image_bytes: bytes) -> str: ...


class MissingOCREngine:
    """未安装 OCR 依赖时的占位。明确失败，避免静默丢数据。"""

    def recognize(self, image_bytes: bytes) -> str:
        raise RuntimeError(
            "当前环境未启用 OCR。请安装: pip install 'awcollector[ocr]'"
        )


class ScriptedOCREngine:
    """测试或预置结果用。生产环境应换成 RapidOCR。"""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.calls = 0

    def recognize(self, image_bytes: bytes) -> str:
        self.calls += 1
        if not image_bytes:
            return ""
        return self.text


def load_ocr_engine(prefer_rapid: bool = True) -> OCREngine:
    if prefer_rapid:
        try:
            from rapidocr_onnxruntime import RapidOCR

            engine = RapidOCR()

            class RapidOCREngine:
                def recognize(self, image_bytes: bytes) -> str:
                    import io

                    from PIL import Image

                    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    result, _ = engine(image)
                    if not result:
                        return ""
                    return "\n".join(str(item[1]) for item in result if len(item) > 1)

            return RapidOCREngine()
        except Exception:
            pass
    return MissingOCREngine()

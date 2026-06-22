import base64
import io
import logging
from typing import Optional

from fastapi import UploadFile
from PIL import Image, ImageOps

from app.config import settings
from app.utils.exceptions import FileTooLargeError, UnsupportedFileTypeError, ImageProcessingError

logger = logging.getLogger(__name__)

# 디컴프레션 폭탄 방지(CWE-409): 작은 파일이 거대 픽셀로 전개되어 메모리를 고갈시키는 것을 차단.
# 초과 시 PIL이 DecompressionBombError 발생.
Image.MAX_IMAGE_PIXELS = 24_000_000  # ~24MP 상한

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class FileHandler:
    @staticmethod
    async def validate_image(file: UploadFile) -> None:
        """이미지 파일 검증 — 확장자·크기(메모리 한도 내)·실제 이미지/폭탄 검증."""
        # 확장자 검증 (filename 없으면 거부 — 검증 우회 방지, CWE-434)
        if not file.filename or "." not in file.filename:
            raise UnsupportedFileTypeError(settings.ALLOWED_EXTENSIONS)
        ext = f".{file.filename.rsplit('.', 1)[-1].lower()}"
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(settings.ALLOWED_EXTENSIONS)

        # 크기 검증 — 한도+1 바이트까지만 읽어 대용량 업로드 메모리 DoS 방지(CWE-400)
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        contents = await file.read(max_bytes + 1)
        await file.seek(0)
        if len(contents) > max_bytes:
            raise FileTooLargeError(settings.MAX_FILE_SIZE_MB)

        # 실제 이미지 여부 + 포맷/폭탄 검증(CWE-409/434) — 확장자 위조 차단
        try:
            with Image.open(io.BytesIO(contents)) as probe:
                fmt = (probe.format or "").upper()
                probe.verify()  # 구조 검증(폭탄이면 MAX_IMAGE_PIXELS로 DecompressionBombError)
        except Image.DecompressionBombError:
            raise FileTooLargeError(settings.MAX_FILE_SIZE_MB)
        except (FileTooLargeError, UnsupportedFileTypeError):
            raise
        except Exception:
            raise UnsupportedFileTypeError(settings.ALLOWED_EXTENSIONS)
        if fmt not in _ALLOWED_FORMATS:
            raise UnsupportedFileTypeError(settings.ALLOWED_EXTENSIONS)

    @staticmethod
    async def image_to_base64(file: UploadFile) -> str:
        """이미지를 Base64로 변환 (필요시 리사이징)"""
        try:
            contents = await file.read()

            # 이미지 최적화 (필요시 리사이징)
            image = Image.open(io.BytesIO(contents))

            # RGBA를 RGB로 변환 (PNG 투명도 처리)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # 최대 크기 제한 (2048px)
            max_size = 2048
            if max(image.size) > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # JPEG로 변환
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            contents = buffer.getvalue()

            return base64.b64encode(contents).decode('utf-8')
        except Image.DecompressionBombError:
            raise ImageProcessingError("이미지 크기가 허용 범위를 초과했습니다.")
        except Exception as e:
            # 내부 상세는 서버 로그만, 사용자에겐 일반화 메시지(정보노출 방지 CWE-209)
            logger.warning("image_to_base64 failed: %s", e)
            raise ImageProcessingError("이미지 처리에 실패했습니다.")

    @staticmethod
    def make_thumbnail_data_uri(
        image_base64: str, max_dim: int = 480, quality: int = 80
    ) -> Optional[str]:
        """분석 원본 이미지 base64 → 긴 변 max_dim(기본 480px)로 축소(비율 유지) → JPEG data URI.

        분석기록(history)에서 사진을 결과와 함께 경량으로 보여주기 위한 thumbnail.
        축소만 하고 확대는 안 함. 실패 시 None 반환(저장만 생략 — 분석은 정상, 사진은 부가 표시).
        반환 형식: 'data:image/jpeg;base64,...' (프론트 <img src>에 바로 사용).
        """
        try:
            raw = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(raw))
            try:
                image = ImageOps.exif_transpose(image)  # 휴대폰 EXIF 회전 보정
            except Exception:  # noqa: BLE001
                pass
            if image.mode != "RGB":
                image = image.convert("RGB")  # JPEG는 알파 미지원
            image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)  # 비율 유지, 축소만
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("make_thumbnail_data_uri failed: %s", exc)
            return None


file_handler = FileHandler()

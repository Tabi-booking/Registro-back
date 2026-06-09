from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.repositories.tabi_repository import (
    DocumentoRestauranteRepository,
    RestauranteImagenRepository,
    RestauranteRepository,
)
from app.schemas.onboarding import ConfirmUploadRequest, PresignedUrlRequest, PresignedUrlResponse
from app.utils.sanitizers import sanitize_filename
from app.utils.storage import (
    create_signed_upload_url,
    public_url,
    validate_restaurant_storage_key,
)
from app.utils.validators import validate_file_size, validate_mime_type

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentoRestauranteRepository(session)
        self.imagen_repo = RestauranteImagenRepository(session)
        self.restaurante_repo = RestauranteRepository(session)

    def _generate_storage_key(
        self, restaurant_id: int, document_type: str, file_name: str
    ) -> str:
        safe_name = sanitize_filename(file_name)
        unique = uuid.uuid4().hex[:8]
        return f"restaurants/{restaurant_id}/{document_type}/{unique}_{safe_name}"

    async def get_presigned_url(
        self,
        request: PresignedUrlRequest,
        restaurant_id: int,
        user_id: int,
    ) -> PresignedUrlResponse:
        del user_id

        if not validate_mime_type(request.content_type):
            raise BadRequestError(f"Content type '{request.content_type}' is not allowed")

        storage_key = self._generate_storage_key(
            restaurant_id, request.document_type, request.file_name
        )
        upload_url, fields, expires_in = await create_signed_upload_url(storage_key)

        logger.info(
            "Upload URL generated for restaurant_id=%s key=%s type=%s",
            restaurant_id,
            storage_key,
            request.document_type,
        )

        return PresignedUrlResponse(
            upload_url=upload_url,
            storage_key=storage_key,
            expires_in=expires_in,
            fields={
                "Content-Type": request.content_type,
                "x-amz-meta-restaurant-id": str(restaurant_id),
                "x-amz-meta-document-type": request.document_type,
                **fields,
            },
        )

    async def confirm_upload(
        self,
        request: ConfirmUploadRequest,
        restaurant_id: int,
        user_id: int,
        ip_address: str | None = None,
    ) -> dict:
        del user_id, ip_address

        if not validate_mime_type(request.mime_type):
            raise BadRequestError(f"MIME type '{request.mime_type}' is not allowed")

        if not validate_file_size(request.file_size, settings.MAX_FILE_SIZE_BYTES):
            raise BadRequestError(
                f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        validate_restaurant_storage_key(request.storage_key, restaurant_id)

        file_url = public_url(request.storage_key)
        doc_type = request.document_type

        if doc_type == "logo":
            restaurante = await self.restaurante_repo.get(restaurant_id)
            if restaurante:
                await self.restaurante_repo.update(restaurante, imagen_destacada=file_url)
            result_id = restaurant_id
            result_type = "logo"
        elif doc_type == "cover":
            image = await self.imagen_repo.upsert_by_storage_key(
                restaurant_id,
                url=file_url,
                storage_key=request.storage_key,
            )
            result_id = image.id
            result_type = "cover"
        else:
            existing = await self.doc_repo.get_by_storage_key(request.storage_key)
            if existing:
                raise BadRequestError("This file has already been confirmed")
            doc = await self.doc_repo.create(
                id_restaurante=restaurant_id,
                tipo=doc_type,
                url=file_url,
                nombre_archivo=sanitize_filename(request.file_name),
                tamano_bytes=request.file_size,
                mime_type=request.mime_type,
                storage_key=request.storage_key,
            )
            result_id = doc.id
            result_type = doc.tipo

        await self.session.commit()

        logger.info(
            "Upload confirmed: id=%s restaurant_id=%s key=%s type=%s",
            result_id,
            restaurant_id,
            request.storage_key,
            doc_type,
        )

        return {
            "document_id": result_id,
            "storage_key": request.storage_key,
            "file_url": file_url,
            "document_type": result_type,
        }

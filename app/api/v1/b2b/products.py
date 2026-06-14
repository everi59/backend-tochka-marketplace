from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1.common import error_response, get_seller, get_store, hash_password, iso, parse_deep, require_service_key, verify_password
from app.core.repositories.category_repository import CategoryRepository
from app.core.repositories.product_repository import ProductRepository
from app.core.store import ServiceError
from app.infrastructure.database.models.product import Product, ProductCharacteristic, ProductImage, ProductStatus

router = APIRouter()


class ProductImagePayload(BaseModel):
    url: str
    ordering: int = 0
    alt: str = ""


class ProductCharacteristicPayload(BaseModel):
    name: str
    value: str


class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category_id: UUID
    description: str = Field(..., min_length=1, max_length=5000)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=255)
    images: list[ProductImagePayload] = Field(default_factory=list)
    characteristics: list[ProductCharacteristicPayload] = Field(default_factory=list)


def _slugify(title: str) -> str:
    return title.lower().replace(" ", "-")


def _product_response_from_db(product: Product) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "seller_id": str(product.seller_id) if product.seller_id else None,
        "category_id": str(product.category_id) if product.category_id else None,
        "title": product.title,
        "slug": product.slug,
        "description": product.description,
        "status": product.status.value if hasattr(product.status, "value") else str(product.status),
        "deleted": False,
        "blocking_reason_id": None,
        "moderator_comment": None,
        "images": [
            {"id": str(image.id), "url": image.url, "alt": "", "ordering": image.order, "is_main": image.order == 0}
            for image in getattr(product, "images", [])
        ],
        "characteristics": [
            {"id": str(item.id), "name": item.name, "value": item.value}
            for item in getattr(product, "characteristics", [])
        ],
        "skus": [],
        "created_at": iso(product.created_at),
        "updated_at": iso(product.updated_at),
    }


@router.get("/products")
async def b2b_list_products(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_service_key: Optional[str] = Header(None),
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    category: Optional[str] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "date_desc",
    ids: Optional[str] = None,
    include_deleted: bool = False,
):
    store = get_store(request)
    try:
        if x_service_key is not None:
            require_service_key(x_service_key)
            filters = {"category_id": category_id or category, "attributes": {}}
            mapped_sort = {"date_desc": "new", "created_desc": "new", "new": "new", "price_asc": "price_asc", "price_desc": "price_desc", "popular": "popular"}.get(sort)
            if mapped_sort is None:
                raise ServiceError("BAD_REQUEST", "Invalid sort value. Allowed values: price_asc, price_desc, date_desc", 400)
            response = store.list_catalog_products(limit, offset, search, mapped_sort, filters)
            if ids:
                requested_ids = {item.strip() for item in ids.split(",") if item.strip()}
                response["items"] = [item for item in response["items"] if item["id"] in requested_ids]
                response["total_count"] = len(response["items"])
            response["items"] = [store.product_response_b2b(item["id"], public=True) for item in response["items"]]
            return response
        seller = get_seller(store, authorization)
        return store.list_seller_products(seller["id"], limit, offset, status, include_deleted)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/products")
async def b2b_create_product(
    payload: ProductCreate,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    store = get_store(request)
    session = None
    try:
        seller = get_seller(store, authorization)
        db_connection = getattr(request.app.state, "db_connection", None)
        payload_data = payload.model_dump(exclude_none=True)
        payload_data["category_id"] = str(payload.category_id)
        if db_connection is None:
            product = store.create_product(seller["id"], payload_data)
            return JSONResponse(status_code=201, content=jsonable_encoder(store.product_response_b2b(product["id"])))

        session = db_connection.get_session()
        product_repo = ProductRepository(session)
        category_repo = CategoryRepository(session)
        category = await category_repo.get_by_id(payload.category_id)
        if not category:
            raise ServiceError("NOT_FOUND", "Category not found", 404)

        slug = payload.slug or _slugify(payload.title)
        existing = await product_repo.get_by_seller_and_slug(UUID(seller["id"]), slug)
        if existing:
            raise ServiceError("CONFLICT", "Product slug already exists", 409)

        product = Product(
            seller_id=UUID(seller["id"]),
            category_id=payload.category_id,
            title=payload.title,
            slug=slug,
            description=payload.description,
            status=ProductStatus.CREATED,
            images=[ProductImage(url=image.url, order=image.ordering) for image in payload.images],
            characteristics=[ProductCharacteristic(name=item.name, value=item.value) for item in payload.characteristics],
        )
        created = await product_repo.create(product)
        await product_repo.session.refresh(created, attribute_names=["images", "characteristics"])
        return JSONResponse(status_code=201, content=jsonable_encoder(_product_response_from_db(created)))
    except ServiceError as exc:
        return error_response(exc)
    finally:
        if session is not None:
            await session.close()


@router.get("/products/{product_id}")
async def b2b_get_product(product_id: str, request: Request, authorization: Optional[str] = Header(None), x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        public = x_service_key is not None
        if not public:
            seller = get_seller(store, authorization)
            store.ensure_seller_owns_product(seller["id"], store.require_product(product_id))
        else:
            require_service_key(x_service_key)
        return store.product_response_b2b(product_id, public=public)
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/products/{product_id}")
async def b2b_patch_product(product_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.update_product(seller["id"], product_id, payload)
        return store.product_response_b2b(product_id)
    except ServiceError as exc:
        return error_response(exc)


@router.put("/products/{product_id}")
async def b2b_put_product(product_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    return await b2b_patch_product(product_id, payload, request, authorization)


@router.delete("/products/{product_id}", status_code=204)
async def b2b_delete_product(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.delete_product(seller["id"], product_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/products/{product_id}/images")
async def b2b_add_product_image(product_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        product = store.require_product(product_id)
        store.ensure_seller_owns_product(seller["id"], product)
        image = {"image_id": payload.get("image_id"), "url": payload["url"], "ordering": payload.get("ordering", 0)}
        built = store._make_image(image)
        product["images"].append(built)
        return JSONResponse(status_code=201, content=jsonable_encoder(built))
    except KeyError:
        return error_response(ServiceError("VALIDATION_ERROR", "Field 'url' is required", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/products/images/{image_id}")
async def b2b_patch_product_image(image_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for product in store.products.values():
            for image in product["images"]:
                if image["id"] == image_id:
                    if "url" in payload and payload["url"] is not None:
                        image["url"] = payload["url"]
                    if "ordering" in payload and payload["ordering"] is not None:
                        image["ordering"] = int(payload["ordering"])
                    return image
        raise ServiceError("NOT_FOUND", "Image not found", 404)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/products/images/{image_id}", status_code=204)
async def b2b_delete_product_image(image_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for product in store.products.values():
            product["images"] = [image for image in product["images"] if image["id"] != image_id]
        return Response(status_code=204)    
    except ServiceError as exc:
        return error_response(exc)



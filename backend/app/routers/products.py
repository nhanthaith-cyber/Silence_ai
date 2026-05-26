from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.models import Product
from app.services.product_service import (
    search_products,
    get_product_by_id,
    get_product_by_slug,
    check_stock,
    get_size_recommendation,
    product_to_dict,
)
from datetime import datetime
import uuid
import json

router = APIRouter()


# --- Pydantic Schemas ---

class ProductCreate(BaseModel):
    name: str
    slug: str
    category: str  # ao, quan, jacket, phu_kien
    subcategory: Optional[str] = None
    description: Optional[str] = None
    price: int  # VND
    sale_price: Optional[int] = None
    sizes_available: Optional[str] = "{}"  # JSON: {"S": 5, "M": 12, "L": 8}
    size_chart: Optional[str] = "{}"  # JSON bảng size
    fabric: Optional[str] = None
    fabric_properties: Optional[str] = "{}"  # JSON: {"stretch": true, "shrinkage": "2-3%"}
    fit_type: str = "regular"  # relaxed, regular, slim, oversized
    color: Optional[str] = None
    images: Optional[str] = "[]"  # JSON array URLs
    care_instructions: Optional[str] = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    sale_price: Optional[int] = None
    sizes_available: Optional[str] = None
    size_chart: Optional[str] = None
    fabric: Optional[str] = None
    fabric_properties: Optional[str] = None
    fit_type: Optional[str] = None
    color: Optional[str] = None
    images: Optional[str] = None
    care_instructions: Optional[str] = None
    is_active: Optional[bool] = None


class SizeRecommendationRequest(BaseModel):
    height: int  # Chiều cao (cm)
    weight: int  # Cân nặng (kg)
    preferred_fit: Optional[str] = None  # relaxed, regular, slim, oversized


# --- Endpoints ---

@router.get("")
async def list_products(
    category: Optional[str] = None,
    fit_type: Optional[str] = None,
    size: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Lấy danh sách sản phẩm với bộ lọc và phân trang."""
    items, total = search_products(
        db,
        category=category,
        fit_type=fit_type,
        size=size,
        min_price=min_price,
        max_price=max_price,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [product_to_dict(item) for item in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{product_id}")
async def get_product(product_id: str, db: Session = Depends(get_db)):
    """Lấy chi tiết sản phẩm theo ID."""
    item = get_product_by_id(db, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return product_to_dict(item)


@router.get("/slug/{slug}")
async def get_product_slug(slug: str, db: Session = Depends(get_db)):
    """Lấy chi tiết sản phẩm theo slug."""
    item = get_product_by_slug(db, slug)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return product_to_dict(item)


@router.post("")
async def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    """Tạo sản phẩm mới (admin)."""
    # Kiểm tra slug trùng
    existing = get_product_by_slug(db, body.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug đã tồn tại")

    item = Product(
        id=str(uuid.uuid4()),
        name=body.name,
        slug=body.slug,
        category=body.category,
        subcategory=body.subcategory,
        description=body.description,
        price=body.price,
        sale_price=body.sale_price,
        sizes_available=body.sizes_available,
        size_chart=body.size_chart,
        fabric=body.fabric,
        fabric_properties=body.fabric_properties,
        fit_type=body.fit_type,
        color=body.color,
        images=body.images,
        care_instructions=body.care_instructions,
        is_active=body.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return product_to_dict(item)


@router.put("/{product_id}")
async def update_product(
    product_id: str, body: ProductUpdate, db: Session = Depends(get_db)
):
    """Cập nhật sản phẩm (admin)."""
    item = get_product_by_id(db, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    # Kiểm tra slug trùng nếu đổi slug
    if body.slug and body.slug != item.slug:
        existing = get_product_by_slug(db, body.slug)
        if existing:
            raise HTTPException(status_code=400, detail="Slug đã tồn tại")

    for field, val in body.dict(exclude_none=True).items():
        setattr(item, field, val)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return product_to_dict(item)


@router.delete("/{product_id}")
async def delete_product(product_id: str, db: Session = Depends(get_db)):
    """Xoá sản phẩm (admin)."""
    item = get_product_by_id(db, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    db.delete(item)
    db.commit()
    return {"success": True}


@router.get("/{product_id}/stock/{size}")
async def get_stock(product_id: str, size: str, db: Session = Depends(get_db)):
    """Kiểm tra tồn kho theo sản phẩm và size."""
    item = get_product_by_id(db, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    stock = check_stock(item, size)
    return {
        "product_id": product_id,
        "size": size,
        "in_stock": stock > 0,
        "quantity": stock,
    }


@router.post("/{product_id}/recommend-size")
async def recommend_size(
    product_id: str,
    body: SizeRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Gợi ý size dựa trên chiều cao, cân nặng và kiểu fit yêu thích."""
    item = get_product_by_id(db, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    recommendation = get_size_recommendation(
        product=item,
        height=body.height,
        weight=body.weight,
        preferred_fit=body.preferred_fit,
    )
    return recommendation

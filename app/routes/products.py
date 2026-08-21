from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models.product import Product
from ..middleware.auth_middleware import get_optional_uid

router = APIRouter()


def _product_to_dict(product: Product) -> dict:
    import json as _json
    images = []
    if product.images:
        try:
            images = _json.loads(product.images)
        except Exception:
            images = [product.images] if product.images else []

    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "original_price": product.original_price,
        "stock": product.stock,
        "images": images,
        "category": product.category,
        "type": product.type,            # 'diy_kit' or 'electronics'
        "is_active": product.is_active,
        "linked_course_id": product.linked_course_id,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


@router.get("", include_in_schema=False)
@router.get("/")
def get_products(
    product_type: Optional[str] = None,
    category: Optional[str] = None,
    uid: Optional[str] = Depends(get_optional_uid),
    db: Session = Depends(get_db),
):
    """
    Returns all active products.
    Optionally filters by product_type ('diy_kit' or 'electronics') or category.
    """
    query = db.query(Product).filter(Product.is_active == True)
    if product_type:
        query = query.filter(Product.type == product_type)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    products = query.order_by(Product.id.asc()).all()
    return [_product_to_dict(p) for p in products]


@router.get("/{product_id}")
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Returns full product details for a specific active product."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_dict(product)


@router.post("/", status_code=201)
def create_product(
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint to create a product.
    TODO: Add admin JWT role check.
    """
    import json as _json
    images_val = body.get("images", [])
    images_str = _json.dumps(images_val) if isinstance(images_val, list) else images_val

    product = Product(
        name=body.get("name", ""),
        description=body.get("description"),
        price=float(body.get("price", 0.0)),
        original_price=float(body.get("original_price")) if body.get("original_price") else None,
        stock=int(body.get("stock", 0)),
        images=images_str,
        category=body.get("category"),
        type=body.get("type", "diy_kit"),
        is_active=bool(body.get("is_active", True)),
        linked_course_id=body.get("linked_course_id"),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_to_dict(product)

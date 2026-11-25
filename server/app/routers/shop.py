from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import DB, CurrentUser
from app.models import Product
from app.schemas import OrderIn, OrderOut, ProductOut
from app.services.orders import cancel_order, create_order
from app.services.presenters import order_out, product_out

router = APIRouter(tags=["shop"])


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: DB, category: str | None = None, featured: Annotated[bool, Query()] = False
) -> list[ProductOut]:
    stmt = select(Product).where(Product.active.is_(True))
    if category and category != "全部":
        stmt = stmt.where(Product.category == category)
    if featured:
        stmt = stmt.where(Product.featured.is_(True))
    products = db.scalars(stmt.order_by(Product.sort_order, Product.id)).all()
    return [product_out(p) for p in products]


@router.post("/orders", response_model=OrderOut)
def post_order(data: OrderIn, db: DB, user: CurrentUser) -> OrderOut:
    return order_out(create_order(db, user, data))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def post_cancel(order_id: int, db: DB, user: CurrentUser) -> OrderOut:
    return order_out(cancel_order(db, user, order_id))

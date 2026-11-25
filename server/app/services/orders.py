from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.errors import bad_request, not_found
from app.models import Order, Product, User
from app.schemas import Address, OrderIn
from app.services.ledger import INSUFFICIENT_BALANCE, apply_delta, lock_user

ORDER_NOT_FOUND = "订单不存在"
PRODUCT_NOT_FOUND = "商品不存在"
ADDRESS_REQUIRED = "请填写收货地址（收货人、手机号、详细地址）"
OUT_OF_STOCK = "库存不足"
MIN_QTY, MAX_QTY = 1, 99


def _address_ok(addr: Address | None) -> bool:
    return bool(addr and addr.name.strip() and addr.phone.strip() and addr.detail.strip())


def create_order(db: Session, user: User, data: OrderIn) -> Order:
    if not (MIN_QTY <= data.quantity <= MAX_QTY):
        raise bad_request("兑换数量需在 1–99 之间")
    # Lock order: user row first, then product row (same as cancel_order).
    locked = lock_user(db, user.id)
    product = db.scalars(
        select(Product).where(Product.id == data.product_id, Product.active.is_(True))
        .with_for_update().execution_options(populate_existing=True)
    ).one_or_none()
    if product is None:
        raise not_found(PRODUCT_NOT_FOUND)
    if product.kind == "goods" and not _address_ok(data.address):
        raise bad_request(ADDRESS_REQUIRED)
    if product.stock < data.quantity:
        raise bad_request(OUT_OF_STOCK)

    total = product.price * data.quantity
    if locked.flower_balance < total:
        raise bad_request(INSUFFICIENT_BALANCE)

    is_goods = product.kind == "goods"
    product.stock = product.stock - data.quantity
    order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=data.quantity,
        unit_price=product.price,
        total_price=total,
        status="pending_shipment" if is_goods else "completed",
        address=data.address.model_dump() if (is_goods and data.address) else None,
    )
    db.add(order)
    db.flush()
    apply_delta(db, locked, -total, "redeem", ref_type="order", ref_id=order.id)
    db.commit()
    db.refresh(order)
    return order


def lock_order(db: Session, order_id: int) -> Order:
    order = db.scalars(
        select(Order).where(Order.id == order_id)
        .with_for_update(of=Order).execution_options(populate_existing=True)
    ).unique().one_or_none()
    if order is None:
        raise not_found(ORDER_NOT_FOUND)
    return order


def cancel_order(db: Session, user: User, order_id: int) -> Order:
    order = lock_order(db, order_id)
    if order.user_id != user.id:
        raise not_found(ORDER_NOT_FOUND)
    if order.status != "pending_shipment":
        raise bad_request("只有待发货的订单可以取消")
    locked = lock_user(db, user.id)
    apply_delta(db, locked, order.total_price, "refund", ref_type="order", ref_id=order.id)
    db.execute(
        update(Product).where(Product.id == order.product_id)
        .values(stock=Product.stock + order.quantity)
        .execution_options(synchronize_session=False)
    )
    order.status = "cancelled"
    order.cancelled_at = datetime.now(UTC)
    db.commit()
    db.refresh(order)
    db.refresh(order.product)
    return order


def ship_order(db: Session, order_id: int, tracking_no: str | None) -> Order:
    order = lock_order(db, order_id)
    if order.status != "pending_shipment":
        raise bad_request("只有待发货的订单可以发货")
    order.status = "shipped"
    order.tracking_no = (tracking_no or "").strip() or None
    order.shipped_at = datetime.now(UTC)
    db.commit()
    db.refresh(order)
    return order

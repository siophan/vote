"""Idempotent seed: `uv run python -m app.seed`.

Inserts the 15 categories, 110 events and 5 products when missing (matched by
name/title). Existing rows are left untouched so operator edits and live
counters (participant_count, flower_count, stock) survive re-runs.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Event, Product
from app.seed_data import (
    CATEGORY_ICON_KEYS,
    CATEGORY_META,
    CATEGORY_REWARDS,
    DEFAULT_STOCK,
    PRODUCTS,
    build_events,
)


def seed(db: Session) -> dict[str, int]:
    created = {"categories": 0, "events": 0, "products": 0}

    existing_cats = {c.name: c for c in db.scalars(select(Category))}
    for order, (name, (emoji, note, image)) in enumerate(CATEGORY_META.items()):
        if name in existing_cats:
            continue
        cat = Category(name=name, note=note, emoji=emoji, icon_key=CATEGORY_ICON_KEYS[name],
                       image=image, reward_text=CATEGORY_REWARDS[name], sort_order=order)
        db.add(cat)
        existing_cats[name] = cat
        created["categories"] += 1
    db.flush()

    existing_titles = set(db.scalars(select(Event.title)))
    for row in build_events():
        if row["title"] in existing_titles:
            continue
        data = dict(row)
        category = existing_cats[data.pop("category")]
        db.add(Event(category_id=category.id, **data))
        created["events"] += 1

    existing_products = set(db.scalars(select(Product.name)))
    for order, p in enumerate(PRODUCTS):
        if p["name"] in existing_products:
            continue
        db.add(Product(stock=DEFAULT_STOCK, sort_order=order, **p))
        created["products"] += 1

    db.commit()
    return created


def main() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        created = seed(db)
    print("seed done, created:", created)


if __name__ == "__main__":
    main()

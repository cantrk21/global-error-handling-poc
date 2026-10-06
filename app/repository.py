"""PoC deposu. Gerçek veritabanı yerine sabit veri kullanır."""

_PRODUCTS = {1: {"id": 1, "name": "Python kitabı", "stock": 3}}


def find_product(product_id: int) -> dict | None:
    product = _PRODUCTS.get(product_id)
    return dict(product) if product is not None else None

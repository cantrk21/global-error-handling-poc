"""İş kuralları: FastAPI veya HTTP bağımlılığı yok."""
from .repository import find_product


class DomainError(Exception):
    pass


class ProductNotFound(DomainError):
    pass


class InsufficientStock(DomainError):
    pass


def get_product(product_id: int) -> dict:
    product = find_product(product_id)
    if product is None:
        raise ProductNotFound("Ürün bulunamadı.")
    return product


def preview_order(product_id: int, quantity: int) -> dict:
    product = get_product(product_id)
    if quantity > product["stock"]:
        raise InsufficientStock("İstenen miktar stoktan fazla.")
    # Eğitim için önizleme: stok değiştirilmez, tekrarlanabilir sonuç verir.
    return {"product_id": product_id, "quantity": quantity, "accepted": True}

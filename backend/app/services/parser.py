from app.models.product import Product


def parse_product(title: str) -> Product:
    text = title.lower()

    product = Product(
        original_title=title,
        normalized_title=title,
    )

    if "mac" in text:
        product.brand = "Apple"
        product.category = "Laptop"
        product.model = "MacBook Air"

    if "iphone" in text:
        product.brand = "Apple"
        product.category = "Phone"

    if "8gb" in text:
        product.ram = "8GB"

    if "16gb" in text:
        product.ram = "16GB"

    if "256" in text:
        product.storage = "256GB"

    if "512" in text:
        product.storage = "512GB"

    return product
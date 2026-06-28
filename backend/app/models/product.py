from dataclasses import dataclass

@dataclass
class Product:
    original_title: str
    normalized_title: str

    brand: str | None = None
    category: str | None = None
    model: str | None = None

    ram: str | None = None
    storage: str | None = None

    condition: str | None = None
    year: int | None = None
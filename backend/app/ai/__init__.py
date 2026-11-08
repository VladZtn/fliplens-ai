def create_ai_provider():
    # Lazy import keeps pure pricing/risk modules independent from optional AI SDK loading.
    from app.ai.factory import create_ai_provider as factory
    return factory()


__all__ = ["create_ai_provider"]

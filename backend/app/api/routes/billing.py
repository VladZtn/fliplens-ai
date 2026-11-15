import logging

from fastapi import APIRouter, HTTPException, Query

from app.services import billing

logger = logging.getLogger("fliplens.billing")

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

UNAVAILABLE = "Payments are temporarily unavailable. Please try again in a minute."


@router.post("/checkout")
async def start_checkout() -> dict[str, str]:
    try:
        return {"url": await billing.create_checkout_url()}
    except billing.BillingError as exc:
        logger.warning("Checkout failed: %s", exc)
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from exc


@router.get("/pass")
async def claim_pass(session_id: str = Query(max_length=200)) -> dict[str, str]:
    try:
        subscription_id = await billing.pass_from_session(session_id)
    except billing.BillingError as exc:
        logger.warning("Pass lookup failed: %s", exc)
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from exc
    if subscription_id is None:
        raise HTTPException(status_code=402, detail="This payment was not completed.")
    return {"pass": subscription_id}

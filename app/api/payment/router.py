"""Payment API router for handling Robokassa payments."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from app.api.deps import get_db
from app.db.dao import PaymentDAO, PlanDAO, TGUserDAO
from app.services import DatabaseSessionManager, RobokassaService

from .schemas import (
    CreateRobokassaRequestSchema,
    CreateRobokassaResponseSchema,
)

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


def get_robokassa() -> RobokassaService:
    """Dependency for RobokassaService."""
    return RobokassaService()


@payment_router.post(
    "/create",
    response_model=CreateRobokassaResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create a Robokassa payment",
    description=(
        "Create a payment request for a plan purchase. "
        "Returns a Robokassa payment URL and invoice ID."
    ),
    responses={
        200: {"description": "Payment created successfully"},
        404: {"description": "Plan or user not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def create_payment(
    data: CreateRobokassaRequestSchema,
    db: DatabaseSessionManager = Depends(get_db),
    robokassa: RobokassaService = Depends(get_robokassa),
) -> CreateRobokassaResponseSchema:
    """
    Create a Robokassa payment for plan purchase.

    **Workflow:**
    1. Validate plan exists and is active
    2. Validate user exists
    3. Create payment record with pending status (stores plan_id)
    4. Generate Robokassa payment link

    Args:
        data: Payment request with tg_id and plan_type.
        db: Database session manager dependency.
        robokassa: Robokassa service dependency.

    Returns:
        CreateRobokassaResponseSchema: Payment URL and invoice ID.

    Raises:
        HTTPException: 404 if plan or user not found.

    Example:
        POST /api/payments/create
        Body: {"tg_id": 123456789, "plan_type": "Base"}
        Response: {
            "payment_url": "https://auth.robokassa.ru/...",
            "invoice_id": "INV_123456789_1708092300"
        }
    """
    async with db.session() as session:
        # Get plan
        plan = await PlanDAO.get_by_active_type(data.plan_type, session)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{data.plan_type}' not found or inactive",
            )

        # Get user
        user = await TGUserDAO.get_by_telegram_id(data.tg_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Generate invoice ID
        invoice_id = f"INV_{data.tg_id}_{int(datetime.now().timestamp())}"

        # Create payment record with plan_id
        await PaymentDAO.add(
            session,
            tg_user_id=user.id,
            plan_id=plan.id,  # Store plan_id for callback
            invoice_id=invoice_id,
            amount=plan.price,
            status="pending",
        )

        # Generate payment link (convert cents to rubles)
        payment_url = robokassa.generate_payment_link(
            invoice_id=invoice_id,
            amount=plan.price / 100,
            description=f"Оплата тарифа {plan.name.value}",
        )

        return CreateRobokassaResponseSchema(
            payment_url=payment_url,
            invoice_id=invoice_id,
        )


@payment_router.post(
    "/result",
    response_class=PlainTextResponse,
    summary="Handle Robokassa ResultURL callback",
    description=(
        "Endpoint for Robokassa to notify about successful payments. "
        "Verifies signature and upgrades user plan."
    ),
    responses={
        200: {
            "description": "Payment processed successfully - returns OK{InvId}"
        },
        400: {"description": "Bad signature"},
        404: {"description": "Payment not found"},
    },
)
async def payment_result(
    request: Request,
    db: DatabaseSessionManager = Depends(get_db),
    robokassa: RobokassaService = Depends(get_robokassa),
) -> PlainTextResponse:
    """
    Handle Robokassa ResultURL callback.

    **Workflow:**
    1. Extract form data from Robokassa
    2. Verify signature
    3. Mark payment as paid
    4. Get plan from payment.plan_id (stored during creation)
    5. Upgrade user's plan

    Args:
        request: FastAPI request with form data.
        db: Database session manager dependency.
        robokassa: Robokassa service dependency.

    Returns:
        PlainTextResponse: "OK{InvId}" on success, or error message.

    Note:
        This endpoint receives form-data from Robokassa, not JSON.
        The response must be plain text "OK{InvId}" for success.

    Example:
        POST /api/payments/result
        Form data: OutSum=990.00&InvId=INV_123_123&SignatureValue=abc123
        Response: OKINV_123_123
    """
    form = await request.form()
    out_sum = str(form.get("OutSum", ""))
    inv_id = str(form.get("InvId", ""))
    signature = str(form.get("SignatureValue", ""))

    # Verify signature
    if not robokassa.verify_result(out_sum, inv_id, signature):
        return PlainTextResponse("Bad signature", status_code=400)

    async with db.session() as session:
        # Mark payment as paid
        payment = await PaymentDAO.mark_paid(inv_id, session)
        if not payment:
            return PlainTextResponse("Payment not found", status_code=404)

        # Get the plan from payment (stored during creation)
        # Payment model has plan relationship with lazy="joined"
        payment_with_plan = await PaymentDAO.get_by_invoice(inv_id, session)
        if not payment_with_plan:
            return PlainTextResponse(
                "Payment details not found", status_code=404
            )

        # Get user to upgrade
        user = await TGUserDAO.get(session, payment.tg_user_id)
        if not user:
            return PlainTextResponse("User not found", status_code=404)

        # Upgrade user's plan using plan_id from payment
        await TGUserDAO.upgrade_plan(
            user.telegram_id, payment_with_plan.plan_id, session
        )
        await session.commit()

    return PlainTextResponse(f"OK{inv_id}")

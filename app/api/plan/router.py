from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db
from app.db.dao import PlanDAO
from app.services import DatabaseSessionManager

from .schemas import (
    CreatePlanRequestSchema,
    ListPlanSchema,
    PlanResponseSchema,
    UpdatePlanRequestSchema,
)

plan_router = APIRouter(prefix="/plans", tags=["Plans"])


@plan_router.get(
    "",
    response_model=ListPlanSchema,
    status_code=status.HTTP_200_OK,
    summary="List all active plans",
    description="Retrieve a list of all active subscription plans available for purchase.",
    responses={
        200: {"description": "Plans retrieved successfully"},
        500: {"description": "Internal Server Error"},
    },
)
async def list_plans(
    db: DatabaseSessionManager = Depends(get_db),
) -> ListPlanSchema:
    """
    Retrieves all active subscription plans.

    Args:
        db: Database session manager dependency.

    Returns:
        ListPlanSchema: List of active plans with total count.

    Example:
        GET /api/plans
        Response: {
            "total": 3,
            "plans": [
                {"id": 1, "name": "Test", "price": 0, "price_rub": 0.0, ...},
                {"id": 2, "name": "Base", "price": 99000, "price_rub": 990.0, ...}
            ]
        }
    """
    async with db.session() as session:
        plans = await PlanDAO.get_all_active(session)

    plan_responses = [
        PlanResponseSchema.model_validate(plan) for plan in plans
    ]
    return ListPlanSchema(total=len(plans), plans=plan_responses)


@plan_router.post(
    "",
    response_model=PlanResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new plan",
    description="Create a new subscription plan with specified parameters.",
    responses={
        201: {"description": "Plan created successfully"},
        400: {"description": "Plan with this name already exists"},
        500: {"description": "Internal Server Error"},
    },
)
async def create_plan(
    data: CreatePlanRequestSchema,
    db: DatabaseSessionManager = Depends(get_db),
) -> PlanResponseSchema:
    """
    Create a new subscription plan.

    Args:
        data: Plan creation data with name, price, limits.
        db: Database session manager dependency.

    Returns:
        PlanResponseSchema: Created plan with all details.

    Raises:
        HTTPException: 400 if plan with this name already exists.

    Example:
        POST /api/plans
        Body: {
            "name": "Base",
            "price": 99000,
            "monthly_analyses": 100,
            "max_reels_per_request": 10,
            "is_active": true
        }
        Response: {
            "id": 2,
            "name": "Base",
            "price": 99000,
            "price_rub": 990.0,
            "monthly_analyses": 100,
            "max_reels_per_request": 10,
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    """
    async with db.session() as session:
        # Check if plan with this name already exists
        existing = await PlanDAO.get_by_active_type(data.name, session)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan '{data.name}' already exists",
            )

        # Create new plan
        plan = await PlanDAO.add(
            session,
            name=data.name,
            price=data.price,
            monthly_analyses=data.monthly_analyses,
            max_reels_per_request=data.max_reels_per_request,
            is_active=data.is_active,
        )

    return PlanResponseSchema.model_validate(plan)


@plan_router.patch(
    "/{plan_id}",
    response_model=PlanResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a plan",
    description="Update specific fields of an existing plan. Only provided fields will be updated.",
    responses={
        200: {"description": "Plan updated successfully"},
        404: {"description": "Plan not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def update_plan(
    plan_id: int,
    data: UpdatePlanRequestSchema,
    db: DatabaseSessionManager = Depends(get_db),
) -> PlanResponseSchema:
    """
    Update an existing subscription plan.

    Only provided fields will be updated. Omitted fields remain unchanged.

    Args:
        plan_id (int): The ID of the plan to update.
        data: Plan update data (all fields optional).
        db: Database session manager dependency.

    Returns:
        PlanResponseSchema: Updated plan with all details.

    Raises:
        HTTPException: 404 if plan not found.

    Example:
        PATCH /api/plans/2
        Body: {
            "price": 149000,
            "monthly_analyses": 150
        }
        Response: {
            "id": 2,
            "name": "Base",
            "price": 149000,
            "price_rub": 1490.0,
            "monthly_analyses": 150,
            "max_reels_per_request": 10,
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z"
        }
    """
    async with db.session() as session:
        # Get existing plan
        plan = await PlanDAO.get(session, plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan with id {plan_id} not found",
            )

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)

        await session.commit()
        await session.refresh(plan)

    return PlanResponseSchema.model_validate(plan)

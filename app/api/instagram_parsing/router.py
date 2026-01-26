from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.db.dao import InstagramAccountDAO
from app.models import InstagramAuth
from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
    ProxyManager,
)

from ..deps import get_browser, get_db, get_orchestrator, get_proxy_manager
from .schemas import ParseReelsSchema

parsing_router = APIRouter(prefix="/instagram", tags=["Instagram"])


@parsing_router.post(
    "/parse/xlsx",
    status_code=status.HTTP_200_OK,
    summary="Parse Instagram Reels to XLSX",
    description=(
        "Parse Reels from a target Instagram profile and return an XLSX file. "
        "Uses stored account credentials to authenticate and fetch data."
    ),
    response_model=StreamingResponse,
    responses={
        200: {
            "description": "XLSX file with parsed reels",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        404: {
            "description": "No valid accounts available",
        },
        500: {"description": "Internal Server Error"},
    },
)
async def parse_reels_xlsx(
    data: ParseReelsSchema,
    browser: BrowserManager = Depends(get_browser),
    db: DatabaseSessionManager = Depends(get_db),
    orchestrator: InstagramOrchestrator = Depends(get_orchestrator),
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
):
    """
    Parse Instagram Reels and return XLSX file.

    **Workflow:**
    1. Retrieve account from database
    2. Extract fresh credentials (doc_id, variables, headers)
    3. Fetch all reels with pagination
    4. Generate XLSX file with results

    **XLSX Columns:**
    - url: Direct link to the reel
    - views: Number of views
    - likes: Number of likes
    - comments: Number of comments
    - er: Engagement Rate (calculated as (likes + comments) / views)

    Args:
        data: Parsing parameters

    Returns:
        StreamingResponse: XLSX file as download.

    Raises:
        HTTPException 500: For unexpected errors.
    """
    import io

    import pandas as pd
    from fastapi.responses import StreamingResponse

    async with db.session() as session:
        account = await InstagramAccountDAO.get_least_used(session)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid Instagram accounts available. Please add an account first.",
            )

        auth = InstagramAuth(
            login=account.login,
            password=account.password,
            cookies=account.cookies,
        )

        proxy_formatted = None
        proxy = await proxy_manager.get_least_used()
        if proxy:
            proxy_formatted = proxy.to_playwright_proxy()

        try:
            async with browser.context(proxy=proxy_formatted) as (page, ctx):
                credentials = await orchestrator.login_and_extract_credentials(
                    page, ctx, auth, data.target_username
                )
        except Exception as exc:
            async with db.session() as session:
                await InstagramAccountDAO.update_by_login(
                    session, auth.login, valid=False
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to use account '{account.login}'. Account has been invalidated: {exc}.",
            )

    credentials = {
        "cookies": account.cookies,
    }

    reels = await orchestrator.parse_profile_reels(
        credentials=credentials,
        target_username=data.target_username,
        max_reels=data.max_reels,
    )

    df = pd.DataFrame(reels)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reels")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={data.target_username}_reels.xlsx"
        },
    )

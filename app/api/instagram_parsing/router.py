from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.db.dao import InstagramAccountDAO
from app.exceptions import (
    AuthUnexpectedError,
    UserNotFoundError,
    UserPrivateError,
)
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
    response_model=None,
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
    - Link: Direct link to the reel
    - Views: Number of views
    - Likes: Number of likes
    - Comments: Number of comments
    - Virality: Engagement Rate (calculated as (likes + comments) / views)

    Args:
        data: Parsing parameters

    Returns:
        StreamingResponse: XLSX file as download.

    Raises:
        HTTPException 500: For unexpected errors.
    """
    import io

    import pandas as pd

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
            reels, credentials = await orchestrator.full_workflow(
                page, ctx, auth, data.target_username, data.max_reels
            )
    except AuthUnexpectedError as exc:
        async with db.session() as session:
            await InstagramAccountDAO.update_by_login(
                session, auth.login, valid=False
            )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use account '{account.login}' with unexpected error, account has been invalidated: {exc}.",
        )
    except UserPrivateError:
        raise HTTPException(status_code=403, detail="This account private")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as exc:
        async with db.session() as session:
            await InstagramAccountDAO.update_by_login(
                session, auth.login, valid=False
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use account '{account.login}'. Account has been invalidated: {exc}.",
        )

    # Update cookies and last_used_at in DB
    async with db.session() as session:
        await InstagramAccountDAO.update_by_login(
            session,
            auth.login,
            cookies=credentials.get("cookies"),
            last_used_at=datetime.now(),
        )

    required_keys = ["url", "views", "likes", "comments", "virality"]
    reels = [
        r
        for r in reels
        if isinstance(r, dict) and all(k in r for k in required_keys)
    ]

    if not reels:
        raise HTTPException(500, "Failed to get reels")

    df = pd.DataFrame(reels)
    df = df[required_keys].rename(
        columns={
            "url": "Ссылка",
            "views": "Просмотры",
            "likes": "Лайки",
            "comments": "Комменты",
            "virality": "Вирусность",
        }
    )
    df["Просмотры"] = df["Просмотры"].astype(int)
    df["Лайки"] = df["Лайки"].astype(int)
    df["Комменты"] = df["Комменты"].astype(int)
    df["Вирусность"] = df["Вирусность"].astype(float)

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

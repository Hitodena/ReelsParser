"""Proxy API router for managing proxy servers."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.proxy import ProxyModel
from app.services.proxy_manager import ProxyManager

from ..deps import get_proxy_manager
from .schemas import (
    ProxyAddResponseSchema,
    ProxyAddSchema,
    ProxyBlockResponseSchema,
    ProxyDeleteResponseSchema,
    ProxyListSchema,
    ProxyResponseSchema,
    ProxyUnblockResponseSchema,
)

proxy_router = APIRouter(prefix="/proxies", tags=["Proxies"])


@proxy_router.post(
    "/",
    summary="Add a new proxy to the pool",
    response_model=ProxyAddResponseSchema,
    responses={
        200: {"description": "Proxy added successfully"},
        400: {"description": "Bad Request - Invalid proxy data"},
        500: {"description": "Internal Server Error - Failed to add proxy"},
    },
    status_code=status.HTTP_200_OK,
)
async def add_proxy(
    data: ProxyAddSchema,
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ProxyAddResponseSchema:
    """
    Add a new proxy to the proxy pool.

    Args:
        data: The proxy data including host, port, username, password, and protocol.
        proxy_manager: The proxy manager service instance.

    Returns:
        ProxyAddResponseSchema: Response containing the status and proxy ID.

    Raises:
        HTTPException: 500 if failed to add proxy.

    Example:
        POST /api/proxies/
        Body: {
            "host": "192.168.1.1",
            "port": 8080,
            "username": "user",
            "password": "pass",
            "protocol": "http"
        }
        Response: {
            "status": "success",
            "proxy_id": "abc123"
        }
    """
    try:
        proxy = ProxyModel(
            host=data.host,
            port=data.port,
            username=data.username,
            password=data.password,
            protocol=data.protocol,
        )

        proxy_id = await proxy_manager.add_proxy(proxy)

        return ProxyAddResponseSchema(status="success", proxy_id=proxy_id)
    except Exception as exc:
        raise HTTPException(500, f"Failed to add proxy: {exc}")


@proxy_router.get(
    "/",
    summary="Retrieve a list of all proxies",
    response_model=ProxyListSchema,
    responses={
        200: {"description": "Proxies retrieved successfully"},
        404: {"description": "There are no proxies in pool"},
        500: {
            "description": "Internal Server Error - Failed to retrieve proxies"
        },
    },
    status_code=status.HTTP_200_OK,
)
async def list_proxies(
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ProxyListSchema:
    """
    Retrieve a list of all proxies in the pool.

    Returns proxy information including blocked status.
    Blocked proxies are temporarily excluded from rotation.

    Args:
        proxy_manager: The proxy manager service instance.

    Returns:
        ProxyListSchema: Response containing the total count and list of proxies.

    Raises:
        HTTPException: 404 if no proxies exist.

    Example:
        GET /api/proxies/
        Response: {
            "total": 2,
            "proxies": [
                {
                    "host": "192.168.1.1",
                    "port": 8080,
                    "is_blocked": false
                },
                {
                    "host": "10.0.0.1",
                    "port": 3128,
                    "is_blocked": true
                }
            ]
        }
    """
    proxies_with_status = await proxy_manager.get_all_with_status()
    proxy_list = [
        ProxyResponseSchema(
            host=item["proxy"].host,
            port=item["proxy"].port,
            is_blocked=item["is_blocked"],
        )
        for item in proxies_with_status
    ]
    if not proxy_list:
        raise HTTPException(404, "Proxies not found")
    return ProxyListSchema(total=len(proxies_with_status), proxies=proxy_list)


@proxy_router.delete(
    "/{proxy_id}",
    summary="Delete a specific proxy",
    response_model=ProxyDeleteResponseSchema,
    responses={
        200: {"description": "Proxy deleted successfully"},
        404: {"description": "Not Found - Proxy not found"},
        500: {"description": "Internal Server Error - Failed to delete proxy"},
    },
    status_code=status.HTTP_200_OK,
)
async def delete_proxy(
    proxy_id: str,
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ProxyDeleteResponseSchema:
    """
    Delete a specific proxy from the pool.

    Args:
        proxy_id: The unique identifier of the proxy to delete.
        proxy_manager: The proxy manager service instance.

    Returns:
        ProxyDeleteResponseSchema: Response containing the status of the deletion.

    Raises:
        HTTPException: 404 if proxy not found.

    Example:
        DELETE /api/proxies/abc123
        Response: {"status": "success"}
    """
    try:
        await proxy_manager.delete_proxy(proxy_id)
        return ProxyDeleteResponseSchema(status="success")
    except Exception as exc:
        raise HTTPException(404, f"Proxy not found: {exc}")


@proxy_router.post(
    "/{proxy_id}/unblock",
    summary="Manually unblock a specific proxy",
    response_model=ProxyUnblockResponseSchema,
    responses={
        200: {"description": "Proxy unblocked successfully"},
        404: {"description": "Not Found - Proxy not found"},
        500: {
            "description": "Internal Server Error - Failed to unblock proxy"
        },
    },
    status_code=status.HTTP_200_OK,
)
async def unblock_proxy(
    proxy_id: str,
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ProxyUnblockResponseSchema:
    """
    Manually unblock a specific proxy.

    Args:
        proxy_id: The unique identifier of the proxy to unblock.
        proxy_manager: The proxy manager service instance.

    Returns:
        ProxyUnblockResponseSchema: Response containing the status of the unblock operation.

    Raises:
        HTTPException: 404 if proxy not found.

    Example:
        POST /api/proxies/abc123/unblock
        Response: {"status": "success"}
    """
    try:
        await proxy_manager.unblock_proxy(proxy_id)
        return ProxyUnblockResponseSchema(status="success")
    except Exception as exc:
        raise HTTPException(404, f"Proxy not found: {exc}")


@proxy_router.post(
    "/{proxy_id}/block",
    summary="Manually block a specific proxy",
    response_model=ProxyBlockResponseSchema,
    responses={
        200: {"description": "Proxy blocked successfully"},
        404: {"description": "Not Found - Proxy not found"},
        500: {"description": "Internal Server Error - Failed to block proxy"},
    },
    status_code=status.HTTP_200_OK,
)
async def block_proxy(
    proxy_id: str,
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ProxyBlockResponseSchema:
    """
    Manually block a specific proxy.

    Args:
        proxy_id: The unique identifier of the proxy to block.
        proxy_manager: The proxy manager service instance.

    Returns:
        ProxyBlockResponseSchema: Response containing the status of the block operation.

    Raises:
        HTTPException: 404 if proxy not found.

    Example:
        POST /api/proxies/abc123/block
        Response: {"status": "success"}
    """
    try:
        await proxy_manager.block_proxy(proxy_id)
        return ProxyBlockResponseSchema(status="success")
    except Exception as exc:
        raise HTTPException(404, f"Proxy not found: {exc}")

"""
Clients router: manage tenant clients.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import TokenData, get_current_user
from app.repositories.repositories import ClientRepository
from app.schemas.schemas import ClientResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=ClientResponse,
    summary="Get current client (tenant) details",
)
async def get_my_client(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the client record for the authenticated user's tenant."""
    client_repo = ClientRepository(db)
    client = await client_repo.get_by_id(current_user.client_id)
    if not client:
        raise NotFoundError("Client", current_user.client_id)
    return client

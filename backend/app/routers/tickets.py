from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.ticket import TicketResponse
from app.services.database.repositories import ticket_repo

router = APIRouter(prefix="/api/v1/tickets", tags=["Support Tickets"])


@router.get("", response_model=List[TicketResponse])
async def list_tickets():
    """List all created support tickets."""
    tickets = await ticket_repo.find_all(limit=100)
    return [TicketResponse.model_validate(t.model_dump(mode="json")) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    """Retrieve support ticket details by ID."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return TicketResponse.model_validate(ticket.model_dump(mode="json"))

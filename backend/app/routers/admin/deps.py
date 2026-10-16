"""Dependencies shared by the staff routers."""

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import StaffUser
from app.core.state import ClientIpDep
from app.domain.staff import Actor


def get_actor(user: StaffUser, ip: ClientIpDep) -> Actor:
    """Return the acting staff member."""
    return Actor(user=user, ip=ip)


ActorDep = Annotated[Actor, Depends(get_actor)]

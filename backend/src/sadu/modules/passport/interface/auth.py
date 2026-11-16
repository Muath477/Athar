from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from sadu.modules.passport import api as passport
from sadu.shared.errors import Unauthorized
from sadu.shared.web import Session

PASSPORT_HEADER = "X-Passport-Token"


async def optional_passport(
    session: Session, token: Annotated[str | None, Header(alias=PASSPORT_HEADER, max_length=128)] = None
) -> UUID | None:
    return await passport.resolve(session, token) if token else None


async def required_passport(passport_id: Annotated[UUID | None, Depends(optional_passport)]) -> UUID:
    if passport_id is None:
        raise Unauthorized("invalid_passport")
    return passport_id


OptionalPassport = Annotated[UUID | None, Depends(optional_passport)]
RequiredPassport = Annotated[UUID, Depends(required_passport)]

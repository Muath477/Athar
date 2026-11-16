from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sadu.modules.passport import api as passport
from sadu.modules.passport.interface.auth import RequiredPassport
from sadu.modules.sites import api as sites
from sadu.shared.web import Session, limit_per_ip, public

router = APIRouter(tags=["passport"])


class NewPassport(BaseModel):
    passport_id: str
    token: str


class Stamp(BaseModel):
    site_id: str
    site_name_ar: str
    site_name_en: str
    stamped_at: datetime


class PassportOut(BaseModel):
    passport_id: str
    created_at: datetime
    stamps: list[Stamp]


@router.post(
    "/passports", status_code=201, dependencies=[Depends(public), Depends(limit_per_ip("passport", 10, 3600))]
)
async def create_passport(session: Session) -> NewPassport:
    passport_id, token = await passport.create(session)
    return NewPassport(passport_id=str(passport_id), token=token)


@router.get("/passport")
async def get_passport(passport_id: RequiredPassport, session: Session) -> PassportOut:
    summary = await passport.summary(session, passport_id)
    stamps = []
    for entry in summary.entries:
        site = await sites.get_site(session, entry.site_id)
        stamps.append(
            Stamp(
                site_id=str(site.id),
                site_name_ar=site.name_ar,
                site_name_en=site.name_en,
                stamped_at=entry.stamped_at,
            )
        )
    return PassportOut(passport_id=str(summary.id), created_at=summary.created_at, stamps=stamps)

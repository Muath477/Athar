from sadu.modules.admin.infrastructure import orm as admin_orm
from sadu.modules.capture.infrastructure import orm as capture_orm
from sadu.modules.inspection.infrastructure import orm as inspection_orm
from sadu.modules.missions.infrastructure import orm as missions_orm
from sadu.modules.passport.infrastructure import orm as passport_orm
from sadu.modules.sites.infrastructure import orm as sites_orm
from sadu.modules.stories.infrastructure import orm as stories_orm
from sadu.modules.verification.infrastructure import orm as verification_orm
from sadu.shared.db import Base

ALL_ORM_MODULES = (
    admin_orm,
    capture_orm,
    inspection_orm,
    missions_orm,
    passport_orm,
    sites_orm,
    stories_orm,
    verification_orm,
)
metadata = Base.metadata

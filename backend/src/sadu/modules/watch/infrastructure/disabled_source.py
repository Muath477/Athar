from datetime import date

from sadu.modules.watch.application.ports import SceneSourceUnavailable, WatchArea
from sadu.modules.watch.domain.scene import Scene


class DisabledSceneSource:
    @property
    def name(self) -> str:
        return "none"

    @property
    def is_sample(self) -> bool:
        return False

    async def scenes(self, area: WatchArea, start: date, end: date, limit: int) -> list[Scene]:
        raise SceneSourceUnavailable("Satellite screening is turned off")

from sadu.modules.mapping.application.ports import DetectionInput, DetectionOutput


class ManualOnly:
    @property
    def name(self) -> str:
        return "manual"

    async def detect(self, request: DetectionInput) -> DetectionOutput:
        return DetectionOutput(cells=())

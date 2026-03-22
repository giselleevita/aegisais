from app.modules.itdae.models import ItdaePosition
from app.modules.itdae.schemas import ItdaePositionSchema


def itdae_position_to_schema(row: ItdaePosition) -> ItdaePositionSchema:
    return ItdaePositionSchema.model_validate(row, from_attributes=True)

from app.modules.vessels.models import VesselLatest, VesselPosition
from app.modules.vessels.schemas import VesselLatestOut, VesselPositionOut


def vessel_latest_to_out(row: VesselLatest) -> VesselLatestOut:
    return VesselLatestOut.model_validate(row, from_attributes=True)


def vessel_position_to_out(row: VesselPosition) -> VesselPositionOut:
    return VesselPositionOut.model_validate(row, from_attributes=True)

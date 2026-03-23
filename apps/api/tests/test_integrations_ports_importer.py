from app.core.database import Base
from app.modules.integrations.importers_ports import (
    ingest_port_datasets,
    parse_unlocode_csv,
    parse_wpi_csv,
)
from app.modules.integrations.models import PortReference, UnlocodeReference
from tests.conftest import TestingSessionLocal, _engine


def test_parse_wpi_csv_maps_to_postgis_friendly_rows(tmp_path):
    p = tmp_path / "wpi.csv"
    p.write_text(
        "world_port_index_number,port_name,country_code,latitude,longitude,harbor_size\n"
        "101,Port Alpha,GB,51.5,-0.1,Large\n",
        encoding="utf-8",
    )
    rows = parse_wpi_csv(str(p))
    assert len(rows) == 1
    row = rows[0]
    assert row.source == "world_port_index"
    assert row.geom_wkt == "POINT(-0.1 51.5)"
    assert row.license_tag == "restricted_non_commercial"


def test_parse_unlocode_csv_maps_to_postgis_friendly_rows(tmp_path):
    p = tmp_path / "locode.csv"
    p.write_text(
        "locode,name,country_code,latitude,longitude,function\n"
        "GBLON,London,GB,51.5074,-0.1278,1-5-\n",
        encoding="utf-8",
    )
    rows = parse_unlocode_csv(str(p))
    assert len(rows) == 1
    row = rows[0]
    assert row.unlocode == "GBLON"
    assert row.geom_wkt == "POINT(-0.1278 51.5074)"


def test_ingest_port_datasets_writes_reference_tables(tmp_path):
    Base.metadata.create_all(bind=_engine)
    try:
        wpi = tmp_path / "wpi.csv"
        loc = tmp_path / "locode.csv"
        wpi.write_text(
            "world_port_index_number,port_name,country_code,latitude,longitude\n"
            "101,Port Alpha,GB,51.5,-0.1\n",
            encoding="utf-8",
        )
        loc.write_text(
            "locode,name,country_code,latitude,longitude\n"
            "GBLON,London,GB,51.5074,-0.1278\n",
            encoding="utf-8",
        )
        db = TestingSessionLocal()
        try:
            result = ingest_port_datasets(
                db,
                world_port_index_rows=parse_wpi_csv(str(wpi)),
                unlocode_rows=parse_unlocode_csv(str(loc)),
            )
            assert result == {"ports_written": 1, "locodes_written": 1}
            assert db.query(PortReference).count() == 1
            assert db.query(UnlocodeReference).count() == 1
        finally:
            db.close()
    finally:
        Base.metadata.drop_all(bind=_engine)


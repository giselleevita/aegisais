from app.modules.integrations.importers_ports import PortSeedRow
from app.modules.integrations.migration_validator import validate_port_seed_rows


def test_validate_port_seed_rows_counts_duplicates_and_missing_fields():
    rows = [
        PortSeedRow(
            source="world_port_index",
            source_id="101",
            name="Port Alpha",
            country_code="GB",
            unlocode="GBALP",
            latitude=51.5,
            longitude=-0.1,
            geom_wkt="POINT(-0.1 51.5)",
            metadata_json={},
            license_tag="restricted_non_commercial",
        ),
        PortSeedRow(
            source="world_port_index",
            source_id="101",
            name=" ",
            country_code="GB",
            unlocode=None,
            latitude=51.6,
            longitude=-0.2,
            geom_wkt="",
            metadata_json={},
            license_tag="restricted_non_commercial",
        ),
    ]

    report = validate_port_seed_rows(rows)

    assert report.total_rows == 2
    assert report.duplicate_source_keys == 1
    assert report.missing_names == 1
    assert report.missing_geometry == 1
    assert report.valid_rows == 0
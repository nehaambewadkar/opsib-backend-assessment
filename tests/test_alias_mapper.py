
import pytest

from app.mapping.alias_mapper import (
    build_alias_map,
    build_product_alias_map,
)


def test_build_location_alias_map():
    rows = [
        {
            "source_system": "ERP",
            "external_location_id": "MUM-014",
            "canonical_location_id": "STORE-014",
        },
        {
            "source_system": "WMS",
            "external_location_id": "WH-MH-014",
            "canonical_location_id": "STORE-014",
        },
    ]

    aliases = build_alias_map(
        rows,
        "external_location_id",
        "canonical_location_id",
    )

    assert aliases["MUM-014"] == "STORE-014"
    assert aliases["WH-MH-014"] == "STORE-014"


def test_conflicting_location_alias_is_rejected():
    rows = [
        {
            "external_location_id": "MUM-014",
            "canonical_location_id": "STORE-014",
        },
        {
            "external_location_id": "MUM-014",
            "canonical_location_id": "STORE-015",
        },
    ]

    with pytest.raises(ValueError, match="Conflicting alias"):
        build_alias_map(
            rows,
            "external_location_id",
            "canonical_location_id",
        )


def test_product_alias_preserves_conversion_factor():
    rows = [
        {
            "source_system": "ERP",
            "external_item_id": "ERP-BOX-12",
            "canonical_product_id": "SKU-002",
            "source_uom": "BOX",
            "base_uom": "EA",
            "to_base_factor": "12",
        }
    ]

    aliases = build_product_alias_map(rows)
    product = aliases[("ERP", "ERP-BOX-12")]

    assert product["canonical_product_id"] == "SKU-002"
    assert product["source_uom"] == "BOX"
    assert product["base_uom"] == "EA"
    assert float(product["to_base_factor"]) == 12


def test_conflicting_product_alias_is_rejected():
    rows = [
        {
            "source_system": "ERP",
            "external_item_id": "ERP-SKU-001",
            "canonical_product_id": "SKU-001",
            "source_uom": "EA",
            "base_uom": "EA",
            "to_base_factor": "1",
        },
        {
            "source_system": "ERP",
            "external_item_id": "ERP-SKU-001",
            "canonical_product_id": "SKU-999",
            "source_uom": "EA",
            "base_uom": "EA",
            "to_base_factor": "1",
        },
    ]

    with pytest.raises(ValueError, match="Conflicting product alias"):
        build_product_alias_map(rows)

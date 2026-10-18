
def build_alias_map(
    rows: list[dict[str, str]],
    source_id_column: str,
    canonical_id_column: str,
) -> dict[str, str]:
    """Map external IDs to canonical IDs and reject ambiguous mappings."""
    aliases: dict[str, str] = {}

    for row in rows:
        source_id = row[source_id_column].strip()
        canonical_id = row[canonical_id_column].strip()

        if not source_id or not canonical_id:
            raise ValueError("Alias records must have non-empty IDs.")

        existing = aliases.get(source_id)

        if existing is not None and existing != canonical_id:
            raise ValueError(
                f"Conflicting alias for {source_id}: "
                f"{existing} vs {canonical_id}"
            )

        aliases[source_id] = canonical_id

    return aliases


def build_product_alias_map(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    """Map (source system, external item ID) to product and unit metadata."""
    aliases: dict[tuple[str, str], dict[str, str]] = {}

    for row in rows:
        key = (
            row["source_system"].strip(),
            row["external_item_id"].strip(),
        )

        factor = float(row["to_base_factor"])
        if factor <= 0:
            raise ValueError(f"Conversion factor must be positive: {key}")

        value = {
            "canonical_product_id": row["canonical_product_id"].strip(),
            "source_uom": row["source_uom"].strip(),
            "base_uom": row["base_uom"].strip(),
            "to_base_factor": str(factor),
        }

        if not all([key[0], key[1], value["canonical_product_id"],
                    value["source_uom"], value["base_uom"]]):
            raise ValueError("Product alias fields must not be empty.")

        existing = aliases.get(key)
        if existing is not None and existing != value:
            raise ValueError(f"Conflicting product alias: {key}")

        aliases[key] = value

    return aliases

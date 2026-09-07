"""Adapt declared property fields and explicit document mappings before scoring."""


def adapt_records(records, preset, paper_map=None):
    aliases = {
        preset.main_extraction_keyword.casefold(),
        *(name.casefold() for name in preset.property_aliases),
    }
    output = []
    for item in records:
        record = dict(item)
        legacy = any(key in record for key in preset.legacy_fields)
        property_name = record.get("property", record.get("property_name"))
        if (
            legacy
            and property_name is not None
            and str(property_name).strip().casefold() not in aliases
        ):
            raise ValueError("Legacy fields conflict with the selected property preset")
        for old, new in preset.legacy_fields.items():
            if old in record:
                value = record.pop(old)
                if new in record and str(record[new]).strip() != str(value).strip():
                    raise ValueError(f"Conflicting {old} and {new} fields")
                record[new] = value
        if legacy or (
            property_name is not None
            and str(property_name).strip().casefold() in aliases
        ):
            record["property"] = preset.main_extraction_keyword
        if paper_map and not record.get("document_id"):
            paper = str(record.get("paper_id", ""))
            if paper not in paper_map:
                raise ValueError(
                    f"paper_id {paper} is absent from the supplied paper map"
                )
            record["document_id"] = paper_map[paper]
        output.append(record)
    return output

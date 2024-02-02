from wikidata_bot_framework import resolve_multiple_property_claims


def test_resolve_multiple_property_claims_simple():
    prop = "P268"
    value = "123747698"
    data = resolve_multiple_property_claims({prop: {value}})
    assert len(data) == 1
    assert (prop, value) in data
    assert len(data[(prop, value)]) == 1
    assert list(data[(prop, value)])[0] == "http://www.wikidata.org/entity/Q1"


def test_resolve_multiple_property_claims_multiple_values():
    prop = "P268"
    values = ["123747698", "15250572g"]
    expected_entity_ids = ["Q1", "Q6980"]
    data = resolve_multiple_property_claims({prop: set(values)})
    assert len(data) == 2
    for value, expected_entity_id in zip(values, expected_entity_ids):
        assert (prop, value) in data
        assert len(data[(prop, value)]) == 1
        assert (
            list(data[(prop, value)])[0]
            == f"http://www.wikidata.org/entity/{expected_entity_id}"
        )

import pytest
from wikidata_bot_framework.utils import get_entity_id_from_entity_url


def test_item():
    assert get_entity_id_from_entity_url("http://www.wikidata.org/entity/Q1") == "Q1"


def test_property():
    assert get_entity_id_from_entity_url("http://www.wikidata.org/entity/P31") == "P31"


def test_lexeme():
    assert get_entity_id_from_entity_url("http://www.wikidata.org/entity/L1") == "L1"


def test_invalid_url():
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/Q")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/P")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/L")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/Q1/")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/P31/")
    with pytest.raises(AssertionError):
        get_entity_id_from_entity_url("http://www.wikidata.org/entity/L1/")

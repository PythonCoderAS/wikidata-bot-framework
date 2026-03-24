from wikidata_bot_framework import ExtraProperty, ExtraQualifier


def test_property_same_claim():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    assert prop1 == prop2
    assert prop1.same_claim(prop2)


def test_property_same_claim_different_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert prop1 != prop2
    assert prop1.same_claim(prop2)


def test_property_different_claims():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "4")
    assert prop1 != prop2
    assert not prop1.same_claim(prop2)


def test_property_different_claim_and_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "4")
    prop1.add_qualifier_with_property_id_and_value("P433", "1")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert prop1 != prop2
    assert not prop1.same_claim(prop2)


def test_qualifier_same_claim():
    qual1 = ExtraQualifier.from_property_id_and_value("P304", "5")
    qual2 = ExtraQualifier.from_property_id_and_value("P304", "5")
    assert qual1 == qual2
    assert qual1.same_claim(qual2)


def test_qualifier_different_claims():
    qual1 = ExtraQualifier.from_property_id_and_value("P304", "5")
    qual2 = ExtraQualifier.from_property_id_and_value("P304", "4")
    assert qual1 != qual2
    assert not qual1.same_claim(qual2)


def test_property_no_conflicts():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    assert not prop1.conflicts_with(prop2)


def test_property_conflicts_different_values():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "4")
    assert prop1.conflicts_with(prop2)


def test_property_no_conflicts_with_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert not prop1.conflicts_with(prop2)


def test_property_conflicts_with_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop1.add_qualifier_with_property_id_and_value("P433", "1")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert prop1.conflicts_with(prop2)


def test_property_no_conflicts_different_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop1.add_qualifier_with_property_id_and_value("P478", "1")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert not prop1.conflicts_with(prop2)


def test_property_conflicts_different_qualifiers():
    prop1 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop2 = ExtraProperty.from_property_id_and_value("P304", "5")
    prop1.add_qualifier_with_property_id_and_value("P478", "1")
    prop1.add_qualifier_with_property_id_and_value("P433", "2")
    prop2.add_qualifier_with_property_id_and_value("P433", "12")
    assert prop1.conflicts_with(prop2)

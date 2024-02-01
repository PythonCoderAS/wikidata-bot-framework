Quickstart
==========

.. code-block:: python

    from wikidata_bot_framework import PropertyAdderBot, ExtraProperty, ExtraQualifier, ExtraReference, OutputHelper, site
    from pywikibot import Claim

    class MyBot(PropertyAdderBot):
        def get_edit_summary(self, page):
            return "Doing some stuff..."

        def run_item(self, page):
            helper = OutputHelper()
            helper.add_property_from_property_id_and_value("P31", "Q5") # instance of human
            extra_prop = ExtraProperty.from_property_id_and_value("P106", "Q82955") # occupation: politican
            extra_qual = ExtraQualifier.from_property_id_and_value("P580", "2020-01-01T00:00:00Z") # qualifier: start time: 2020-01-01
            extra_ref = ExtraReference()
            claim = Claim(site, "P854")
            claim.setTarget("https://www.example.com")
            extra_ref.add_claim(claim, True) # reference: stated in: https://www.example.com
            extra_prop.add_qualifier(extra_qual)
            extra_prop.add_reference(extra_ref)
            helper.add_property(extra_prop)
            return helper

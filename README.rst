wikidata-bot-framework
======================

.. image:: https://img.shields.io/pypi/v/wikidata-bot-framework
   :alt: PyPI - Version
   :target: https://pypi.org/project/wikidata-bot-framework/

.. image:: https://img.shields.io/pypi/pyversions/wikidata-bot-framework
   :alt: PyPI - Python Version
   :target: https://pypi.org/project/wikidata-bot-framework/

.. image:: https://img.shields.io/pypi/dm/wikidata-bot-framework
   :alt: PyPI - Downloads
   :target: https://pypi.org/project/wikidata-bot-framework/

.. image:: https://img.shields.io/github/commit-activity/m/PythonCoderAS/wikidata-bot-framework
   :alt: GitHub commit activity
   :target: https://github.com/PythonCoderAS/wikidata-bot-framework

.. image:: https://img.shields.io/github/issues/PythonCoderAS/wikidata-bot-framework
   :alt: GitHub issues
   :target: https://github.com/PythonCoderAS/wikidata-bot-framework

.. image:: https://github.com/PythonCoderAS/wikidata-bot-framework/actions/workflows/test.yml/badge.svg
   :alt: GitHub Actions test status
   :target: https://github.com/PythonCoderAS/wikidata-bot-framework/actions/workflows/test.yml

.. image:: https://coveralls.io/repos/github/PythonCoderAS/wikidata-bot-framework/badge.svg?branch=master
   :alt: Coverage Status
   :target: https://coveralls.io/github/PythonCoderAS/wikidata-bot-framework?branch=master

.. image:: https://github.com/PythonCoderAS/wikidata-bot-framework/actions/workflows/type-lint.yml/badge.svg
   :alt: GitHub Actions type-lint status
   :target: https://github.com/PythonCoderAS/wikidata-bot-framework/actions/workflows/type-lint.yml

.. image:: https://img.shields.io/pypi/l/wikidata-bot-framework
   :alt: PyPI - License
   :target: https://pypi.org/project/wikidata-bot-framework/


A framework for creating bots that edit Wikidata.

The framework heavily simplifies the process of making a bot that uses another dataset to edit Wikidata.
It will automatically add claims, qualifiers, and references and intelligently make sure not to duplicate anything.
It also allows you to manually edit the item if you need to remove claims.
The framework also has many hooks that are called in various parts of the processing pipeline, for even more customizability.

Read full docs at https://pythoncoderas.github.io/wikidata-bot-framework/.

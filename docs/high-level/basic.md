# Basic Overview of the Wikidata Bot Framework

The root idea of the framework is that your job is to supply the properties,
qualifiers and references that you want to add to Wikidata, and the framework
will execute these edits while taking care of making sure not to introduce
duplicates.

The framework is intended that if you provide the same output twice, calling the
bot multiple times will not cause any item modification as long as there are no
outside edits.

The framework can be used on both user accounts and bot accounts, although it is
heavily recommended to use a bot account for any large-scale edits. The
framework is hard-coded for Wikidata as several of the values assume certain
items and properties available only on the Wikidata instance of Wikibase. In the
future, support may be added for custom Wikibase instances.

## Extendability

The framework has many options so that the processing can be customized to do
whatever you need. The framework offers many hooks so that you do not need to
copy-paste the processing code to make a small change. The framework also
supports hooks modifying the processing pipeline.

The framework also has a lot of configuration options so that most cases do not
require advanced code to use the hooks. The framework is designed to be easy to
use for simple cases, but also to be able to handle complex cases. For more
information on configuration, see the [configuration](configuration.md) page.

## Processing Pipeline

The framework will first add claims to the item. For each claim, it will add the
main claim, then the qualifiers, and finally the references. There are
situations where this will not always be true, such as a qualifier configuration
option requiring a new claim to be made.

You can read more about the processing pipeline on the
[processing pipeline](processing-pipeline.md) page.

## Error Handling

The framework has built-in Sentry support. If you provide a Sentry DSN, it will
automatically log both errors and transactions (successful processing of an
item) to Sentry.

You can read more about error handling on the
[error handling](error-handling.md) page.

## Utils

The framework has several utility functions in order to help with the most
common data fetching operations, such as interaction with the
[Wikidata Query Service](https://query.wikidata.org/).

You can read more about the utils on the [utils](utils.md) page.

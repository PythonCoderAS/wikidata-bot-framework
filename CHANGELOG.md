# CHANGELOG


## v10.0.0 (2026-03-24)

### Features

- Allow comparing claims and qualifiers on just the main claim
  ([`4908ce7`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/4908ce779db0c24cb0dde6a2d81eb4d31d3c039e))

- Allow returning multiple outputs and processing each
  ([`32b88b8`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/32b88b8d7565adb7a74cf5e1643c893b7b026950))

BREAKING CHANGE: The type signature for several methods have changed to also include
  `Sequence[Output]` as a valid possibility. To always get a sequence, use the line `output =
  self.ensure_output_sequence(output)`.

Methods that need to be updated:

- `post_output_process_hook` - `pre_edit_process_hook` - `post_edit_process_hook` - `process`

### Breaking Changes

- The type signature for several methods have changed to also include `Sequence[Output]` as a valid
  possibility. To always get a sequence, use the line `output =
  self.ensure_output_sequence(output)`.


## v9.1.0 (2026-03-24)

### Features

- Seperate the merging of output from the rest of processing
  ([`5c95284`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/5c952847d9cb950fd89effa59152fc1be961b22a))


## v9.0.0 (2026-03-20)

### Bug Fixes

- Improve type signature on get_sparql_query
  ([`bc194d1`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/bc194d138f88b7495c935e818480ac405b0834bb))

BREAKING CHANGE: property_val is now positional only.

### Breaking Changes

- Property_val is now positional only.


## v8.0.1 (2026-03-20)

### Bug Fixes

- Fix version detection if package isn't installed
  ([`cd11e2f`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/cd11e2f0f05c580d9d1c892640ff2e8d79fd584e))

- Fix version type
  ([`ed7bb51`](https://github.com/PythonCoderAS/wikidata-bot-framework/commit/ed7bb51b6df0f7888c5060b941c6d0f56c2b3368))


## v8.0.0 (2026-03-18)


## v7.3.0 (2024-01-25)


## v7.2.1 (2024-01-25)

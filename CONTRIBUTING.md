# Contributing to ewp-transcripts

Contributions to `ewp-transcripts` are welcome.

Before submitting a pull request, please read:

- [`LICENSING.md`](./LICENSING.md) for the licensing model and scope of the AGPL-3.0-only license; and
- [`CONTRIBUTOR_TERMS.md`](./CONTRIBUTOR_TERMS.md) for the terms that apply to submitted Contributions.

## Pull Requests

When submitting a pull request:

1. keep the change focused and explain its purpose;
2. add or update tests where appropriate;
3. update documentation when behavior or user-facing interfaces change;
4. identify any third-party code, data, text, models, or other material included in the contribution;
5. ensure that you have the right to submit all material contained in the pull request; and
6. affirmatively accept the Contributor Terms using the checkbox in the pull-request template.

A pull request should not be merged unless the Contributor Terms checkbox has been affirmatively selected by the contributor.

## Engineering Requirements

1. Every functional change must reference an FR/NFR requirement or add an ADR.
2. A CLI change requires an update to `docs/05-cli-specification.md` and a contract test.
3. A JSON contract change requires updates to the schema, examples, and `schema_version`.
4. An ML backend update requires a quality regression benchmark appropriate to its scope.
5. Secrets and private audio or benchmark material must never be committed.

Before submitting, confirm that:

- linting, static typing, and tests pass;
- documentation is updated;
- existing data is not overwritten;
- offline workflows do not gain undeclared network access;
- generated artifacts conform to their schemas;
- WER, timestamp, DER, semantic-translation, or other relevant quality impact has been
  evaluated when the change affects model behavior; and
- third-party material has compatible licensing, documented provenance, and preserved
  attribution or notices.

## Third-Party Material

Do not submit third-party code, data, media, text, model files, model weights, or other material unless its provenance and applicable license terms are clearly identified and are compatible with the Project.

If you are unsure whether third-party material may be included, describe its source and license in the pull request rather than assuming compatibility.

## Models and Model Weights

Do not add third-party machine-learning model weights to the repository unless their inclusion has been expressly discussed and approved.

Where possible, the Project should continue to obtain third-party models separately at the user's explicit request rather than redistributing them as part of `ewp-transcripts`.

## Contributor Terms

By submitting a Contribution through a pull request that references the Contributor Terms and affirmatively selecting the acceptance checkbox, you agree to the version of [`CONTRIBUTOR_TERMS.md`](./CONTRIBUTOR_TERMS.md) in effect for that submission.

Contributors retain copyright ownership of their Contributions while granting the rights described in the Contributor Terms.

## Review and Acceptance

Submission does not guarantee acceptance.

Maintainers may request changes, reject a pull request, or decline material whose provenance, licensing, security, maintainability, scope, or technical quality is unclear or unsuitable for the Project.

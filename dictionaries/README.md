# Project dictionaries

This catalog contains small, explicitly reviewed dictionaries whose source material may be
published in this repository. Dictionaries are never discovered or enabled globally.

Use one directory per project and purpose:

```text
dictionaries/<project-id>/correction/<language>/<dictionary-id>.json
dictionaries/<project-id>/translation/<direction>/<dictionary-id>.json
```

Dictionary IDs and filenames are immutable versions. Publish a new file for a changed decision
set; Git history is not a substitute for the artifact's own version, ID, proposal hash, and
content hash. Correction dictionaries retain both approved and rejected decisions. Only
approved entries are sent to a provider; rejected entries are carried into later proposals so
the same mapping does not return as pending without an explicit human decision change.

Private-corpus proposals, model state, and pilot output remain under `/tmp` and outside Git.
Commit a reviewed dictionary only when its source and included evidence are redistributable.

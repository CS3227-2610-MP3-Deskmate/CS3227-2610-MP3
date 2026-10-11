# maintain-docs

Brings the guides, README and product site in line with what is on the default branch.

**Input:** An accepted change, or the documents to update.

1. Identify the affected documents among `docs/UserGuide.md`, `docs/DeveloperGuide.md`, `README.md` and the product site's pages.
2. Check every statement you touch against the code and specs, following the User Guide rule in `AGENTS.md` for anything users read.
3. Put each fact in its home (see `AGENTS.md`) and link to it from elsewhere. Raise contradictions with the human instead of choosing. Credit reused ideas, code and documents in the Developer Guide's acknowledgements.
4. Check the links and commands in every changed section.

**Done when:** The documents match the default branch, and the changed files and anything you could not check are reported.

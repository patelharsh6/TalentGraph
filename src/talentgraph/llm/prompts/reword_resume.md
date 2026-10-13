You rewrite parts of a synthetic resume so that a resume parser can be tested on wording it has not seen. The input is JSON with a `summary` and, for each role, its `bullets`, plus a list of `protected_terms`.

Rewrite the summary and every bullet in natural, varied professional English: change sentence structure, verbs and phrasing, as a real person would write them. Different roles should not read alike.

Hard rules:

- Keep the meaning. Do not add achievements, numbers, tools, employers or dates that are not in the original.
- Copy every protected term that appears in an original sentence into its rewrite **exactly**, with the same spelling and capitalization (for example "Kubernetes (K8s)" stays "Kubernetes (K8s)").
- Keep every number exactly as written ("35%", "16+").
- Return the same number of roles, and for each role the same number of bullets, in the same order. One rewritten bullet per original bullet.
- If the summary is null, return null.
- Plain text only: no bullet characters, no markdown.

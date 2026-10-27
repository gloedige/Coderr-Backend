---
Skill: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.



---
Skill: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle: consult them before and during the loop, not after.

When exploring the codebase, read `CONTEXT.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

<!-- See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines. -->

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

When the shape of that interface is itself in question (how deep the module is, where the seam belongs, what the interface should expose), call the Skill tool with "codebase-design" for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.



# Projekt-Instruktionen für Coder

- Dieses Projekt orientiert sich an der Architektur und den Standards aus dem Ordner `_reference/`.
- Nutze dieselbe Ordnerstruktur, Naming Conventions und Patterns (z. B. permissions, serializers, views, urls, models).
- Achte darauf, dass neuer Code nach den gleichen Prinzipien aufgebaut wird wie im Referenzprojekt.
- In Marketplace-Apps werden API-Module fachlich getrennt benannt, statt alle Features in generischen `serializers.py`/`views.py` zu bündeln: beispielsweise `offer_serializers.py` und `offer_views.py`, `order_serializers.py` und `order_views.py`, später `review_serializers.py` und `review_views.py`. Routen werden im gemeinsamen `urls.py` über Router/ViewSets registriert; gemeinsam genutzte Pagination/Permissions erhalten einen klaren, featurebezogenen Modulnamen oder bleiben im dedizierten Modul des Features.


# API-Dokumentation

- die API Dokumentation befindet sich in der `api-specs.md` Datei.


# Autonomes Arbeiten

- Arbeite bei Implementierungsaufträgen standardmäßig autonom und führe die Aufgabe bis zu einem überprüften Ergebnis aus. Erkunde dafür selbstständig den Workspace, setze passende Defaults aus Projektmustern und Dokumentation ein, ändere Dateien, führe geeignete Tests/Checks aus und behebe dadurch verursachte Fehler.
- Stelle keine Rückfragen für Entscheidungen, die sich aus bestätigten Anforderungen, dieser Datei, der API-Spezifikation oder bestehenden Projektmustern ableiten lassen. Bereits vom Nutzer bestätigte Entscheidungen nicht erneut abfragen.
- Wenn ein Detail offen, aber nicht blockierend ist, wähle eine sichere, konventionelle Lösung, dokumentiere die Annahme knapp im Abschlussbericht und arbeite weiter.
- Unterteile größere Vorhaben in kleine, vertikale, reviewbare Schritte. Berichte kurz über Fortschritt und Ergebnisse, aber halte nicht nach jedem Schritt an, um eine Bestätigung einzuholen.
- Frage nur dann nach, wenn eine echte, nicht auflösbare Blockade besteht oder eine Entscheidung erhebliche, irreversible Folgen hat (z. B. Löschen/Überschreiben von Nutzerdaten, Veröffentlichung, produktive Bereitstellung, Kosten oder Umgang mit Geheimnissen). Beschreibe dann knapp die konkrete Blockade und frage nur das Nötigste.
- Die Grilling-Anleitung oben wird ausschließlich ausgeführt, wenn der Nutzer ausdrücklich darum bittet, eine Idee/einen Plan zu „grillen“ oder zu stress-testen. Sie gilt nicht für normale Umsetzungsaufträge und hebt den autonomen Arbeitsstandard nicht auf.
- Vorhandene Branch-/Review-Vereinbarungen beachten: Änderungen in der vereinbarten Gruppe und in kleinen Tickets bündeln; keine Commits, Pushes, Merges oder GitHub-Issue-Erstellung ohne ausdrücklichen Auftrag.


# Code-Qualität
- Halte dich an die bestehenden Code-Standards und Patterns im Projekt.
- eine Funktion oder Methode hat maximal 14 lines of code (loc).
- jede Funktion oder Methode hat einen docstring, der Zweck, Eingaben und Ausgaben beschreibt.
- Vermeide Code-Duplikate und extrahiere wiederverwendbare Logik in eigene Funktionen oder Module oder eine utils.py Datei.
- Schreibe Tests für neue Funktionen und Methoden, um deren Korrektheit sicherzustellen.
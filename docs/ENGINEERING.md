# Engineering

Mandatory coding rules, quality gates, the functional paradigm and prohibition policies that bind all code and every other document.

## Documentation ownership

Each concept has one canonical definition in exactly one document. Other documents reference that definition by link or identifier and never restate it.

| Owner | Defines |
| ----- | ------- |
| `docs/ENGINEERING.md` | Coding and documentation rules |
| `docs/REQUIREMENTS.md` | Business scenarios, nonfunctional targets, and gate acceptance criteria |
| `docs/DOMAIN.md` | Terms, states, invariants, and policies of the concierge |
| `docs/ARCHITECTURE.md` | Modules, their responsibilities, allowed dependency directions, and runtime topology |
| `docs/CONTRACTS.md` | Ports, typed outcomes, failures, cancellation, and provider substitution |
| `docs/SLICES.md` | How each business scenario executes across modules and ports |
| `docs/VALIDATION.md` | How tests prove requirements, contracts, and behaviors |
| `docs/adr/` | Why a consequential decision went the way it did |

## System ownership

Each kind of fact lives in one system. The others point to it.

| System | Authoritative for |
| ------ | ----------------- |
| Beads | Work items, dependencies, progress, and execution order |
| Design documents | Requirements, architecture, invariants, contracts, and decisions |
| Automated gates | Mechanical checks of rules these documents state |
| Commit and pull request recaps | What changed, why, and its risk |

Open questions belong in Beads. A document states only settled decisions.

## Identifiers

Requirements, domain rules, modules, ports, slices, tests and decisions each carry a stable identifier. Its owning document defines it once: in a heading or in a table row. Every other document cites the identifier instead of repeating the definition. Retired identifiers stay retired. Nobody reuses or renumbers them.

| Prefix | Owner |
| ------ | ----- |
| `REQ-` | Requirements |
| `DOM-` | Domain |
| `ARC-` | Architecture |
| `CON-` | Contracts |
| `SLC-` | Slices |
| `VAL-` | Validation |
| `ADR-` | Decision records |

Each prefix takes a three-digit number, for example `REQ-001`. A decision record filename starts with its number, for example `adr/0001-ports.md`.

## Writing rules

- Link only to documents this one builds on: an earlier entry in the index, or a decision record. A link to a later document or to the index inverts the dependency.
- Split a document before the docs gate's size cap. Put the parts in a folder named after the owner and list each part in the index.
- Draw diagrams as plain-text art inside fenced text blocks.
- State the current design only. Git history and decision records hold change. Documents carry no version, date, or status labels.
- A specification links to the decision record behind it. The record explains the reasoning, may link to earlier documents, and never links back to that specification.
- Scope stays at proof of concept. Add no capability, abstraction, or hardening unless the requirements call for it.

## Review checklist

Reviewers apply this checklist to every pull request that changes a document. It covers only what the automated gates can't check.

1. Each new concept appears in its owning document and nowhere else.
2. No document defines an existing concept again in different words.
3. Every cited identifier resolves to exactly one definition.
4. No statement contradicts another document.
5. New requirements carry acceptance criteria a test can observe.
6. Reasoning sits in a decision record, not in the specification.
7. The text states decisions. Options and open questions stay out.
8. The change stays within proof-of-concept scope.

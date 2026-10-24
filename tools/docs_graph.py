import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DOCS: Final = Path("docs")
INDEX: Final = DOCS / "README.md"
DECISIONS: Final = DOCS / "adr"
MAX_LINES: Final = 120
MAX_WORDS: Final = 1000

_FENCE: Final = re.compile(r"^\s*(```|~~~)")
_HEADING: Final = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_INLINE_LINK: Final = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_REFERENCE_LINK: Final = re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)")
_EXTERNAL: Final = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_MERMAID: Final = re.compile(r"^\s*(```|~~~)\s*mermaid\b", re.IGNORECASE)
_STATE_LABEL: Final = re.compile(
    r"\bv\d+(?:\.\d+)*\b|\b\d{4}-\d{2}-\d{2}\b|^\s*(?:status|version|last updated)\s*:",
    re.IGNORECASE,
)
_WORD: Final = re.compile(r"\S+")


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass(frozen=True, slots=True)
class Document:
    path: Path
    headings: tuple[Heading, ...]
    targets: frozenset[Path]
    scope: str
    lines: int
    words: int
    mermaid: tuple[int, ...]
    state_labels: tuple[tuple[int, str], ...]


def _visible_lines(text: str) -> Iterator[tuple[int, str]]:
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            yield number, line


def _link_targets(path: Path, lines: Sequence[str]) -> frozenset[Path]:
    raw = [match for line in lines for match in _INLINE_LINK.findall(line)]
    raw += [match.group(1) for line in lines if (match := _REFERENCE_LINK.match(line))]
    return frozenset(
        (path.parent / target.split("#", 1)[0]).resolve()
        for target in raw
        if target.split("#", 1)[0] and not _EXTERNAL.match(target)
    )


def _scope(lines: Sequence[str]) -> str:
    after_title = False
    paragraph: list[str] = []
    for line in lines:
        if not after_title:
            after_title = line.startswith("# ")
        elif line.strip():
            paragraph.append(line.strip())
        elif paragraph:
            break
    text = " ".join(paragraph)
    return "" if _HEADING.match(text) or text.startswith(("-", "*", "+", "|", ">")) else text


def parse(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    visible = tuple(_visible_lines(text))
    lines = tuple(line for _, line in visible)
    headings = tuple(
        Heading(len(match.group(1)), match.group(2), number)
        for number, line in visible
        if (match := _HEADING.match(line))
    )
    return Document(
        path,
        headings,
        _link_targets(path, lines),
        _scope(lines),
        len(text.splitlines()),
        sum(len(_WORD.findall(line)) for line in lines),
        tuple(number for number, line in enumerate(text.splitlines(), start=1) if _MERMAID.match(line)),
        tuple(
            (number, match.group().strip())
            for number, line in visible
            if (match := _STATE_LABEL.search(line))
        ),
    )


def _cycle(graph: Mapping[Path, frozenset[Path]]) -> tuple[Path, ...]:
    state: dict[Path, int] = {}
    stack: list[Path] = []

    def visit(node: Path) -> tuple[Path, ...]:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(graph[node]):
            if state.get(nxt) == 1:
                return (*stack[stack.index(nxt) :], nxt)
            if nxt not in state and (found := visit(nxt)):
                return found
        stack.pop()
        state[node] = 2
        return ()

    for node in sorted(graph):
        if node not in state and (found := visit(node)):
            return found
    return ()


def check(root: Path) -> tuple[str, ...]:
    docs_dir = (root / DOCS).resolve()
    index_path = (root / INDEX).resolve()
    decisions_dir = (root / DECISIONS).resolve()
    if not docs_dir.is_dir():
        return ()
    entries = sorted(docs_dir.rglob("*"))
    errors = [
        f"{entry.relative_to(root.resolve())}: only Markdown files are allowed in docs/"
        for entry in entries
        if entry.is_file() and entry.suffix != ".md"
    ]
    files = [entry for entry in entries if entry.is_file() and entry.suffix == ".md"]
    if index_path not in files:
        return (*errors, f"{INDEX}: documentation index is missing")

    parsed = {path: parse(path) for path in files}
    nodes = {path: document for path, document in parsed.items() if path != index_path}
    decisions = {path for path in nodes if path.is_relative_to(decisions_dir)}
    specifications = set(nodes) - decisions

    def name(path: Path) -> str:
        return str(path.relative_to(root.resolve()))

    errors += [
        f"{name(path)}:1: first line must be the H1 title"
        for path, document in parsed.items()
        if not document.headings or document.headings[0].line != 1 or document.headings[0].level != 1
    ]
    errors += [
        f"{name(path)}: the paragraph after the title must declare the document scope"
        for path, document in nodes.items()
        if not document.scope
    ]

    errors += [
        f"{name(path)}: {document.lines} lines, {document.words} words; the cap is "
        f"{MAX_LINES} lines and {MAX_WORDS} words, about two A4 pages; split the document"
        for path, document in parsed.items()
        if document.lines > MAX_LINES or document.words > MAX_WORDS
    ]
    errors += [
        f"{name(path)}:{line}: mermaid diagrams are banned; draw the diagram in ASCII"
        for path, document in parsed.items()
        for line in document.mermaid
    ]
    errors += [
        f"{name(path)}:{line}: \"{label}\" is a version, date or status label; documents are stateless"
        for path, document in parsed.items()
        for line, label in document.state_labels
    ]

    unlinked = sorted(specifications - parsed[index_path].targets)
    errors += [f"{name(path)}: not linked from {INDEX}" for path in unlinked]
    referenced = {target for path in specifications for target in nodes[path].targets}
    errors += [
        f"{name(path)}: decision record is not referenced from its authoritative document"
        for path in sorted(decisions - referenced)
    ]

    owners: dict[str, list[tuple[Path, Heading]]] = {}
    for path, document in nodes.items():
        if path in decisions:
            continue
        for heading in document.headings[1:]:
            owners.setdefault(heading.text.casefold(), []).append((path, heading))
    errors += [
        f"{name(path)}:{heading.line}: heading \"{heading.text}\" is owned more than once: "
        + ", ".join(f"{name(other)}:{seen.line}" for other, seen in claims if seen != heading)
        for claims in owners.values()
        if len(claims) > 1
        for path, heading in claims
    ]

    graph = {
        path: frozenset(target for target in document.targets if target in nodes and target != path)
        for path, document in nodes.items()
    }
    errors += [
        f"{name(path)}: links to the index; documents reference definitions, not {INDEX}"
        for path, document in nodes.items()
        if index_path in document.targets
    ]
    if cycle := _cycle(graph):
        errors.append("docs: reference cycle " + " -> ".join(name(path) for path in cycle))
    return tuple(errors)


def main(argv: Sequence[str]) -> int:
    root = Path(argv[0]) if argv else Path()
    errors = check(root)
    sys.stdout.write("".join(f"{error}\n" for error in errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

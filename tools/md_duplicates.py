import argparse
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, override

DEFAULT_WINDOW: Final = 8
DEFAULT_MIN_SENTENCE_WORDS: Final = 5
DEFAULT_EXCLUDE: Final = (
    r"^(archive_DO_NOT_COMMIT|\.agents|\.beads|\.claude|\.codex|\.cursor"
    r")/|^(AGENTS|CLAUDE)\.md$"
)
MARKDOWN_PATTERNS: Final = ("*.md", "*.mdx")

_COMMENT: Final = re.compile(r"<!--.*?-->", re.DOTALL)
_FRONT_MATTER: Final = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_FENCE: Final = re.compile(r"^\s*(```|~~~)")
_HEADING: Final = re.compile(r"^\s*#{1,6}\s")
_BLOCK_START: Final = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\|)")
_REFERENCE_DEFINITION: Final = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")
_LINK_TARGET: Final = re.compile(r"\]\([^)]*\)")
_URL: Final = re.compile(r"<?https?://\S+>?")
_SENTENCE_END: Final = re.compile(r"(?<=[.!?])\s+")
_WORD: Final = re.compile(r"[^\W_]+")

type Kind = Literal["sentence", "window"]


@dataclass(frozen=True, slots=True)
class Location:
    path: str
    line: int

    @override
    def __str__(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True, slots=True)
class Block:
    location: Location
    text: str


@dataclass(frozen=True, slots=True)
class Finding:
    kind: Kind
    location: Location
    others: tuple[Location, ...]
    words: tuple[str, ...]

    def render(self) -> str:
        others = ", ".join(str(other) for other in self.others)
        excerpt = " ".join(self.words)
        size = len(self.words)
        return f'{self.location}: duplicate {self.kind} ({size} words) also at {others}: "{excerpt}"'


def normalize(text: str) -> tuple[str, ...]:
    without_links = _URL.sub(" ", _LINK_TARGET.sub("]", text))
    return tuple(_WORD.findall(without_links.lower()))


def _blank_preserving_lines(match: re.Match[str]) -> str:
    return "\n" * match.group().count("\n")


def _strip_invisible(text: str) -> str:
    return _COMMENT.sub(_blank_preserving_lines, _FRONT_MATTER.sub(_blank_preserving_lines, text))


def split_blocks(path: str, text: str) -> tuple[Block, ...]:
    blocks: list[Block] = []
    current: list[str] = []
    start = 0
    in_fence = False

    def flush() -> None:
        if current:
            blocks.append(Block(Location(path, start), "\n".join(current)))
            current.clear()

    for number, line in enumerate(_strip_invisible(text).splitlines(), start=1):
        if _FENCE.match(line):
            flush()
            in_fence = not in_fence
            start = number + 1
        elif in_fence:
            current.append(line)
        elif not line.strip() or _REFERENCE_DEFINITION.match(line):
            flush()
        else:
            if _BLOCK_START.match(line):
                flush()
            if not current:
                start = number
            current.append(line)
            if _HEADING.match(line):
                flush()
    flush()
    return tuple(blocks)


def _runs(positions: Sequence[int]) -> tuple[tuple[int, int], ...]:
    runs: list[tuple[int, int]] = []
    for position in positions:
        if runs and runs[-1][1] == position - 1:
            runs[-1] = (runs[-1][0], position)
        else:
            runs.append((position, position))
    return tuple(runs)


def _window_findings(blocks: Sequence[Block], window: int) -> tuple[Finding, ...]:
    words_by_block = tuple(normalize(block.text) for block in blocks)
    occurrences: defaultdict[tuple[str, ...], list[tuple[int, int]]] = defaultdict(list)
    for index, words in enumerate(words_by_block):
        for position in range(len(words) - window + 1):
            occurrences[words[position : position + window]].append((index, position))

    findings: list[Finding] = []
    for index, words in enumerate(words_by_block):
        duplicated = [
            position
            for position in range(len(words) - window + 1)
            if len(occurrences[words[position : position + window]]) > 1
        ]
        for run_start, run_end in _runs(duplicated):
            key = words[run_start : run_start + window]
            others = tuple(
                blocks[other].location
                for other, position in occurrences[key]
                if (other, position) != (index, run_start)
            )
            excerpt = words[run_start : run_end + window]
            findings.append(Finding("window", blocks[index].location, others, excerpt))
    return tuple(findings)


def _sentence_findings(
    blocks: Sequence[Block], window: int, min_words: int
) -> tuple[Finding, ...]:
    occurrences: defaultdict[tuple[str, ...], list[Location]] = defaultdict(list)
    for block in blocks:
        for sentence in _SENTENCE_END.split(block.text):
            words = normalize(sentence)
            if min_words <= len(words) < window:
                occurrences[words].append(block.location)
    return tuple(
        Finding("sentence", location, tuple(locations[:index] + locations[index + 1 :]), words)
        for words, locations in occurrences.items()
        if len(locations) > 1
        for index, location in enumerate(locations)
    )


def find_duplicates(
    documents: Iterable[tuple[str, str]], window: int, min_sentence_words: int
) -> tuple[Finding, ...]:
    blocks = tuple(block for path, text in documents for block in split_blocks(path, text))
    findings = _window_findings(blocks, window) + _sentence_findings(
        blocks, window, min_sentence_words
    )
    return tuple(
        sorted(findings, key=lambda finding: (finding.location.path, finding.location.line))
    )


def tracked_markdown(exclude: re.Pattern[str]) -> tuple[str, ...]:
    git = shutil.which("git")
    if git is None:
        message = "git executable not found on PATH"
        raise RuntimeError(message)
    listed = subprocess.run(
        [git, "ls-files", "-z", "--cached", "--", *MARKDOWN_PATTERNS],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return tuple(
        path
        for path in listed.split("\0")
        if path and not exclude.search(path) and Path(path).is_file()
    )


class Arguments(argparse.Namespace):
    window: int = DEFAULT_WINDOW
    min_sentence_words: int = DEFAULT_MIN_SENTENCE_WORDS
    exclude: str = DEFAULT_EXCLUDE
    paths: Sequence[str] = ()


def parse_arguments(argv: Sequence[str]) -> Arguments:
    parser = argparse.ArgumentParser(description="Ruthless duplicate-prose gate for Markdown.")
    _ = parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    _ = parser.add_argument("--min-sentence-words", type=int, default=DEFAULT_MIN_SENTENCE_WORDS)
    _ = parser.add_argument("--exclude", default=DEFAULT_EXCLUDE)
    _ = parser.add_argument("paths", nargs="*", help="files to scan (default: git index)")
    return parser.parse_args(argv, namespace=Arguments())


def main(argv: Sequence[str]) -> int:
    arguments = parse_arguments(argv)
    paths = tuple(arguments.paths) or tracked_markdown(re.compile(arguments.exclude))
    documents = tuple((path, Path(path).read_text(encoding="utf-8")) for path in paths)
    findings = find_duplicates(documents, arguments.window, arguments.min_sentence_words)
    for finding in findings:
        print(finding.render())
    if findings:
        summary = f"{len(findings)} duplicate occurrence(s) in {len(paths)} Markdown file(s)."
        print(f"\n{summary} Keep one authoritative copy and link to it.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

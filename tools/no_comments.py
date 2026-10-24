import re
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Final

type Checker = Callable[[str], Iterator[int]]

PARSED_BY_AST_GREP: Final = frozenset(
    {
        ".py",
        ".pyi",
        ".sh",
        ".yml",
        ".yaml",
        ".json",
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".mts",
        ".cts",
        ".tsx",
        ".css",
        ".html",
        ".htm",
    }
)
COMMENTLESS_SUFFIXES: Final = frozenset({".txt"})

_HASH_LINE: Final = re.compile(r"^\s*#")
_INI_COMMENT: Final = re.compile(r"(^|\s)[#;]")
_MAKE_COMMENT: Final = re.compile(r"(^|\s)#")
_FENCE: Final = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE: Final = re.compile(r"`+[^`]*`+")
_HTML_COMMENT: Final = re.compile(r"<!--")
_LINK_COMMENT: Final = re.compile(r"^\s*\[[^\]]*\]:\s*(#|<>)")


def hash_lines(text: str) -> Iterator[int]:
    for number, line in enumerate(text.splitlines(), start=1):
        if _HASH_LINE.match(line):
            yield number


def ini_lines(text: str) -> Iterator[int]:
    for number, line in enumerate(text.splitlines(), start=1):
        if _INI_COMMENT.search(line):
            yield number


def make_lines(text: str) -> Iterator[int]:
    for number, line in enumerate(text.splitlines(), start=1):
        if _MAKE_COMMENT.search(line):
            yield number


def markdown_lines(text: str) -> Iterator[int]:
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            visible = _INLINE_CODE.sub("", line)
            if _HTML_COMMENT.search(visible) or _LINK_COMMENT.match(visible):
                yield number


def toml_lines(text: str) -> Iterator[int]:
    multiline: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        index = 0
        while index < len(line):
            if multiline is not None:
                end = line.find(multiline, index)
                if end < 0:
                    break
                multiline, index = None, end + 3
            elif line.startswith(('"""', "'''"), index):
                multiline, index = line[index : index + 3], index + 3
            elif line[index] in "\"'":
                quote, index = line[index], index + 1
                while index < len(line) and line[index] != quote:
                    index += 2 if quote == '"' and line[index] == "\\" else 1
                index += 1
            elif line[index] == "#":
                yield number
                break
            else:
                index += 1


CHECKERS_BY_SUFFIX: Final[dict[str, Checker]] = {
    ".toml": toml_lines,
    ".ini": ini_lines,
    ".cfg": ini_lines,
    ".md": markdown_lines,
    ".mdx": markdown_lines,
    ".env": hash_lines,
}
CHECKERS_BY_NAME: Final[dict[str, Checker]] = {
    ".editorconfig": ini_lines,
    ".gitignore": hash_lines,
    ".gitattributes": hash_lines,
    ".dockerignore": hash_lines,
    "Dockerfile": hash_lines,
    "Makefile": make_lines,
}


def checker_for(path: Path) -> Checker | None:
    if path.name in CHECKERS_BY_NAME:
        return CHECKERS_BY_NAME[path.name]
    if path.name.startswith(".env"):
        return hash_lines
    return CHECKERS_BY_SUFFIX.get(path.suffix)


def violations(path: Path) -> tuple[str, ...]:
    data = path.read_bytes()
    if not data or b"\0" in data or path.suffix in COMMENTLESS_SUFFIXES:
        return ()
    if path.suffix in PARSED_BY_AST_GREP:
        return ()
    checker = checker_for(path)
    if checker is None:
        return (f"{path}: no comment checker for this file type; add one before committing it",)
    return tuple(
        f"{path}:{line}: comments are banned" for line in checker(data.decode("utf-8"))
    )


def main(paths: Sequence[str]) -> int:
    found = tuple(message for path in paths for message in violations(Path(path)))
    sys.stdout.write("".join(f"{message}\n" for message in found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

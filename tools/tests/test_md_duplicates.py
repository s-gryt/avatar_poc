import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from typing import Final

from md_duplicates import find_duplicates, main

WINDOW: Final = 8
MIN_WORDS: Final = 5
SHARED: Final = "Every design fact has exactly one authoritative document in this repository"


def kinds(documents: list[tuple[str, str]]) -> list[str]:
    return [finding.kind for finding in find_duplicates(documents, WINDOW, MIN_WORDS)]


class FindDuplicatesTest(unittest.TestCase):
    def test_distinct_prose_passes(self) -> None:
        documents = [("a.md", "Alpha owns the domain model."), ("b.md", "Beta owns the ports.")]
        self.assertEqual(kinds(documents), [])

    def test_shared_window_fails_in_both_files(self) -> None:
        documents = [("a.md", f"Intro. {SHARED}."), ("b.md", f"{SHARED}, as stated.")]
        findings = find_duplicates(documents, WINDOW, MIN_WORDS)
        self.assertEqual({finding.location.path for finding in findings}, {"a.md", "b.md"})
        self.assertEqual({finding.kind for finding in findings}, {"window"})

    def test_short_repeated_sentence_fails(self) -> None:
        sentence = "Ports never call each other."
        documents = [("a.md", f"{sentence} Alpha."), ("b.md", f"Beta. {sentence}")]
        self.assertEqual(kinds(documents), ["sentence", "sentence"])

    def test_sentence_below_minimum_passes(self) -> None:
        documents = [("a.md", "See the index."), ("b.md", "See the index.")]
        self.assertEqual(kinds(documents), [])

    def test_link_targets_and_urls_are_ignored(self) -> None:
        target = "contracts/session/start/and/stop/flow/details/page.md"
        documents = [
            ("a.md", f"Alpha [a]({target}) and https://example.com/{target} here."),
            ("b.md", f"Beta [b]({target}) or https://example.com/{target} there."),
        ]
        self.assertEqual(kinds(documents), [])

    def test_html_comments_and_front_matter_are_ignored(self) -> None:
        documents = [
            ("a.md", f"---\ntitle: {SHARED}\n---\nAlpha."),
            ("b.md", f"Beta.\n<!-- {SHARED} -->\n"),
        ]
        self.assertEqual(kinds(documents), [])

    def test_finding_reports_line_of_block(self) -> None:
        documents = [("a.md", f"# Title\n\n{SHARED}."), ("b.md", f"{SHARED}.")]
        lines = {f.location.path: f.location.line for f in find_duplicates(documents, WINDOW, MIN_WORDS)}
        self.assertEqual(lines, {"a.md": 3, "b.md": 1})


class MainTest(unittest.TestCase):
    def run_main(self, texts: dict[str, str]) -> int:
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, text in texts.items():
                path = Path(directory) / name
                _ = path.write_text(text, encoding="utf-8")
                paths.append(str(path))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return main(paths)

    def test_exit_one_on_duplicate(self) -> None:
        self.assertEqual(self.run_main({"a.md": SHARED, "b.md": SHARED}), 1)

    def test_exit_zero_when_clean(self) -> None:
        self.assertEqual(self.run_main({"a.md": "Alpha owns state.", "b.md": "Beta owns ports."}), 0)


if __name__ == "__main__":
    unittest.main()

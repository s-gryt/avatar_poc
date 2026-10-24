import tempfile
import unittest
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from docs_graph import check

INDEX: Final = "# Documentation\n\n1. [Alpha](ALPHA.md)\n2. [Beta](BETA.md)\n"
ALPHA: Final = "# Alpha\n\nAlpha owns the domain model.\n"
BETA: Final = "# Beta\n\nBeta owns the ports and builds on [Alpha](ALPHA.md).\n"
VALID: Final = {"README.md": INDEX, "ALPHA.md": ALPHA, "BETA.md": BETA}


@contextmanager
def docs(files: Mapping[str, str]) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, text in files.items():
            path = root / "docs" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            _ = path.write_text(text, encoding="utf-8")
        yield root


def errors(files: Mapping[str, str]) -> str:
    with docs(files) as root:
        return "\n".join(check(root))


class CheckTest(unittest.TestCase):
    def test_valid_graph_passes(self) -> None:
        self.assertEqual(errors(VALID), "")

    def test_repository_docs_pass(self) -> None:
        self.assertEqual(check(Path(__file__).resolve().parents[2]), ())

    def test_missing_docs_directory_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(check(Path(directory)), ())

    def test_missing_index_fails(self) -> None:
        self.assertIn("documentation index is missing", errors({"ALPHA.md": ALPHA}))

    def test_unlinked_document_fails(self) -> None:
        self.assertIn("docs/GAMMA.md: not linked from", errors({**VALID, "GAMMA.md": "# Gamma\n\nGamma.\n"}))

    def test_missing_title_fails(self) -> None:
        self.assertIn("first line must be the H1 title", errors({**VALID, "ALPHA.md": "Alpha.\n"}))

    def test_missing_scope_fails(self) -> None:
        self.assertIn("must declare the document scope", errors({**VALID, "ALPHA.md": "# Alpha\n\n## Part\n"}))

    def test_reference_cycle_fails(self) -> None:
        cyclic = "# Alpha\n\nAlpha builds on [Beta](BETA.md).\n"
        self.assertIn("reference cycle", errors({**VALID, "ALPHA.md": cyclic}))

    def test_link_inside_code_fence_is_ignored(self) -> None:
        fenced = "# Alpha\n\nAlpha owns state.\n\n```markdown\n[Beta](BETA.md)\n```\n"
        self.assertEqual(errors({**VALID, "ALPHA.md": fenced}), "")

    def test_heading_owned_twice_fails(self) -> None:
        files = {**VALID, "ALPHA.md": ALPHA + "\n## Session\n", "BETA.md": BETA + "\n## session\n"}
        self.assertIn('heading "Session" is owned more than once', errors(files))

    def test_link_to_index_fails(self) -> None:
        self.assertIn("links to the index", errors({**VALID, "ALPHA.md": ALPHA + "\n[Index](README.md)\n"}))

    def test_nested_directory_fails(self) -> None:
        self.assertIn("only flat Markdown files", errors({**VALID, "contracts/PORT.md": "# Port\n\nPort.\n"}))

    def test_non_markdown_file_fails(self) -> None:
        self.assertIn("only flat Markdown files", errors({**VALID, "diagram.txt": "x\n"}))


if __name__ == "__main__":
    unittest.main()

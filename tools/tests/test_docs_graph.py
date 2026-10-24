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

    def test_nested_document_linked_from_index_passes(self) -> None:
        index = INDEX + "3. [Port](contracts/PORT.md)\n"
        port = "# Port\n\nPort builds on [Beta](../BETA.md).\n"
        self.assertEqual(errors({**VALID, "README.md": index, "contracts/PORT.md": port}), "")

    def test_nested_document_not_in_index_fails(self) -> None:
        self.assertIn("docs/contracts/PORT.md: not linked from", errors({**VALID, "contracts/PORT.md": "# Port\n\nPort.\n"}))

    def test_non_markdown_file_fails(self) -> None:
        self.assertIn("only Markdown files are allowed", errors({**VALID, "diagram.txt": "x\n"}))

    def test_decision_referenced_by_specification_passes(self) -> None:
        beta = BETA + "\nChosen per [ADR 1](adr/0001-ports.md).\n"
        record = "# Ports over direct calls\n\nCapabilities talk through ports.\n\n## Context\n"
        self.assertEqual(errors({**VALID, "BETA.md": beta, "adr/0001-ports.md": record}), "")

    def test_unreferenced_decision_fails(self) -> None:
        record = "# Ports over direct calls\n\nCapabilities talk through ports.\n"
        self.assertIn("decision record is not referenced", errors({**VALID, "adr/0001-ports.md": record}))

    def test_decision_linking_back_to_specification_fails(self) -> None:
        beta = BETA + "\nChosen per [ADR 1](adr/0001-ports.md).\n"
        record = "# Ports over direct calls\n\nSee [Beta](../BETA.md).\n"
        self.assertIn("reference cycle", errors({**VALID, "BETA.md": beta, "adr/0001-ports.md": record}))

    def test_decision_template_headings_may_repeat(self) -> None:
        beta = BETA + "\n[ADR 1](adr/0001-a.md) and [ADR 2](adr/0002-b.md).\n"
        first = "# First choice\n\nAlpha first.\n\n## Context\n\n## Decision\n"
        second = "# Second choice\n\nBeta second.\n\n## Context\n\n## Decision\n"
        files = {**VALID, "BETA.md": beta, "adr/0001-a.md": first, "adr/0002-b.md": second}
        self.assertEqual(errors(files), "")

    def test_document_over_line_cap_fails(self) -> None:
        self.assertIn("split the document", errors({**VALID, "ALPHA.md": ALPHA + "\n" * 130}))

    def test_document_over_word_cap_fails(self) -> None:
        self.assertIn("split the document", errors({**VALID, "ALPHA.md": ALPHA + "word " * 1001 + "\n"}))

    def test_mermaid_fence_fails(self) -> None:
        diagram = ALPHA + "\n```mermaid\ngraph TD\n```\n"
        self.assertIn("mermaid diagrams are banned", errors({**VALID, "ALPHA.md": diagram}))

    def test_version_label_fails(self) -> None:
        self.assertIn("documents are stateless", errors({**VALID, "ALPHA.md": ALPHA + "\nThe v2 model applies.\n"}))

    def test_date_label_fails(self) -> None:
        self.assertIn("documents are stateless", errors({**VALID, "ALPHA.md": ALPHA + "\nAgreed 2026-10-24.\n"}))

    def test_status_label_fails(self) -> None:
        self.assertIn("documents are stateless", errors({**VALID, "ALPHA.md": ALPHA + "\nStatus: draft\n"}))

    def test_long_mermaid_fence_fails(self) -> None:
        diagram = ALPHA + "\n````Mermaid\ngraph TD\n````\n"
        self.assertIn("mermaid diagrams are banned", errors({**VALID, "ALPHA.md": diagram}))

    def test_mermaid_text_inside_longer_fence_passes(self) -> None:
        nested = ALPHA + "\n````text\n```mermaid\nv2\n```\n````\n"
        self.assertEqual(errors({**VALID, "ALPHA.md": nested}), "")

    def test_date_label_without_iso_value_fails(self) -> None:
        self.assertIn("documents are stateless", errors({**VALID, "ALPHA.md": ALPHA + "\nDate: pending\n"}))

    def test_date_in_link_destination_passes(self) -> None:
        beta = BETA + "\nChosen per [the decision](adr/2026-10-24-ports.md).\n"
        record = "# Ports over direct calls\n\nCapabilities talk through ports.\n"
        self.assertEqual(errors({**VALID, "BETA.md": beta, "adr/2026-10-24-ports.md": record}), "")

    def test_fenced_words_count_toward_word_cap(self) -> None:
        fenced = ALPHA + "\n```text\n" + "word " * 1001 + "\n```\n"
        self.assertIn("split the document", errors({**VALID, "ALPHA.md": fenced}))

    def test_decision_linking_to_earlier_specification_passes(self) -> None:
        beta = BETA + "\nChosen per [ADR 1](adr/0001-ports.md).\n"
        record = "# Ports over direct calls\n\nPorts carry [Alpha](../ALPHA.md) concepts.\n"
        self.assertEqual(errors({**VALID, "BETA.md": beta, "adr/0001-ports.md": record}), "")

    def test_decorated_status_labels_fail(self) -> None:
        for label in ("## Status: draft", "[Status: draft](BETA.md)", "- **Status:** draft"):
            with self.subTest(label=label):
                self.assertIn("documents are stateless", errors({**VALID, "ALPHA.md": ALPHA + f"\n{label}\n"}))

    def test_labels_inside_code_fence_pass(self) -> None:
        fenced = ALPHA + "\n```text\nv2 2026-10-24\n```\n"
        self.assertEqual(errors({**VALID, "ALPHA.md": fenced}), "")


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from no_comments import main, violations


def found(name: str, content: str | bytes) -> tuple[str, ...]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        if isinstance(content, bytes):
            _ = path.write_bytes(content)
        else:
            _ = path.write_text(content, encoding="utf-8")
        return tuple(message.removeprefix(f"{path}") for message in violations(path))


class ViolationsTest(unittest.TestCase):
    def test_hash_comment_in_ignore_file_fails(self) -> None:
        self.assertEqual(found(".gitignore", "dist/\n# build output\n"), (":2: comments are banned",))

    def test_clean_ignore_file_passes(self) -> None:
        self.assertEqual(found(".gitignore", "dist/\n*.log\n"), ())

    def test_dotenv_variants_use_hash_checker(self) -> None:
        self.assertEqual(found(".env.local", "# secret\nKEY=1\n"), (":1: comments are banned",))

    def test_toml_hash_inside_strings_passes(self) -> None:
        text = 'a = "x # y"\nb = \'z # w\'\nc = """\n# still string\n"""\n'
        self.assertEqual(found("lychee.toml", text), ())

    def test_toml_trailing_comment_fails(self) -> None:
        self.assertEqual(found("lychee.toml", 'a = "x" # note\n'), (":1: comments are banned",))

    def test_ini_semicolon_comment_fails(self) -> None:
        self.assertEqual(found(".vale.ini", "StylesPath = .vale\n; note\n"), (":2: comments are banned",))

    def test_makefile_comment_fails(self) -> None:
        self.assertEqual(found("Makefile", "all:\n\techo ok # note\n"), (":2: comments are banned",))

    def test_markdown_html_comment_fails(self) -> None:
        self.assertEqual(found("a.md", "# A\n\n<!-- hidden -->\n"), (":3: comments are banned",))

    def test_markdown_link_label_comment_fails(self) -> None:
        self.assertEqual(found("a.md", "[//]: # (hidden)\n"), (":1: comments are banned",))

    def test_markdown_comment_in_code_passes(self) -> None:
        self.assertEqual(found("a.md", "Use `<!-- x -->` here.\n\n```html\n<!-- x -->\n```\n"), ())

    def test_unknown_file_type_fails(self) -> None:
        self.assertEqual(
            found("data.xyz", "value\n"),
            (": no comment checker for this file type; add one before committing it",),
        )

    def test_ast_grep_types_are_skipped(self) -> None:
        self.assertEqual(found("tool.py", "# handled by ast-grep\n"), ())

    def test_commentless_empty_and_binary_files_are_skipped(self) -> None:
        self.assertEqual(found("notes.txt", "# plain\n"), ())
        self.assertEqual(found("empty.xyz", ""), ())
        self.assertEqual(found("blob.xyz", b"\x00\x01"), ())


class MainTest(unittest.TestCase):
    def test_exit_code_reflects_violations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clean = Path(directory) / ".gitignore"
            _ = clean.write_text("dist/\n", encoding="utf-8")
            dirty = Path(directory) / "Makefile"
            _ = dirty.write_text("# x\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([str(clean)]), 0)
                self.assertEqual(main([str(dirty)]), 1)
            self.assertEqual(output.getvalue(), f"{dirty}:1: comments are banned\n")


if __name__ == "__main__":
    unittest.main()

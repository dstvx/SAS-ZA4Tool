import unittest
from unittest.mock import MagicMock, patch

from lib.ui.ui import _parse_posix_key_seq, get_option_description


class TestUIKeyNavigation(unittest.TestCase):
    """Tests keyboard navigation mapping across standard ANSI and application cursor sequences."""

    def test_arrow_keys_normal_ansi(self) -> None:
        """Standard ANSI arrow sequences (\x1b[A, \x1b[B, \x1b[C, \x1b[D)."""
        self.assertEqual(_parse_posix_key_seq(b"\x1b[A"), "up")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[B"), "down")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[C"), "right")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[D"), "left")

    def test_arrow_keys_application_cursor(self) -> None:
        """Application cursor mode arrow sequences (\x1bOA, \x1bOB, \x1bOC, \x1bOD)."""
        self.assertEqual(_parse_posix_key_seq(b"\x1bOA"), "up")
        self.assertEqual(_parse_posix_key_seq(b"\x1bOB"), "down")
        self.assertEqual(_parse_posix_key_seq(b"\x1bOC"), "right")
        self.assertEqual(_parse_posix_key_seq(b"\x1bOD"), "left")

    def test_arrow_keys_modified(self) -> None:
        """Shift/Ctrl modified arrow sequences."""
        self.assertEqual(_parse_posix_key_seq(b"\x1b[1;2A"), "up")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[1;5A"), "up")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[1;2B"), "down")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[1;5B"), "down")

    def test_navigation_keys(self) -> None:
        """Home, End, PageUp, PageDown navigation."""
        self.assertEqual(_parse_posix_key_seq(b"\x1b[H"), "home")
        self.assertEqual(_parse_posix_key_seq(b"\x1bOH"), "home")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[1~"), "home")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[F"), "end")
        self.assertEqual(_parse_posix_key_seq(b"\x1bOF"), "end")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[4~"), "end")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[5~"), "pageup")
        self.assertEqual(_parse_posix_key_seq(b"\x1b[6~"), "pagedown")

    def test_standard_control_keys(self) -> None:
        """Enter, Space, Backspace, Esc, Ctrl keys."""
        self.assertEqual(_parse_posix_key_seq(b"\x1b"), "esc")
        self.assertEqual(_parse_posix_key_seq(b"\r"), "enter")
        self.assertEqual(_parse_posix_key_seq(b"\n"), "enter")
        self.assertEqual(_parse_posix_key_seq(b" "), "space")
        self.assertEqual(_parse_posix_key_seq(b"\x7f"), "backspace")
        self.assertEqual(_parse_posix_key_seq(b"\x08"), "backspace")
        self.assertEqual(_parse_posix_key_seq(b"\x03"), "ctrl+c")
        self.assertEqual(_parse_posix_key_seq(b"\x18"), "ctrl+x")
        self.assertEqual(_parse_posix_key_seq(b"\t"), "ctrl+i")

    def test_alphanumeric_shortcuts(self) -> None:
        """Alphanumeric shortcut inputs (1-9, A-Z)."""
        self.assertEqual(_parse_posix_key_seq(b"1"), "1")
        self.assertEqual(_parse_posix_key_seq(b"9"), "9")
        self.assertEqual(_parse_posix_key_seq(b"a"), "A")
        self.assertEqual(_parse_posix_key_seq(b"Z"), "Z")
        self.assertEqual(_parse_posix_key_seq(b""), "")

    def test_option_description_lookup(self) -> None:
        """Tests finding descriptions for menu items."""
        desc = get_option_description("Character Editor")
        self.assertIn("character name", desc.lower())
        desc_unknown = get_option_description("Nonexistent Option XYZ")
        self.assertEqual(desc_unknown, "No description available for this option.")

    @patch("subprocess.Popen")
    def test_launch_game_invocation(self, mock_popen: MagicMock) -> None:
        """Tests that launch_game executes without unhandled errors."""
        mock_popen.return_value = MagicMock()
        from lib.ui.ui import launch_game
        res = launch_game()
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)


if __name__ == "__main__":
    unittest.main()

import curses
import queue
import threading
import unittest
from unittest.mock import patch

import terminal_ui


class FakeScreen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.lines = []
        self.keypad_enabled = False

    def keypad(self, enabled):
        self.keypad_enabled = enabled

    def timeout(self, _milliseconds):
        pass

    def erase(self):
        self.lines = []

    def getmaxyx(self):
        return 12, 80

    def addstr(self, row, column, text, _attributes=0):
        self.lines.append((row, column, text))

    def move(self, _row, _column):
        pass

    def refresh(self):
        pass

    def get_wch(self):
        return next(self.keys, -1)

    def getch(self):
        return next(self.keys, -1)


class TerminalUITests(unittest.TestCase):
    def test_receive_send_unicode_and_quit(self):
        screen = FakeScreen(["h", "i", "é", curses.KEY_ENTER, "/", "q", "u", "i", "t", curses.KEY_ENTER])
        updates = queue.Queue()
        updates.put(("message", "[12:00] bob: welcome"))
        sent = []

        with patch.object(terminal_ui.curses, "wrapper", side_effect=lambda draw: draw(screen)), patch.object(
            terminal_ui.curses, "curs_set"
        ):
            terminal_ui.run_chat_tui(
                "alice",
                "bob",
                updates,
                lambda message: sent.append(message) or True,
                threading.Event(),
            )

        self.assertEqual(sent, ["hié"])
        self.assertTrue(screen.keypad_enabled)
        self.assertTrue(any("bob: welcome" in line for _, _, line in screen.lines))


if __name__ == "__main__":
    unittest.main()
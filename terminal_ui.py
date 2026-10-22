import curses
import queue


_SPINNER = "|/-\\"


def run_chat_tui(username, other, updates, send_message, stop_event):
    def draw(stdscr):
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(120)
        _init_colors()

        input_text = ""
        transcript = []
        status = "Connected"
        scroll_from_bottom = 0
        frame = 0

        while not stop_event.is_set():
            while True:
                try:
                    kind, payload = updates.get_nowait()
                except queue.Empty:
                    break
                if kind == "message":
                    transcript.append(_single_line(payload))
                    scroll_from_bottom = 0
                elif kind == "error":
                    status = payload

            stdscr.erase()
            height, width = stdscr.getmaxyx()
            if height < 8 or width < 40:
                _safe_add(stdscr, 0, 0, "Resize terminal: minimum 40 columns x 8 rows", width)
                stdscr.refresh()
                try:
                    key = stdscr.get_wch()
                except curses.error:
                    continue
                if key in (3, 27):
                    break
                continue

            header = f" {username}   /   {other}"
            _safe_add(stdscr, 0, 0, header, width, curses.A_BOLD | _pair(1))
            live = f"{_SPINNER[frame % len(_SPINNER)]} LIVE " if not stop_event.is_set() else "OFFLINE"
            _safe_add(stdscr, 0, max(0, width - len(live) - 1), live, width, _pair(2) | curses.A_BOLD)
            _safe_add(stdscr, 1, 0, "─" * (width - 1), width, curses.A_DIM)

            body_top = 2
            body_height = height - 5
            max_scroll = max(0, len(transcript) - body_height)
            scroll_from_bottom = min(scroll_from_bottom, max_scroll)
            end = len(transcript) - scroll_from_bottom
            start = max(0, end - body_height)
            for row, line in enumerate(transcript[start:end]):
                attr = _pair(3) if line.startswith("You: ") else 0
                _safe_add(stdscr, body_top + row, 0, _clip(line, width - 1), width, attr)

            if scroll_from_bottom:
                status = f"History  +{scroll_from_bottom} rows  |  Up/Down to scroll"
            _safe_add(stdscr, height - 3, 0, "─" * (width - 1), width, curses.A_DIM)
            prompt = "> " + input_text
            _safe_add(stdscr, height - 2, 0, _clip(prompt, width - 1), width, _pair(4))
            _safe_add(stdscr, height - 1, 0, _clip(status, width - 1), width, curses.A_DIM)
            cursor_x = min(2 + len(input_text), width - 2)
            try:
                stdscr.move(height - 2, cursor_x)
            except curses.error:
                pass
            stdscr.refresh()
            frame += 1

            try:
                key = stdscr.get_wch()
            except curses.error:
                continue
            if key in (3, 27):
                break
            if key == curses.KEY_UP:
                scroll_from_bottom = min(scroll_from_bottom + 1, max_scroll)
                continue
            if key == curses.KEY_DOWN:
                scroll_from_bottom = max(0, scroll_from_bottom - 1)
                continue
            if key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
                input_text = input_text[:-1]
                continue
            if key in (curses.KEY_ENTER, "\n", "\r"):
                message = input_text.strip()
                input_text = ""
                if not message:
                    continue
                if message.lower() in {"/quit", "/exit"}:
                    break
                if message.lower() == "/help":
                    status = "Enter sends  |  /help commands  |  /quit exits  |  Up/Down history"
                    continue
                status = "Sending"
                stdscr.refresh()
                if not send_message(message):
                    status = "Send failed. Session may have expired."
                    stop_event.set()
                    continue
                transcript.append(_single_line(f"You: {message}"))
                scroll_from_bottom = 0
                status = "Sent"
                continue
            if isinstance(key, str) and key.isprintable() and len(input_text) < 4096:
                input_text += key

    curses.wrapper(draw)


def _init_colors():
    try:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
    except curses.error:
        pass


def _pair(number):
    try:
        return curses.color_pair(number) if curses.has_colors() else 0
    except curses.error:
        return 0


def _single_line(text):
    return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())


def _clip(text, width):
    if width <= 0:
        return ""
    text = _single_line(text)
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def _safe_add(stdscr, row, column, text, width, attributes=0):
    if width <= column or row < 0:
        return
    try:
        stdscr.addstr(row, column, str(text)[: width - column], attributes)
    except curses.error:
        pass

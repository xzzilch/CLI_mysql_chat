import curses
import queue
import textwrap


def run_chat_tui(username, other, updates, send_message, stop_event):
    def draw(stdscr):
        curses.curs_set(1)
        stdscr.keypad(True)
        stdscr.timeout(150)
        input_text = ""
        transcript = []
        status = "Connected. Enter sends; /help lists commands; /quit exits."
        scroll_from_bottom = 0

        while not stop_event.is_set():
            while True:
                try:
                    kind, payload = updates.get_nowait()
                except queue.Empty:
                    break

                if kind == "message":
                    transcript.append(payload)
                    scroll_from_bottom = 0
                elif kind == "error":
                    status = payload

            stdscr.erase()
            height, width = stdscr.getmaxyx()
            if height < 8 or width < 40:
                _safe_add(stdscr, 0, 0, "Resize terminal to at least 40 columns by 8 rows.", width)
                stdscr.refresh()
                key = stdscr.getch()
                if key in (3, 27):
                    break
                continue

            _safe_add(stdscr, 0, 0, f" TEXT SERVICE  |  {username}  ->  {other}", width, curses.A_BOLD)
            _safe_add(stdscr, 1, 0, "-" * width, width, curses.A_DIM)

            body_top = 2
            body_bottom = height - 4
            body_height = body_bottom - body_top
            wrapped = []
            for line in transcript:
                wrapped.extend(textwrap.wrap(line, max(1, width - 1)) or [""])
            visible = wrapped[-(body_height + scroll_from_bottom):] if scroll_from_bottom else wrapped[-body_height:]
            if scroll_from_bottom:
                visible = visible[:-scroll_from_bottom] if scroll_from_bottom < len(visible) else []
            for row, line in enumerate(visible[-body_height:]):
                _safe_add(stdscr, body_top + row, 0, line, width)

            _safe_add(stdscr, height - 3, 0, "-" * width, width, curses.A_DIM)
            _safe_add(stdscr, height - 2, 0, "> " + input_text, width)
            _safe_add(stdscr, height - 1, 0, status, width, curses.A_DIM)
            cursor_x = min(2 + len(input_text), width - 1)
            stdscr.move(height - 2, cursor_x)
            stdscr.refresh()

            try:
                key = stdscr.get_wch()
            except curses.error:
                continue
            if key in (3, 27):
                break
            if key == curses.KEY_UP:
                scroll_from_bottom = min(scroll_from_bottom + 1, max(0, len(wrapped) - body_height))
                continue
            if key == curses.KEY_DOWN:
                scroll_from_bottom = max(0, scroll_from_bottom - 1)
                continue
            if key in (curses.KEY_BACKSPACE, 8, 127):
                input_text = input_text[:-1]
                continue
            if key in (curses.KEY_ENTER, 10, 13):
                message = input_text.strip()
                input_text = ""
                if not message:
                    continue
                if message.lower() in {"/quit", "/exit"}:
                    break
                if message.lower() == "/help":
                    status = "Commands: /help, /quit. Up/Down scroll the transcript."
                    continue
                if not send_message(message):
                    status = "Send failed. The session may have expired."
                    stop_event.set()
                    break
                transcript.append(f"You: {message}")
                scroll_from_bottom = 0
                status = "Message sent."
                continue
            if isinstance(key, str) and key.isprintable() and len(input_text) < min(4096, width - 4):
                input_text += key

    curses.wrapper(draw)


def _safe_add(stdscr, row, column, text, width, attributes=0):
    if width <= column or row < 0:
        return
    try:
        stdscr.addstr(row, column, str(text)[:width - column], attributes)
    except curses.error:
        pass
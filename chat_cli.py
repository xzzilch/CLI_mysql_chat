import queue
import threading
import mysql.connector
import sys

from chat_backend import (
    add_contact,
    login,
    logout,
    passw,
    reg_user,
    search_contact,
    send_txt,
    stream_txts,
    uname,
)
from terminal_ui import run_chat_tui

db_lock = threading.Lock()
stop_signal = threading.Event()


def receive_messages(cursor, other, session_token, updates):
    last_timestamp = "2026-01-01 00:00:00"
    while not stop_signal.is_set():
        try:
            with db_lock:
                messages = stream_txts(cursor, other, last_timestamp, session_token)

            for msg in messages:
                updates.put((
                    "message",
                    f"[{msg['dispatched_at']}] {msg['sender_username']}: {msg['body_text']}",
                ))
                last_timestamp = str(msg['dispatched_at'])
        except mysql.connector.Error as error:
            updates.put(("error", "Listener stopped. The session or database rejected polling."))
            return
        except Exception as error:
            updates.put(("error", "Listener stopped because of a local error."))
            return

        stop_signal.wait(1.0)


def main():
    conn = None
    cursor = None
    session_token = None
    listener = None

    try:
        print("1. Login")
        print("2. Register")
        choice = input("> ").strip()

        if choice == "2":
            username = uname()
            phone = input("Phone Number > ").strip()
            if not phone:
                print("Phone number cannot be empty.")
                return
            password = passw()
            if not reg_user(username, phone, password):
                print("Registration failed. No account was created.")
                return
            print("Registration complete. Please restart script to log in.")
            return
        if choice != "1":
            print("Invalid choice. Enter 1 to log in or 2 to register.")
            return

        user_session = uname()
        pass_session = passw()
        conn, cursor, session_token = login(user_session, pass_session)
        pass_session = None
        if not conn or not cursor or not session_token:
            print("Login failed. Check your credentials and database connection.")
            return

        print("Logged in as--------", user_session)
        other = input("  Chat with user: ").strip()
        if not other:
            print("No chat user was entered.")
            return

        if not search_contact(cursor, other, session_token):
            print("User does not exist or could not be found.")
            return

        print(f"Connecting to ------------ {other}")
        if not add_contact(cursor, conn, other, session_token):
            print("Could not add the contact. The chat will not start.")
            return

        stop_signal.clear()
        updates = queue.Queue()
        listener = threading.Thread(
            target=receive_messages,
            args=(cursor, other, session_token, updates),
            daemon=True,
        )
        listener.start()

        def send_message(message):
            with db_lock:
                return send_txt(cursor, conn, other, message, session_token)

        if sys.stdin.isatty():
            run_chat_tui(user_session, other, updates, send_message, stop_signal)
        else:
            print("Chat connected. Type /quit to exit.")
            while not stop_signal.is_set():
                while True:
                    try:
                        kind, payload = updates.get_nowait()
                    except queue.Empty:
                        break
                    print(payload)
                message = input("> ").strip()
                if message.lower() in {"/quit", "/exit"}:
                    break
                if message and not send_message(message):
                    print("Send failed. The session may have expired.")
                    stop_signal.set()

    except KeyboardInterrupt:
        print("\nInterrupted. Closing the chat.")
    except EOFError:
        print("\nInput closed. Closing the chat.")
    except mysql.connector.Error as error:
        print("Database operation was rejected or unavailable.")
    except Exception as error:
        print("Unexpected local error. The chat will close.")
    finally:
        stop_signal.set()
        if listener and listener.is_alive():
            listener.join(timeout=2.0)
        if conn and cursor:
            with db_lock:
                logout(conn, cursor, session_token)


if __name__ == "__main__":
    main()

#FUNCTIONS
#CAREFUL -FUNCTIONS HAVE VERTICAL_DEPENDENCE
rt = '| RETURNED\n------------------\n END OF TEST'
import sys
import os
import re
import hashlib
import secrets
import mysql.connector
import socket
from port_utils import portstatus
import json
from getpass import getpass

_DB_PASSWORD_PATTERN = re.compile(r"^[A-Za-z0-9!@#$%^&*()_+=.\-]{16,128}$")
_PASSWORD_HASH_ITERATIONS = 600_000


def get_db_config():
    password = os.environ.get("TEXTSERVICE_DB_PASSWORD", "")
    if not _DB_PASSWORD_PATTERN.fullmatch(password):
        raise ValueError(
            "TEXTSERVICE_DB_PASSWORD must be 16-128 characters and use only "
            "letters, numbers, and !@#$%^&*()_+=.-"
        )

    try:
        port_number = int(os.environ.get("TEXTSERVICE_DB_PORT", "3306"))
    except ValueError:
        raise ValueError("TEXTSERVICE_DB_PORT must be a number from 1 to 65535") from None
    if not 1 <= port_number <= 65535:
        raise ValueError("TEXTSERVICE_DB_PORT must be a number from 1 to 65535")

    config = {
        "host": os.environ.get("TEXTSERVICE_DB_HOST", "localhost").strip(),
        "port": port_number,
        "user": os.environ.get("TEXTSERVICE_DB_USER", "client_user"),
        "password": password,
        "database": "text_service_db",
        "connection_timeout": 5,
    }

    if config["host"] not in {"localhost", "127.0.0.1", "::1"}:
        ca_file = os.environ.get("TEXTSERVICE_DB_SSL_CA")
        if not ca_file:
            raise ValueError("TEXTSERVICE_DB_SSL_CA is required for remote database connections")
        config.update(ssl_ca=ca_file, ssl_verify_cert=True, ssl_verify_identity=True)

    return config


def _validate_identity(user, field="username"):
    if not isinstance(user, str) or not user.strip() or len(user.strip()) > 50:
        raise ValueError(f"{field.capitalize()} must be between 1 and 50 characters")
    return user.strip()


def _validate_target(target):
    return _validate_identity(target, "contact username")


def _derive_password_verifier(password, salt):
    if not isinstance(password, str) or not 12 <= len(password) <= 255:
        raise ValueError("Password must be between 12 and 255 characters")
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_HASH_ITERATIONS,
        dklen=32,
    )

###############################Functions###############################

#GET A OPEN PORT FROM USER______________________________________________________
def port(timeout= 1, ip='localhost'):
    while True:
        try:
            '''Query User for a port'''

            val = input('Port >')
            port = int(val) if val else 3306
            is_open, status = portstatus(port, timeout, ip)
            print(status)

            if not is_open:
                if input('Unable to connect retry? [y/n] > ') == 'n':
                    print('returning standard 3306')
                    return 3306
                else:
                    continue
            print('\n')
            return port
        except ValueError as e:
            print("Enter numbers only " , e)
#print(port(),rt)

#GET USER NAME FROM USER_________________________________________________________
def uname():
    '''Query User for a '''

    user = None
    while not user:
        user = input("Username: ")
    return user
#print(uname(), rt)

#GET GOST ADDRESS FROM USER_____________________________________________________
def host():
    o = None
    while not o:
        o = input("hostip >")
    return o
#print(host(), rt)

#GET PASSWORD FROM USER_________________________________________________________
def passw():
    o = None
    while not o:
        o = getpass("Password: ")
    return o
#print(passw(), rt)

#RUN SCRIPTS FROM CWD____________________________________________________________________
def sqlscript(sql_script="text_service_schema.sql", json_cfg="DB_METADATA.json"):
    try:
        if not os.path.isabs(sql_script):
            sql_script = os.path.join(os.path.dirname(__file__), sql_script)

        # Only attempt to read metadata and format if a template configuration string is explicitly given
        if json_cfg:
            if not os.path.isabs(json_cfg):
                json_cfg = os.path.join(os.path.dirname(__file__), json_cfg)
            with open(json_cfg, encoding='utf-8') as f:
                cfg = json.load(f)
            with open(sql_script, encoding = 'utf-8') as f:
                script = f.read().format(**cfg)
        else:
            # If json_cfg is None or empty, skip formatting entirely
            with open(sql_script, encoding = 'utf-8') as f:
                script = f.read()

        if "__CLIENT_DB_PASSWORD__" in script:
            password = os.environ.get("TEXTSERVICE_DB_PASSWORD", "")
            if not _DB_PASSWORD_PATTERN.fullmatch(password):
                raise ValueError("A valid TEXTSERVICE_DB_PASSWORD is required to provision the database")
            script = script.replace("__CLIENT_DB_PASSWORD__", password)
        return script

    except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Unable to load SQL script or metadata: {e}")
        return None
#print(sqlscript(), rt)

#SERVER CONNECTION_______________________________________________________________________
def server_connection(t=''):
    while True:
        try:
            h = host()
            p = port(1, h)
            u = uname()
            ps = passw()
            if t == 'text_service' or t == 'text_service_guest':
                config = get_db_config()
                u = config["user"]
                ps = config["password"]
                t = config["database"]

            print('Connect to server-----')

            connect_kwargs = {
                "host": h,
                "port": p,
                "user": u,
                "password": ps
            }
            if t:
                connect_kwargs["database"] = t

            o = mysql.connector.connect(**connect_kwargs)
            print('----------------------')
            if o:
                return o
        except mysql.connector.Error as e:
            print('-----------------------ERROR\n', str(e).rjust(3))
            if input('Retry database connection? [y/n] > ') == 'n':
                return None
        except KeyboardInterrupt as k:
            sys.exit('Exit Signal')
#print(server_connection(), rt)

#GET OPERATIONAL DB CONNECTION FROM CONFIG______________________________________________
def get_conn():
    return mysql.connector.connect(**get_db_config())

#REGISTER NEW PROFILE IN SYSTEM_________________________________________________________
def reg_user(user, phone, pwd):
    user = _validate_identity(user)
    if not isinstance(phone, str) or not phone.strip() or len(phone.strip()) > 20:
        raise ValueError("Phone number must be between 1 and 20 characters")
    if not isinstance(pwd, str) or not 12 <= len(pwd) <= 255:
        raise ValueError("Password must be between 12 and 255 characters")
    phone = phone.strip()
    password_salt = secrets.token_bytes(16)
    password_verifier = _derive_password_verifier(pwd, password_salt)
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.callproc('RegisterUser', [user, phone, password_salt, password_verifier])
        conn.commit()
        print(f" Registered user: {user}")
        return True
    except mysql.connector.Error as err:
        print("Registration failed. Check the submitted details or database availability.")
        return False
    finally:
        try:
            if cursor:
                cursor.close()
        finally:
            if conn:
                conn.close()

#AUTHENTICATE USER AND ACQUIRE ACTIVE SESSION CONTEXT___________________________________
def login(user, pwd):
    user = _validate_identity(user)
    if not isinstance(pwd, str) or not 12 <= len(pwd) <= 255:
        raise ValueError("Password must be between 12 and 255 characters")
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('BeginUserLogin', [user])
        challenge = None
        for res in cursor.stored_results():
            challenge = res.fetchone()

        if not challenge or not challenge.get("password_salt") or not challenge.get("challenge_nonce"):
            raise mysql.connector.Error("Authentication challenge unavailable")

        verifier = _derive_password_verifier(pwd, challenge["password_salt"])
        challenge_response = hashlib.sha256(challenge["challenge_nonce"] + verifier).digest()
        cursor.callproc('CompleteUserLogin', [challenge_response])
        for res in cursor.stored_results():
            row = res.fetchone()
            if row and row.get("status") == "Login Successful!" and row.get("session_token"):
                print(f"🔓 {user} logged in successfully.")
                return conn, cursor, row["session_token"]

        print("Login failed. Check your credentials or database availability.")
        cursor.close()
        conn.close()
        return None, None, None
    except mysql.connector.Error as err:
        print("Login failed. Check your credentials or database availability.")
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        return None, None, None

#TERMINATE LOGGED IN SESSION AND CLOSE ASSETS___________________________________________
def logout(conn, cursor, session_token):
    if not conn:
        return
    try:
        if conn.is_connected():
            cursor.callproc('UserLogout', [session_token])
            conn.commit()
            print("🔒 Logged out successfully.")
    except mysql.connector.Error as err:
        print("Logout could not be confirmed by the database.")
    finally:
        try:
            if cursor:
                cursor.close()
        finally:
            conn.close()

#DISPATCH TEXT MESSAGE INTERACTION OVER SECURED LINE___________________________________
def send_txt(cursor, conn, receiver, text, session_token):
    receiver = _validate_target(receiver)
    if not isinstance(text, str) or not text.strip() or len(text) > 65535:
        raise ValueError("Message must be between 1 and 65,535 characters")
    try:
        cursor.callproc('SendText', [session_token, receiver, text])
        conn.commit()
        return True
    except mysql.connector.Error as err:
        return False

#STREAM EXCHANGE FEED BETWEEN USERS SINCE HISTORICAL POINT______________________________
def stream_txts(cursor, target, timestamp, session_token):
    target = _validate_target(target)
    logs = []
    cursor.callproc('StreamNewTexts', [session_token, target, timestamp])
    for res in cursor.stored_results():
        logs.extend(res.fetchall())
    return logs

#ADD MUTUAL LINK CONTACT RELATION MATRIX________________________________________________
def add_contact(cursor, conn, target, session_token):
    target = _validate_target(target)
    try:
        cursor.callproc('AddContactRelation', [session_token, target])
        conn.commit()
        print(f"🔗 Added {target} to contacts.")
        return True
    except mysql.connector.Error as err:
        print("Could not add contact. The session or database operation was rejected.")
        return False

#SEARCH PUBLIC USERS TO VERIFY PROFILE RECORD___________________________________________
def search_contact(cursor, target, session_token):
    target = _validate_target(target)
    cursor.callproc('SearchContact', [session_token, target])
    for res in cursor.stored_results():
        row = res.fetchone()
        if row:
            return row
    return None

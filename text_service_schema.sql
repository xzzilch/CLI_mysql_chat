CREATE DATABASE IF NOT EXISTS text_service_db;
USE text_service_db;

-- =========================================================================
-- 1. BASE MASTER TABLES & PUBLIC PRESENTATION VIEWS
-- =========================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE DEFAULT NULL, 
    password_salt BINARY(16) NOT NULL,
    password_verifier BINARY(32) NOT NULL,
    status ENUM('ONLINE', 'OFFLINE') DEFAULT 'OFFLINE'
);

CREATE TABLE IF NOT EXISTS login_challenges (
    connection_id BIGINT UNSIGNED PRIMARY KEY,
    user_id INT NULL,
    password_salt BINARY(16) NOT NULL,
    challenge_nonce BINARY(32) NOT NULL,
    expires_at TIMESTAMP(6) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    connection_id BIGINT UNSIGNED PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARBINARY(32) NOT NULL,
    authenticated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE OR REPLACE VIEW public_users AS
SELECT 
    user_id,
    username,
    phone_number,
    status
FROM users;

-- =========================================================================
-- 2. RELATION TABLES (MUTUAL CONTACT LINKS)
-- =========================================================================

CREATE TABLE IF NOT EXISTS contact_relations (
    user1_id INT NOT NULL, 
    user2_id INT NOT NULL,
    PRIMARY KEY (user1_id, user2_id),
    FOREIGN KEY (user1_id) REFERENCES users(user_id), 
    FOREIGN KEY (user2_id) REFERENCES users(user_id),
    CHECK (user1_id < user2_id)
);

-- =========================================================================
-- 3. CHAT LOGGER STORAGE
-- =========================================================================

CREATE TABLE IF NOT EXISTS messages (
    text_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,   
    receiver_id INT NOT NULL, 
    body_text TEXT NOT NULL,                  
    dispatched_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6), 
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id),
    INDEX idx_msg_routing (sender_id, receiver_id, dispatched_at)
);

-- =========================================================================
-- 4. FIREWALL UTILITIES & AUTH PROCEDURES
-- =========================================================================

DROP PROCEDURE IF EXISTS VerifySession;
DELIMITER //
CREATE PROCEDURE VerifySession(IN p_session_token VARBINARY(32))
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    SELECT user_id INTO v_user_id
    FROM auth_sessions
        WHERE connection_id = CONNECTION_ID()
            AND session_token = p_session_token;

    IF v_user_id IS NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Access Denied: Session unauthorized. Please log in first.';
    END IF;
END//
DELIMITER ;

DROP PROCEDURE IF EXISTS RegisterUser;
DELIMITER //
CREATE PROCEDURE RegisterUser(
    IN guest_username VARCHAR(50),
    IN guest_phone_number VARCHAR(20),
    IN guest_password_salt BINARY(16),
    IN guest_password_verifier BINARY(32)
)
SQL SECURITY DEFINER
BEGIN
    INSERT INTO users (username, phone_number, password_salt, password_verifier)
    VALUES (guest_username, guest_phone_number, guest_password_salt, guest_password_verifier);
END//
DELIMITER ;

-- Passwords are checked using a one-use challenge; the plaintext password is never sent to MySQL.
DROP PROCEDURE IF EXISTS UserLogin;
DROP PROCEDURE IF EXISTS BeginUserLogin;
DELIMITER //
CREATE PROCEDURE BeginUserLogin(IN p_username VARCHAR(50))
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    DECLARE v_password_salt BINARY(16) DEFAULT NULL;
    DECLARE v_challenge_nonce BINARY(32) DEFAULT NULL;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_user_id = NULL;

    DELETE FROM auth_sessions WHERE connection_id = CONNECTION_ID();

    SELECT user_id, password_salt
    INTO v_user_id, v_password_salt
    FROM users
    WHERE username = p_username;

    SET v_password_salt = COALESCE(v_password_salt, RANDOM_BYTES(16));
    SET v_challenge_nonce = RANDOM_BYTES(32);
    INSERT INTO login_challenges (connection_id, user_id, password_salt, challenge_nonce, expires_at)
    VALUES (CONNECTION_ID(), v_user_id, v_password_salt, v_challenge_nonce, CURRENT_TIMESTAMP(6) + INTERVAL 60 SECOND)
    ON DUPLICATE KEY UPDATE
        user_id = v_user_id,
        password_salt = v_password_salt,
        challenge_nonce = v_challenge_nonce,
        expires_at = CURRENT_TIMESTAMP(6) + INTERVAL 60 SECOND;

    SELECT v_password_salt AS password_salt, v_challenge_nonce AS challenge_nonce;
END//
DELIMITER ;

DROP PROCEDURE IF EXISTS CompleteUserLogin;
DELIMITER //
CREATE PROCEDURE CompleteUserLogin(IN p_challenge_response BINARY(32))
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    DECLARE v_challenge_nonce BINARY(32) DEFAULT NULL;
    DECLARE v_password_verifier BINARY(32) DEFAULT NULL;
    DECLARE v_expected_response BINARY(32) DEFAULT NULL;
    DECLARE v_session_token VARBINARY(32) DEFAULT NULL;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_user_id = NULL;

    SELECT user_id, challenge_nonce
    INTO v_user_id, v_challenge_nonce
    FROM login_challenges
    WHERE connection_id = CONNECTION_ID()
      AND expires_at > CURRENT_TIMESTAMP(6);

    DELETE FROM login_challenges WHERE connection_id = CONNECTION_ID();

    IF v_user_id IS NOT NULL THEN
        SELECT password_verifier INTO v_password_verifier
        FROM users WHERE user_id = v_user_id;
        SET v_expected_response = UNHEX(SHA2(CONCAT(v_challenge_nonce, v_password_verifier), 256));
    END IF;

    IF v_user_id IS NULL OR NOT (v_expected_response <=> p_challenge_response) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Authentication Failed: Invalid username or password.';
    END IF;

    SET v_session_token = RANDOM_BYTES(32);
    INSERT INTO auth_sessions (connection_id, user_id, session_token)
    VALUES (CONNECTION_ID(), v_user_id, v_session_token)
    ON DUPLICATE KEY UPDATE
        user_id = v_user_id,
        session_token = v_session_token,
        authenticated_at = CURRENT_TIMESTAMP;
    UPDATE users SET status = 'ONLINE' WHERE user_id = v_user_id;
    SELECT 'Login Successful!' AS status, v_session_token AS session_token;
END//
DELIMITER ;

--USER LOGOUT
DROP PROCEDURE IF EXISTS UserLogout;
DELIMITER //
CREATE PROCEDURE UserLogout(IN p_session_token VARBINARY(32))
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    SELECT user_id INTO v_user_id
    FROM auth_sessions
        WHERE connection_id = CONNECTION_ID()
            AND session_token = p_session_token;

    IF v_user_id IS NOT NULL THEN
        UPDATE users SET status = 'OFFLINE' WHERE user_id = v_user_id;
        DELETE FROM auth_sessions WHERE connection_id = CONNECTION_ID();
        SELECT 'Logout Successful!' AS status;
    ELSE
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: You are not logged in.';
    END IF;
END//
DELIMITER ;

-- =========================================================================
-- 5. TEXT SERVICES & APP OPERATIONS (REFACTORED WITH CLEAN FIREWALL)
-- =========================================================================

DROP PROCEDURE IF EXISTS StreamNewTexts;
DELIMITER //
CREATE PROCEDURE StreamNewTexts(
    IN p_session_token VARBINARY(32),
    IN target_contact_username VARCHAR(50),
    IN last_timestamp TIMESTAMP
)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    DECLARE v_target_id INT DEFAULT NULL;
    CALL VerifySession(p_session_token);

    SELECT user_id INTO v_user_id
    FROM auth_sessions
    WHERE connection_id = CONNECTION_ID() AND session_token = p_session_token;
    SELECT user_id INTO v_target_id FROM users WHERE username = target_contact_username;

    SELECT 
        m.text_id,
        u.username AS sender_username,
        m.body_text,
        m.dispatched_at
    FROM messages m
    JOIN users u ON m.sender_id = u.user_id
     WHERE ((m.sender_id = v_user_id AND m.receiver_id = v_target_id)
         OR (m.sender_id = v_target_id AND m.receiver_id = v_user_id))
      AND m.dispatched_at > last_timestamp
    ORDER BY m.dispatched_at ASC;
END//
DELIMITER ;

--SEND TEXT
DROP PROCEDURE IF EXISTS SendText;
DELIMITER //
CREATE PROCEDURE SendText(
    IN p_session_token VARBINARY(32),
    IN input_receiver_username VARCHAR(50),
    IN input_body_text TEXT
)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    DECLARE v_rec_id INT DEFAULT NULL;
    CALL VerifySession(p_session_token);

    SELECT user_id INTO v_user_id
    FROM auth_sessions
    WHERE connection_id = CONNECTION_ID() AND session_token = p_session_token;
    SELECT user_id INTO v_rec_id FROM users WHERE username = input_receiver_username;

    IF v_rec_id IS NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Error: The recipient username does not exist.';
    END IF;

    INSERT INTO messages (sender_id, receiver_id, body_text)
    VALUES (v_user_id, v_rec_id, input_body_text);
END//
DELIMITER ;

--ADD CONTACT
DROP PROCEDURE IF EXISTS AddContactRelation;
DELIMITER //
CREATE PROCEDURE AddContactRelation(
    IN p_session_token VARBINARY(32),
    IN target_username VARCHAR(50)
)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    DECLARE v_target_id INT DEFAULT NULL;
    CALL VerifySession(p_session_token);

    SELECT user_id INTO v_user_id
    FROM auth_sessions
    WHERE connection_id = CONNECTION_ID() AND session_token = p_session_token;
    SELECT user_id INTO v_target_id FROM users WHERE username = target_username;
    
    IF v_target_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Target user does not exist.';
    END IF;

    INSERT IGNORE INTO contact_relations (user1_id, user2_id)
    VALUES (
        LEAST(v_user_id, v_target_id),
        GREATEST(v_user_id, v_target_id)
    );
END//
DELIMITER ;

--
DROP PROCEDURE IF EXISTS GetContactList;
DELIMITER //
CREATE PROCEDURE GetContactList(IN p_session_token VARBINARY(32))
SQL SECURITY DEFINER
BEGIN
    DECLARE v_user_id INT DEFAULT NULL;
    CALL VerifySession(p_session_token);
    SELECT user_id INTO v_user_id
    FROM auth_sessions
    WHERE connection_id = CONNECTION_ID() AND session_token = p_session_token;

    SELECT u.user_id, u.username, u.status
    FROM contact_relations cr
    JOIN users u ON cr.user2_id = u.user_id
    WHERE cr.user1_id = v_user_id
    
    UNION ALL
    
    SELECT u.user_id, u.username, u.status
    FROM contact_relations cr
    JOIN users u ON cr.user1_id = u.user_id
    WHERE cr.user2_id = v_user_id;
END//
DELIMITER ;

--
DROP PROCEDURE IF EXISTS SearchContact;
DELIMITER //
CREATE PROCEDURE SearchContact(
    IN p_session_token VARBINARY(32),
    IN user_name VARCHAR(50)
)
SQL SECURITY DEFINER
BEGIN
    CALL VerifySession(p_session_token);

    SELECT user_id, username, status
    FROM public_users
    WHERE username = user_name;
END//
DELIMITER ;

-- =========================================================================
-- 6. SYSTEM PRIVILEGES & GLOBAL PIPELINE SECURITY
-- =========================================================================

-- Standardise user account setup
CREATE USER IF NOT EXISTS 'client_user'@'%' IDENTIFIED BY '__CLIENT_DB_PASSWORD__';
ALTER USER 'client_user'@'%' IDENTIFIED BY '__CLIENT_DB_PASSWORD__';

-- Clean baseline execution box
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'client_user'@'%';

-- Safely expose execution boundaries only
GRANT EXECUTE ON PROCEDURE text_service_db.RegisterUser TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.BeginUserLogin TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.CompleteUserLogin TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.UserLogout TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.StreamNewTexts TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.SendText TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.AddContactRelation TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.GetContactList TO 'client_user'@'%';
GRANT EXECUTE ON PROCEDURE text_service_db.SearchContact TO 'client_user'@'%';

FLUSH PRIVILEGES;

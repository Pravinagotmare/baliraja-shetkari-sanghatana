CREATE DATABASE IF NOT EXISTS baliraja
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'baliraja_user'@'localhost'
IDENTIFIED BY 'CHANGE_THIS_PASSWORD';

GRANT ALL PRIVILEGES ON baliraja.* TO 'baliraja_user'@'localhost';
FLUSH PRIVILEGES;

USE baliraja;

CREATE TABLE IF NOT EXISTS users(
 id INT AUTO_INCREMENT PRIMARY KEY,
 username VARCHAR(100) UNIQUE NOT NULL,
 password_hash VARCHAR(255) NOT NULL,
 full_name VARCHAR(150) NOT NULL,
 role ENUM('admin','staff') NOT NULL DEFAULT 'staff',
 active TINYINT(1) NOT NULL DEFAULT 1,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS talukas(
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(120) UNIQUE NOT NULL,
 active TINYINT(1) NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS villages(
 id INT AUTO_INCREMENT PRIMARY KEY,
 taluka_id INT NOT NULL,
 name VARCHAR(150) NOT NULL,
 active TINYINT(1) NOT NULL DEFAULT 1,
 UNIQUE KEY uq_village_taluka(name,taluka_id),
 FOREIGN KEY(taluka_id) REFERENCES talukas(id)
);

CREATE TABLE IF NOT EXISTS members(
 id INT AUTO_INCREMENT PRIMARY KEY,
 member_no VARCHAR(30) UNIQUE NOT NULL,
 name VARCHAR(150) NOT NULL,
 mobile VARCHAR(20),
 village_id INT,
 address TEXT,
 identity_info VARCHAR(255),
 photo_path VARCHAR(500),
 registration_date DATE NULL,
 whatsapp_opt_in TINYINT(1) NOT NULL DEFAULT 0,
 active TINYINT(1) NOT NULL DEFAULT 1,
 created_by INT,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(village_id) REFERENCES villages(id),
 FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments(
 id INT AUTO_INCREMENT PRIMARY KEY,
 receipt_no VARCHAR(30) UNIQUE NOT NULL,
 member_id INT NOT NULL,
 payment_type ENUM('Membership Fee','Other Contribution','Donation') NOT NULL,
 amount DECIMAL(12,2) NOT NULL,
 payment_method ENUM('Cash','UPI','Bank') NOT NULL,
 transaction_no VARCHAR(100),
 payment_date DATE NULL,
 note TEXT,
 created_by INT,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(member_id) REFERENCES members(id),
 FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS whatsapp_message_logs(
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 batch_id CHAR(36) NOT NULL,
 member_id INT NULL,
 recipient_phone VARCHAR(20) NOT NULL,
 template_name VARCHAR(100) NOT NULL,
 status ENUM('accepted','failed') NOT NULL,
 provider_message_id VARCHAR(255),
 error_text TEXT,
 sent_by INT,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX idx_whatsapp_batch(batch_id),
 FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE SET NULL,
 FOREIGN KEY(sent_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS settings(
 `key` VARCHAR(100) PRIMARY KEY,
 `value` TEXT
);

CREATE TABLE IF NOT EXISTS cash_book_entries(
 id INT AUTO_INCREMENT PRIMARY KEY,
 entry_type ENUM('Income','Expenditure') NOT NULL,
 category VARCHAR(120) NOT NULL,
 description TEXT,
 amount DECIMAL(12,2) NOT NULL,
 entry_date DATE NOT NULL,
 payment_method ENUM('Cash','UPI','Bank') NOT NULL DEFAULT 'Cash',
 created_by INT,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(created_by) REFERENCES users(id)
);

INSERT IGNORE INTO settings(`key`,`value`) VALUES
('membership_fee','0'),
('upi_id','yourupi@bank'),
('upi_name','बळीराजा शेतकरी संघटना');

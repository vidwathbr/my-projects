create database crypto_currency;
use crypto_currency;

-- User table
CREATE TABLE User (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'standard_user') DEFAULT 'standard_user',  -- Adding role column
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wallet table
CREATE TABLE Wallet (
    wallet_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    balance DECIMAL(18, 8) DEFAULT 0.0,
    currency VARCHAR(10) DEFAULT 'USD',
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

-- Watchlist table
CREATE TABLE Watchlist (
    preference_id INT PRIMARY KEY AUTO_INCREMENT,
    preferred_currency VARCHAR(30) NOT NULL,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

-- Portfolio table
CREATE TABLE Portfolio (
    portfolio_id INT PRIMARY KEY AUTO_INCREMENT,
    portfolio_name VARCHAR(50) NOT NULL,
    total_value DECIMAL(18,2) NOT NULL,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

-- Cryptocurrency table
CREATE TABLE Cryptocurrency (
    crypto_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100)
);

-- Transaction table
CREATE TABLE Transaction (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    portfolio_id INT,
    crypto_id INT,
    quantity DECIMAL(18,8),
    transaction_type ENUM('buy', 'sell'),
    price_at_transaction DECIMAL(18,2),
    total_value DECIMAL(18,2),
    time_of_transaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (portfolio_id) REFERENCES Portfolio(portfolio_id),
    FOREIGN KEY (crypto_id) REFERENCES Cryptocurrency(crypto_id)
);

   ALTER TABLE Transaction
   ADD COLUMN wallet_id INT,
   ADD FOREIGN KEY (wallet_id) REFERENCES Wallet(wallet_id);

-- MarketData table
CREATE TABLE MarketData (
    data_id INT PRIMARY KEY AUTO_INCREMENT,
    crypto_id INT,
    price DECIMAL(18, 8),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crypto_id) REFERENCES Cryptocurrency(crypto_id)
);



-- ***********************************************************************************
-- value insertions

INSERT INTO User (name, email, password) VALUES
('Alice Johnson', 'alice.johnson@example.com', 'password123'),
('Bob Smith', 'bob.smith@example.com', 'password456');

INSERT INTO Wallet (user_id, balance, currency) VALUES
(1, 1000.00, 'USD'),
(2, 1500.00, 'USD');

INSERT INTO Watchlist (preferred_currency, user_id) VALUES
('BTC', 1),
('ETH', 2);

INSERT INTO Portfolio (portfolio_name, total_value, user_id) VALUES
('Alice\'s Crypto Portfolio', 5000.00, 1),
('Bob\'s Investment Portfolio', 7000.00, 2);



INSERT INTO Cryptocurrency (name) VALUES ('Bitcoin'), ('Ethereum'), ('litecoin');

INSERT INTO Transaction (user_id, portfolio_id, crypto_id, quantity, transaction_type, price_at_transaction) VALUES
(1, 1, 1, 0.5, 'buy', 50000.00),
(2, 2, 2, 2.0, 'sell', 1600.00);

INSERT INTO MarketData (crypto_id, price) VALUES
(1, 50000.00),
(2, 1600.00);


-- *******************************************

-- *************************************************


-- Trigger to automatically calculate total_value for new transactions.  
DELIMITER //

CREATE TRIGGER before_transaction_insert
BEFORE INSERT ON Transaction
FOR EACH ROW
BEGIN
    SET NEW.total_value = NEW.quantity * NEW.price_at_transaction;
END//

DELIMITER ;

-- ******************************************************************

DELIMITER //

CREATE TRIGGER update_portfolio_value_after_transaction
AFTER INSERT ON Transaction
FOR EACH ROW
BEGIN
    DECLARE new_total DECIMAL(18,2);
    SET new_total = (SELECT SUM(total_value) FROM Transaction WHERE portfolio_id = NEW.portfolio_id);
    UPDATE Portfolio SET total_value = new_total WHERE portfolio_id = NEW.portfolio_id;
END //

DELIMITER ;

-- *****************************************************************. line no 133
DELIMITER //
CREATE PROCEDURE CreateWallet(IN user_id INT, IN initial_balance DECIMAL(18, 8))
BEGIN
    INSERT INTO Wallet (user_id, balance, currency) VALUES (user_id, initial_balance, 'USD');
END //
DELIMITER ;

-- **********************************************************************

DELIMITER //

-- Procedure to add amount to a wallet. -- 813
CREATE PROCEDURE AddAmountToWallet(IN wallet_id INT, IN amount DECIMAL(18, 8))
BEGIN
    UPDATE Wallet SET balance = balance + amount WHERE wallet_id = wallet_id;
END //

-- Procedure to create a new cryptocurrency.  -- 337
CREATE PROCEDURE CreateCryptocurrency(IN crypto_name VARCHAR(100))
BEGIN
    INSERT INTO Cryptocurrency (name) VALUES (crypto_name);
END //

DELIMITER ;


DELIMITER //






select * from user;
select * from wallet;
select * from portfolio;
select * from Cryptocurrency;
select * from transaction;
select * from marketdata;
select * from watchlist;
DESCRIBE Watchlist;



SHOW COLUMNS FROM Cryptocurrency;



set foreign_key_checks =0;



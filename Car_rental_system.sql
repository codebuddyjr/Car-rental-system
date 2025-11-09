-- ===============================
-- CLEANED: CAR_RENTAL DATABASE SCRIPT
-- ===============================

-- Drop database if exists (idempotent)
DROP DATABASE IF EXISTS Car_Rental;
CREATE DATABASE Car_Rental;
USE Car_Rental;

-- ===============================
-- TABLES
-- ===============================

-- Rental_Location
DROP TABLE IF EXISTS Rental_Location;
CREATE TABLE Rental_Location (
    Rental_Location_ID INT AUTO_INCREMENT,
    Phone VARCHAR(15) UNIQUE NOT NULL,
    Email VARCHAR(50) UNIQUE NOT NULL,
    Street_Name VARCHAR(50) NOT NULL,
    State VARCHAR(30) NOT NULL,
    Zip_Code VARCHAR(10) NOT NULL,
    PRIMARY KEY (Rental_Location_ID)
);

-- Car_Type
DROP TABLE IF EXISTS Car_Type;
CREATE TABLE Car_Type (
    Car_Type VARCHAR(30) NOT NULL,
    Daily_Rate DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (Car_Type)
);

-- Cars
DROP TABLE IF EXISTS Car;
CREATE TABLE Car (
    VIN CHAR(17) PRIMARY KEY,
    Rental_Location_ID INT NOT NULL,
    Reg_No VARCHAR(15) UNIQUE,
    Status VARCHAR(15) NOT NULL,
    Seating_Capacity INT NOT NULL,
    Disability_Friendly CHAR(1),
    Car_Type VARCHAR(30) NOT NULL,
    Model VARCHAR(50),
    Year CHAR(4),
    Color VARCHAR(20),
    FOREIGN KEY (Car_Type) REFERENCES Car_Type(Car_Type) ON DELETE CASCADE,
    FOREIGN KEY (Rental_Location_ID) REFERENCES Rental_Location(Rental_Location_ID) ON DELETE CASCADE
);

-- Insurance_Type
DROP TABLE IF EXISTS Insurance_Type;
CREATE TABLE Insurance_Type (
    Insurance_Type VARCHAR(30) NOT NULL,
    Bodily_Coverage DECIMAL(15,2) NOT NULL,
    Medical_Coverage DECIMAL(15,2) NOT NULL,
    Collision_Coverage DECIMAL(15,2) NOT NULL,
    PRIMARY KEY (Insurance_Type)
);

-- Insurance_Price (M:N)
DROP TABLE IF EXISTS Insurance_Price;
CREATE TABLE Insurance_Price (
    Car_Type VARCHAR(30) NOT NULL,
    Insurance_Type VARCHAR(30) NOT NULL,
    Insurance_Price DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (Car_Type, Insurance_Type),
    FOREIGN KEY (Car_Type) REFERENCES Car_Type(Car_Type) ON DELETE CASCADE,
    FOREIGN KEY (Insurance_Type) REFERENCES Insurance_Type(Insurance_Type) ON DELETE CASCADE
);

-- User
DROP TABLE IF EXISTS User;
CREATE TABLE User (
    License_No VARCHAR(20) NOT NULL,
    FName VARCHAR(30) NOT NULL,
    MName VARCHAR(30),
    LName VARCHAR(30) NOT NULL,
    Email VARCHAR(50) UNIQUE NOT NULL,
    Address VARCHAR(200) NOT NULL,
    DOB DATE NOT NULL,
    User_Type ENUM('Customer','Guest', 'Admin') NOT NULL,
    PRIMARY KEY (License_No)
);

INSERT INTO USER (License_No, FName, LName, Email, Address, DOB, User_Type)VALUES 
('ADMIN001', 'System', 'Admin', 'admin@example.com', 'Admin Office', '1990-01-01', 'Admin');

-- User_Phone (multivalued)
DROP TABLE IF EXISTS User_Phone;
CREATE TABLE User_Phone (
    License_No VARCHAR(20) NOT NULL,
    Phone VARCHAR(15) NOT NULL,
    PRIMARY KEY (License_No, Phone),
    FOREIGN KEY (License_No) REFERENCES User(License_No) ON DELETE CASCADE
);

-- User_Credential
DROP TABLE IF EXISTS User_Credential;
CREATE TABLE User_Credential (
    Login_ID INT AUTO_INCREMENT,
    Password VARCHAR(255) NOT NULL,
    Year_Of_Membership YEAR NOT NULL,
    License_No VARCHAR(20) NOT NULL,
    PRIMARY KEY (Login_ID),
    FOREIGN KEY (License_No) REFERENCES User(License_No) ON DELETE CASCADE
);

INSERT INTO user_credential(License_No, Password, Year_Of_Membership)VALUES 
('ADMIN001', 'admin123', YEAR(CURDATE()));



-- Card_Details
DROP TABLE IF EXISTS Card_Details;
CREATE TABLE Card_Details (
    Card_No BIGINT,
    Login_ID INT NOT NULL,
    Name_on_Card VARCHAR(100) NOT NULL,
    Expiry_Date DATE NOT NULL,
    CVV INT NOT NULL,
    Billing_Address VARCHAR(200) NOT NULL,
    PRIMARY KEY (Card_No),
    FOREIGN KEY (Login_ID) REFERENCES User_Credential(Login_ID) ON DELETE CASCADE
);

-- Reservation
DROP TABLE IF EXISTS Reservation;
CREATE TABLE Reservation (
    Reservation_ID INT AUTO_INCREMENT,
    Start_Date DATE NOT NULL,
    End_Date DATE NOT NULL,
    Meter_Start INT NOT NULL DEFAULT 0,
    Meter_End INT,
    Rental_Amount DECIMAL(12,2) NOT NULL,
    Insurance_Amount DECIMAL(12,2),
    Actual_End_Date DATE,
    Status ENUM('Pending','Confirmed','Cancelled') DEFAULT 'Pending',
    License_No VARCHAR(20) NOT NULL,
    VIN CHAR(17) NOT NULL,
    Additional_Amount DECIMAL(12,2),
    Total_Amount DECIMAL(12,2),
    Insurance_Type VARCHAR(30),
    Penalty_Amount DECIMAL(12,2),
    Drop_Location_ID INT,
    PRIMARY KEY (Reservation_ID),
    FOREIGN KEY (License_No) REFERENCES User(License_No) ON DELETE CASCADE,
    FOREIGN KEY (VIN) REFERENCES Car(VIN) ON DELETE CASCADE,
    FOREIGN KEY (Insurance_Type) REFERENCES Insurance_Type(Insurance_Type)
);

-- Payment
DROP TABLE IF EXISTS Payment;
CREATE TABLE Payment (
    Payment_ID INT AUTO_INCREMENT,
    Amount DECIMAL(12,2) NOT NULL,
    Card_No BIGINT NOT NULL,
    Expiry_Date DATE NOT NULL,
    Name_on_Card VARCHAR(100) NOT NULL,
    CVV INT NOT NULL,
    Billing_Address VARCHAR(200) NOT NULL,
    Paid_By_Cash BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (Payment_ID),
    FOREIGN KEY (Card_No) REFERENCES Card_Details(Card_No) ON DELETE CASCADE
);

-- User_Rents_Car (history M:N)
DROP TABLE IF EXISTS User_Rents_Car;
CREATE TABLE User_Rents_Car (
    License_No VARCHAR(20) NOT NULL,
    VIN CHAR(17) NOT NULL,
    Rent_Date DATE NOT NULL,
    Return_Date DATE,
    PRIMARY KEY (License_No, VIN, Rent_Date),
    FOREIGN KEY (License_No) REFERENCES User(License_No) ON DELETE CASCADE,
    FOREIGN KEY (VIN) REFERENCES Car(VIN) ON DELETE CASCADE
);

-- ===============================
-- FUNCTION: CalculateTotalCost
-- ===============================
DELIMITER $$
DROP FUNCTION IF EXISTS CalculateTotalCost $$
CREATE FUNCTION CalculateTotalCost(
    carType VARCHAR(30),
    insuranceType VARCHAR(30),
    start_d DATE,
    end_d DATE
)
RETURNS DECIMAL(12,2)
DETERMINISTIC
BEGIN
    DECLARE days INT;
    DECLARE daily_rate DECIMAL(10,2) DEFAULT 0.00;
    DECLARE ins_rate DECIMAL(10,2) DEFAULT 0.00;
    DECLARE total DECIMAL(12,2) DEFAULT 0.00;

    -- number of days inclusive
    SET days = GREATEST(DATEDIFF(end_d, start_d) + 1, 0);

    SELECT IFNULL(Daily_Rate,0.00) INTO daily_rate
      FROM Car_Type
      WHERE Car_Type = carType
      LIMIT 1;

    SELECT IFNULL(Insurance_Price,0.00) INTO ins_rate
      FROM Insurance_Price
      WHERE Car_Type = carType
        AND Insurance_Type = insuranceType
      LIMIT 1;

    SET total = days * (daily_rate + ins_rate);
    RETURN total;
END$$
DELIMITER ;

-- ===============================
-- TRIGGERS: Prevent overlapping reservations
-- ===============================
DELIMITER //
DROP TRIGGER IF EXISTS BI_Reservation_NoOverlap //
CREATE TRIGGER BI_Reservation_NoOverlap
BEFORE INSERT ON Reservation
FOR EACH ROW
BEGIN
  IF EXISTS (
    SELECT 1
    FROM Reservation r
    WHERE r.VIN = NEW.VIN
      AND r.Status IN ('Pending','Confirmed')
      AND r.Start_Date <= NEW.End_Date
      AND r.End_Date >= NEW.Start_Date
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Overlapping reservation exists for this car';
  END IF;
END //
DELIMITER ;

DELIMITER //
DROP TRIGGER IF EXISTS BU_Reservation_NoOverlap //
CREATE TRIGGER BU_Reservation_NoOverlap
BEFORE UPDATE ON Reservation
FOR EACH ROW
BEGIN
  IF EXISTS (
    SELECT 1
    FROM Reservation r
    WHERE r.VIN = NEW.VIN
      AND r.Reservation_ID <> OLD.Reservation_ID
      AND r.Status IN ('Pending','Confirmed')
      AND r.Start_Date <= NEW.End_Date
      AND r.End_Date >= NEW.Start_Date
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Overlapping reservation exists for this car';
  END IF;
END //
DELIMITER ;

-- ===============================
-- PROCEDURE: AddReservation (creates Pending reservation)
-- ===============================
DELIMITER //
DROP PROCEDURE IF EXISTS AddReservation //
CREATE PROCEDURE AddReservation(
    IN p_License_No VARCHAR(20),
    IN p_VIN CHAR(17),
    IN p_Start_Date DATE,
    IN p_End_Date DATE,
    IN p_Insurance_Type VARCHAR(30)
)
BEGIN
    DECLARE total_cost DECIMAL(12,2);
    DECLARE rental_amt DECIMAL(12,2);
    DECLARE ins_amt DECIMAL(12,2);

    -- validate dates
    IF p_End_Date < p_Start_Date THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='End date cannot be before start date';
    END IF;

    -- overlap check (redundant with triggers but keeps clear error path)
    IF EXISTS (
      SELECT 1 FROM Reservation r
      WHERE r.VIN = p_VIN
        AND r.Status IN ('Pending','Confirmed')
        AND r.Start_Date <= p_End_Date
        AND r.End_Date >= p_Start_Date
    ) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Car already reserved for selected dates';
    END IF;

    -- calculate amounts
    SET total_cost = CalculateTotalCost(
        (SELECT Car_Type FROM Car WHERE VIN = p_VIN LIMIT 1),
        p_Insurance_Type,
        p_Start_Date,
        p_End_Date
    );

    SET rental_amt = (
      SELECT IFNULL(Daily_Rate,0.00) * (DATEDIFF(p_End_Date, p_Start_Date) + 1)
      FROM Car_Type
      WHERE Car_Type = (SELECT Car_Type FROM Car WHERE VIN = p_VIN LIMIT 1)
      LIMIT 1
    );

    SET ins_amt = (
      SELECT IFNULL(Insurance_Price,0.00) * (DATEDIFF(p_End_Date, p_Start_Date) + 1)
      FROM Insurance_Price
      WHERE Car_Type = (SELECT Car_Type FROM Car WHERE VIN = p_VIN LIMIT 1)
        AND Insurance_Type = p_Insurance_Type
      LIMIT 1
    );

    -- default status Pending
    INSERT INTO Reservation (
        License_No, VIN, Start_Date, End_Date, Meter_Start,
        Rental_Amount, Insurance_Amount, Total_Amount, Insurance_Type, Status
    )
    VALUES (
        p_License_No, p_VIN, p_Start_Date, p_End_Date, 0,
        IFNULL(rental_amt,0.00), IFNULL(ins_amt,0.00), IFNULL(total_cost,0.00), p_Insurance_Type, 'Confirmed'
    );
END //
DELIMITER ;

-- Optional helper: ConfirmReservation procedure (marks Confirmed and blocks car)
DELIMITER //
DROP PROCEDURE IF EXISTS ConfirmReservation //
CREATE PROCEDURE ConfirmReservation(
    IN p_Reservation_ID INT
)
BEGIN
    DECLARE vVIN CHAR(17);
    -- get reservation
    SELECT VIN INTO vVIN FROM Reservation WHERE Reservation_ID = p_Reservation_ID LIMIT 1;
    IF vVIN IS NULL THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Reservation not found';
    END IF;

    -- set to Confirmed
    UPDATE Reservation
    SET Status = 'Confirmed'
    WHERE Reservation_ID = p_Reservation_ID;

    -- block car
    UPDATE Car
    SET Status = 'Unavailable'
    WHERE VIN = vVIN;
END //
DELIMITER ;

-- ===============================
-- EVENT: Release cars after reservation End_Date
-- (runs daily and marks cars Available when reservation ended before today)
-- ===============================
DROP EVENT IF EXISTS release_cars_after_end_date;
DELIMITER $$
CREATE EVENT release_cars_after_end_date
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
  -- Release cars whose confirmed reservations ended before today
  UPDATE Car c
  JOIN Reservation r ON r.VIN = c.VIN
  SET c.Status = 'Available'
  WHERE r.Status = 'Confirmed'
    AND r.End_Date < CURDATE();
END$$
DELIMITER ;

-- Turn on event scheduler if server permits
SET GLOBAL event_scheduler = ON;

-- ===============================
-- SAMPLE DATA (idempotent-friendly inserts)
-- ===============================
-- Rental Locations
INSERT INTO Rental_Location (Phone, Email, Street_Name, State, Zip_Code)
VALUES 
('9876543210', 'blrbranch@rentcar.com', 'MG Road', 'Karnataka', '560001'),
('9876500011', 'hydbranch@rentcar.com', 'Banjara Hills', 'Telangana', '500034');

-- Car Types
INSERT INTO Car_Type (Car_Type, Daily_Rate)
VALUES
('SUV', 3000.00),
('Sedan', 2000.00),
('Hatchback', 1500.00);

-- Cars
INSERT INTO Car (VIN, Rental_Location_ID, Reg_No, Status, Seating_Capacity, Disability_Friendly, Car_Type, Model, Year, Color)
VALUES
('1HGCM82633A123456', 1, 'KA01AB1234', 'Available', 5, 'Y', 'Sedan', 'Honda City', '2022', 'White'),
('1HGCM82633A789012', 1, 'KA01AB5678', 'Available', 7, 'N', 'SUV', 'Toyota Fortuner', '2023', 'Black'),
('1HGCM82633A654321', 2, 'TS08AB9999', 'Available', 5, 'Y', 'Hatchback', 'Maruti Swift', '2021', 'Red');

-- Insurance Types
INSERT INTO Insurance_Type (Insurance_Type, Bodily_Coverage, Medical_Coverage, Collision_Coverage)
VALUES
('Premium', 500000.00, 300000.00, 400000.00),
('Standard', 300000.00, 200000.00, 250000.00),
('Basic', 150000.00, 100000.00, 150000.00);

-- Insurance Prices
INSERT INTO Insurance_Price (Car_Type, Insurance_Type, Insurance_Price)
VALUES
('SUV', 'Premium', 1000.00),
('SUV', 'Standard', 700.00),
('SUV', 'Basic', 500.00),
('Sedan', 'Premium', 900.00),
('Sedan', 'Standard', 600.00),
('Sedan', 'Basic', 400.00),
('Hatchback', 'Premium', 800.00),
('Hatchback', 'Standard', 500.00),
('Hatchback', 'Basic', 300.00);

-- Users


-- User Credentials


-- Reservations using procedure 

-- Payments

select * from reservation;
select * from user;
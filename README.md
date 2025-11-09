# Car Rental System

The Online Car Rental System is a web-based application designed to automate the process of car booking and rental management. The system provides an efficient, secure, and user-friendly platform where customers can browse available cars, make bookings, and manage their rentals online.

Traditionally, car rental operations are handled manually, which makes record-keeping and availability tracking difficult. This project aims to eliminate these challenges by creating a centralized database that stores all relevant details of cars, customers, and bookings.

The system allows two types of users — customers and administrators. Customers can register, search for cars, view details, and book available vehicles. Administrators can add, update, and delete car details, manage bookings, and maintain customer records.

The database ensures consistency, accuracy, and integrity of data using SQL-based constraints, triggers, and relationships. This system not only reduces manual work but also increases transparency and convenience for both customers and rental agencies.

## Setup

1. Create venv and install requirements:
   ```
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   # source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure database in backend/.env (example)
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=Car_Rental
   DB_PORT=3306
   SECRET_KEY=replace_with_secure_key
   ```

3. Run:
   ```
   python app.py
   ```

4. Open http://127.0.0.1:5000 in your browser.

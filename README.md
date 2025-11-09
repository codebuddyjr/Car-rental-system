# Car Rental Web (Flask)

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

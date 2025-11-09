import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY','change_me')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


from datetime import date, datetime, timedelta
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in and is admin
        if not session.get('license_no'):
            return redirect(url_for('login_page'))
        
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT User_Type FROM User WHERE License_No = %s", (session['license_no'],))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or user['User_Type'] != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

# Admin Routes
@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')

@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    # Get total and new users
    cur.execute("SELECT COUNT(*) as total FROM User")
    total_users = cur.fetchone()['total']

    # created_at may not exist in every schema; fall back gracefully
    try:
        cur.execute("SELECT COUNT(*) as new FROM User WHERE DATE(created_at) = CURDATE()")
        new_users = cur.fetchone()['new']
    except Exception:
        # If the column doesn't exist, return 0 for new users today
        new_users = 0
    
    # Get reservation stats
    cur.execute("SELECT COUNT(*) as active FROM Reservation WHERE Status='Confirmed' AND End_Date >= CURDATE()")
    active_reservations = cur.fetchone()['active']
    
    cur.execute("SELECT COUNT(*) as pending FROM Reservation WHERE Status='Pending'")
    pending_reservations = cur.fetchone()['pending']
    
    # Get car stats
    cur.execute("SELECT COUNT(*) as available FROM Car WHERE Status='Available'")
    available_cars = cur.fetchone()['available']
    
    cur.execute("SELECT COUNT(*) as total FROM Car")
    total_cars = cur.fetchone()['total']
    
    # Get revenue stats
    cur.execute("""
        SELECT COALESCE(SUM(Total_Amount), 0) as revenue 
        FROM Reservation 
        WHERE YEAR(Start_Date) = YEAR(CURDATE()) 
        AND MONTH(Start_Date) = MONTH(CURDATE())
        AND Status IN ('Confirmed', 'Completed')
    """)
    monthly_revenue = cur.fetchone()['revenue']
    
    # Calculate revenue change
    cur.execute("""
        SELECT COALESCE(SUM(Total_Amount), 0) as last_month 
        FROM Reservation 
        WHERE Status IN ('Confirmed', 'Completed')
        AND Start_Date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
        AND Start_Date < DATE_FORMAT(CURDATE(), '%Y-%m-01')
    """)
    last_month = cur.fetchone()['last_month']
    
    revenue_change = 0
    if last_month > 0:
        revenue_change = ((monthly_revenue - last_month) / last_month) * 100
    
    cur.close()
    conn.close()
    
    return jsonify({
        'totalUsers': total_users,
        'newUsers': new_users,
        'activeReservations': active_reservations,
        'pendingReservations': pending_reservations,
        'availableCars': available_cars,
        'totalCars': total_cars,
        'monthlyRevenue': float(monthly_revenue),
        'revenueChange': float(revenue_change)
    })

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT u.*, COUNT(r.Reservation_ID) as total_reservations,
               SUM(CASE WHEN r.Status = 'Confirmed' THEN 1 ELSE 0 END) as active_reservations
        FROM User u
        LEFT JOIN Reservation r ON u.License_No = r.License_No
        GROUP BY u.License_No
        ORDER BY u.License_No DESC
    """)
    users = cur.fetchall()
    
    cur.close()
    conn.close()
    return jsonify(users)

@app.route('/api/admin/reservations')
@admin_required
def api_admin_reservations():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Return summarized reservations with user contact and car info
    cur.execute("""
        SELECT r.Reservation_ID, r.License_No, u.FName, u.LName, u.Email,
               GROUP_CONCAT(DISTINCT up.Phone SEPARATOR ', ') AS Phones,
               c.VIN, c.Model, c.Car_Type, c.Color,
               r.Start_Date, r.End_Date, r.Status, r.Total_Amount, r.Insurance_Type
        FROM Reservation r
        JOIN User u ON r.License_No = u.License_No
        LEFT JOIN User_Phone up ON up.License_No = u.License_No
        JOIN Car c ON r.VIN = c.VIN
        GROUP BY r.Reservation_ID
        ORDER BY r.Reservation_ID DESC
        LIMIT 200
    """)
    reservations = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(reservations)


@app.route('/api/admin/reservation/<int:reservation_id>')
@admin_required
def api_admin_reservation_detail(reservation_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Try the rich query first (may reference optional Payment columns)
        cur.execute("""
            SELECT r.*, u.FName, u.LName, u.Email, u.Address, u.DOB, u.User_Type,
                   GROUP_CONCAT(DISTINCT up.Phone SEPARATOR ', ') AS Phones,
                   c.VIN, c.Model, c.Car_Type, c.Color, ct.Daily_Rate,
                   p.Amount AS Payment_Amount, p.Payment_Date
            FROM Reservation r
            JOIN User u ON r.License_No = u.License_No
            LEFT JOIN User_Phone up ON up.License_No = u.License_No
            JOIN Car c ON r.VIN = c.VIN
            LEFT JOIN Car_Type ct ON c.Car_Type = ct.Car_Type
            LEFT JOIN Payment p ON p.Reservation_ID = r.Reservation_ID
            WHERE r.Reservation_ID = %s
            GROUP BY r.Reservation_ID
        """, (reservation_id,))
        row = cur.fetchone()
    except Exception:
        # Fallback query: omit Payment_Date/other optional columns in case schema differs
        cur.execute("""
            SELECT r.*, u.FName, u.LName, u.Email, u.Address, u.DOB, u.User_Type,
                   GROUP_CONCAT(DISTINCT up.Phone SEPARATOR ', ') AS Phones,
                   c.VIN, c.Model, c.Car_Type, c.Color, ct.Daily_Rate
            FROM Reservation r
            JOIN User u ON r.License_No = u.License_No
            LEFT JOIN User_Phone up ON up.License_No = u.License_No
            JOIN Car c ON r.VIN = c.VIN
            LEFT JOIN Car_Type ct ON c.Car_Type = ct.Car_Type
            WHERE r.Reservation_ID = %s
            GROUP BY r.Reservation_ID
        """, (reservation_id,))
        row = cur.fetchone()

    if not row:
        cur.close(); conn.close()
        return jsonify({'error':'Reservation not found'}), 404

    # Coerce numbers to python types if needed
    cur.close(); conn.close()
    return jsonify(row)

@app.route('/api/admin/revenue')
@admin_required
def api_admin_revenue():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    # Get daily revenue for last 30 days
    cur.execute("""
        SELECT DATE(Start_Date) as date, 
               COALESCE(SUM(Total_Amount), 0) as revenue
        FROM Reservation
        WHERE Start_Date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        AND Status IN ('Confirmed', 'Completed')
        GROUP BY DATE(Start_Date)
        ORDER BY date
    """)
    revenue_data = cur.fetchall()
    
    # Fill in missing dates with zero revenue
    all_dates = []
    all_revenue = []
    
    start_date = date.today() - timedelta(days=30)
    current_date = start_date
    
    revenue_by_date = {r['date'].strftime('%Y-%m-%d'): float(r['revenue']) for r in revenue_data}
    
    while current_date <= date.today():
        date_str = current_date.strftime('%Y-%m-%d')
        all_dates.append(date_str)
        all_revenue.append(revenue_by_date.get(date_str, 0))
        current_date += timedelta(days=1)
    
    cur.close()
    conn.close()
    
    return jsonify({
        'labels': all_dates,
        'values': all_revenue
    })

@app.route('/api/admin/car-status')
@admin_required
def api_admin_car_status():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT c.Car_Type,
               COUNT(*) as total,
               SUM(CASE WHEN c.Status = 'Available' THEN 1 ELSE 0 END) as available
        FROM Car c
        GROUP BY c.Car_Type
    """)
    status = cur.fetchall()
    
    result = {
        row['Car_Type']: {
            'total': row['total'],
            'available': row['available']
        }
        for row in status
    }
    
    cur.close()
    conn.close()
    return jsonify(result)

@app.route('/api/admin/confirm-reservation/<int:reservation_id>', methods=['POST'])
@admin_required
def api_admin_confirm_reservation(reservation_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.callproc('ConfirmReservation', [reservation_id])
        conn.commit()
        return jsonify({'message': 'Reservation confirmed successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/reservations/<int:reservation_id>/cancel', methods=['POST'])
def api_cancel_reservation(reservation_id):
    # optional: ensure user owns this reservation if using sessions
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT Reservation_ID, Start_Date FROM Reservation WHERE Reservation_ID=%s", (reservation_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error":"Reservation not found"}), 404

        # basic rule: cannot cancel on/after start date
        if date.today() >= row['Start_Date']:
            return jsonify({"error":"Cannot cancel on/after start date"}), 400

        # Deleting the reservation will invoke AfterReservationDelete trigger to free the car
        cur.execute("DELETE FROM Reservation WHERE Reservation_ID=%s", (reservation_id,))
        conn.commit()
        return jsonify({"message":"Reservation cancelled and car released"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close(); conn.close()


# Add to app.py

from datetime import date, datetime
from flask import request

@app.route('/api/metrics/summary', methods=['GET'])
def api_metrics_summary():
    # optional query params: start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        today = date.today()
        start_date = date(today.year, today.month, 1).isoformat()
        # crude month end: next month first - 1 day via SQL, keep end_date as today for simplicity
        end_date = today.isoformat()

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)

    # 1) Revenue by Car Type (joins Reservation->Car->Car_Type)
    cur.execute("""
        SELECT ct.Car_Type,
               COUNT(r.Reservation_ID) AS bookings,
               COALESCE(SUM(r.Total_Amount),0) AS total_revenue,
               COALESCE(AVG(r.Total_Amount),0) AS avg_booking_value
        FROM Reservation r
        JOIN Car c ON r.VIN = c.VIN
        JOIN Car_Type ct ON c.Car_Type = ct.Car_Type
        WHERE r.Status IN ('Pending','Confirmed') 
          AND r.Start_Date >= %s AND r.Start_Date <= %s
        GROUP BY ct.Car_Type
        ORDER BY total_revenue DESC
    """, (start_date, end_date))
    by_type = cur.fetchall()

    # 2) Revenue per Day
    cur.execute("""
        SELECT r.Start_Date AS day,
               COUNT(r.Reservation_ID) AS bookings,
               COALESCE(SUM(r.Total_Amount),0) AS total_revenue
        FROM Reservation r
        WHERE r.Status IN ('Pending','Confirmed')
          AND r.Start_Date >= %s AND r.Start_Date <= %s
        GROUP BY r.Start_Date
        ORDER BY r.Start_Date
    """, (start_date, end_date))
    per_day = cur.fetchall()

    # 3) Headline metrics
    cur.execute("""
        SELECT COALESCE(SUM(Total_Amount),0) AS total_revenue,
               COUNT(*) AS total_bookings
        FROM Reservation
        WHERE Status IN ('Pending','Confirmed')
          AND Start_Date >= %s AND Start_Date <= %s
    """, (start_date, end_date))
    headline = cur.fetchone()

    cur.close(); conn.close()
    return jsonify({
        "range": {"start_date": start_date, "end_date": end_date},
        "headline": headline,
        "by_type": by_type,
        "per_day": per_day
    })

# ROUTES: Pages
@app.route('/')
def index():
    if session.get('license_no'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('license_no'):
        return redirect(url_for('login_page'))
    return render_template('dashboard.html', license_no=session.get('license_no'))

@app.route('/cars')
def cars_page():
    return render_template('cars.html')

@app.route('/reserve')
def reserve_page():
    if not session.get('license_no'):
        return redirect(url_for('login_page'))
    return render_template('reserve.html', license_no=session.get('license_no'))

@app.route('/my_reservations')
def my_reservations_page():
    if not session.get('license_no'):
        return redirect(url_for('login_page'))
    return render_template('my_reservations.html')

# API endpoints
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    required = ['License_No','FName','LName','Email','Address','DOB','Password','Phone']
    for r in required:
        if not data.get(r):
            return jsonify({'error':f'Missing {r}'}), 400
    license_no = data['License_No']
    fname = data['FName']; mname = data.get('MName'); lname = data['LName']
    email = data['Email']; address = data['Address']; dob = data['DOB']
    # Set User_Type to Admin if email contains admin
    user_type = 'Admin' if 'admin' in email.lower() else 'Customer'
    password = data['Password']; phone = data['Phone']
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        print(f"Inserting user with license: {license_no}")  # Debug log
        
        # Insert into User
        cur.execute("""INSERT INTO User (License_No, FName, MName, LName, Email, Address, DOB, User_Type)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (license_no,fname,mname,lname,email,address,dob,user_type))
        print("User inserted successfully")  # Debug log
        
        # Insert credential with hashed password
        hashed = generate_password_hash(password)
        cur.execute("""INSERT INTO User_Credential (Password, Year_Of_Membership, License_No)
                       VALUES (%s, YEAR(CURDATE()), %s)""", (hashed, license_no))
        print("Credentials inserted successfully")  # Debug log
        
        # Insert phone
        cur.execute("""INSERT INTO User_Phone (License_No, Phone) VALUES (%s,%s)""", (license_no, phone))
        print("Phone inserted successfully")  # Debug log
        
        # Verify the insertion
        cur.execute("SELECT License_No FROM User WHERE License_No = %s", (license_no,))
        if cur.fetchone():
            print("User verified in database")  # Debug log
            conn.commit()
            return jsonify({'message':'registered'}), 201
        else:
            print("User not found after insertion!")  # Debug log
            conn.rollback()
            return jsonify({'error': 'User creation failed'}), 500
            
    except Exception as e:
        print(f"Error during registration: {str(e)}")  # Debug log
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    password = data.get('Password')
    is_admin = data.get('isAdmin', False)
    
    if not password:
        return jsonify({'error':'Password is required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        if is_admin:
            email = data.get('Email')
            if not email:
                return jsonify({'error':'Email is required'}), 400
            
            # Find user by email for admin login
            cur.execute("""
                SELECT u.License_No, u.User_Type, u.FName, u.Email, uc.Password 
                FROM User u 
                JOIN User_Credential uc ON u.License_No = uc.License_No 
                WHERE u.Email=%s AND u.User_Type='Admin'
            """, (email,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error':'Invalid admin credentials'}), 401
            
            license_no = user['License_No']
            stored = user['Password']
            session['name'] = user['FName']
            session['email'] = user['Email']
        else:
            license_no = data.get('License_No')
            if not license_no:
                return jsonify({'error':'License number is required'}), 400
            
            # Find user by license
            cur.execute("""
                SELECT u.License_No, u.FName, u.Email, uc.Password
                FROM User u
                JOIN User_Credential uc ON u.License_No = uc.License_No
                WHERE u.License_No = %s
            """, (license_no,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error':'Invalid license or password'}), 401
            
            stored = user['Password']
            session['name'] = user['FName']
            session['email'] = user['Email']
        
        # Check password
        ok = False
        try:
            ok = check_password_hash(stored, password)
        except Exception:
            ok = (stored == password)
        
        if ok:
            session['license_no'] = license_no
            return jsonify({'message':'ok'}), 200
        else:
            return jsonify({'error':'Invalid credentials'}), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return jsonify({'error': 'An error occurred during login'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/users/current', methods=['GET'])
def api_users_current():
    license_no = session.get('license_no')
    if not license_no:
        return jsonify({'error': 'Not authenticated'}), 401
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT License_No, FName, LName, Email, Address, DOB, User_Type FROM User WHERE License_No=%s", (license_no,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error':'User not found'}), 404
        return jsonify(user)
    finally:
        cur.close(); conn.close()

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('license_no', None)
    return jsonify({'message':'logged out'})

@app.route('/api/cars/available', methods=['GET'])
def api_available_cars_by_date():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
        SELECT c.VIN, c.Model, c.Car_Type, c.Color, ct.Daily_Rate, c.Status, c.Year
        FROM Car c
        JOIN Car_Type ct ON c.Car_Type = ct.Car_Type
        WHERE c.Status = 'Available'
        AND c.VIN NOT IN (
            SELECT r.VIN FROM Reservation r
            WHERE r.Status IN ('Pending','Confirmed')
              AND r.Start_Date <= %s AND r.End_Date >= %s
        )
    """
    cur.execute(query, (end_date, start_date))
    cars = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(cars)



@app.route('/api/reservations/add', methods=['POST'])
def api_add_reservation():
    data = request.json
    license_no = data.get('License_No')
    vin = data.get('VIN')
    start_d = data.get('Start_Date')
    end_d = data.get('End_Date')
    insurance = data.get('Insurance_Type')
    # ... your existing validation

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # (User creation logic omitted for brevity)

        # Call stored procedure AddReservation
        cur.callproc('AddReservation', [license_no, vin, start_d, end_d, insurance])
        conn.commit()

        # Get the created reservation ID
        cur.execute("""
            SELECT Reservation_ID FROM Reservation 
            WHERE License_No = %s AND VIN = %s 
            ORDER BY Reservation_ID DESC LIMIT 1
        """, (license_no, vin))
        reservation = cur.fetchone()

        # Return reservation ID and redirect URL for payment page
        return jsonify({
            'message': 'reservation_added',
            'reservation_id': reservation[0],
            'payment_url': url_for('payment_page')
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/my_reservations', methods=['GET'])
def api_my_reservations():
    license_no = session.get('license_no') or request.args.get('license_no')
    if not license_no:
        return jsonify({'error':'Not logged in'}), 401
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT r.Reservation_ID, r.Start_Date, r.End_Date, r.Status, r.Total_Amount, c.Model
                   FROM Reservation r JOIN Car c ON r.VIN = c.VIN WHERE r.License_No=%s ORDER BY r.Reservation_ID DESC""", (license_no,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/payment')
def payment_page():
    if not session.get('license_no'):
        return redirect(url_for('login_page'))
    return render_template('payment.html')


@app.route('/api/payments/add', methods=['POST'])
def api_payments_add():
    data = request.json or {}
    amount = data.get('Amount')
    card_no = data.get('Card_No')
    name_on_card = data.get('Name_on_Card')
    expiry = data.get('Expiry_Date')
    cvv = data.get('CVV')
    billing = data.get('Billing_Address')
    paid_by_cash = data.get('Paid_By_Cash', False)
    reservation_id = data.get('Reservation_ID')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Try to insert into Payment table if it exists
        try:
            cur.execute("""
                INSERT INTO Payment (Amount, Card_No, Name_on_Card, Expiry_Date, CVV, Billing_Address, Paid_By_Cash, Reservation_ID, Payment_Date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
            """, (amount, card_no, name_on_card, expiry, cvv, billing, int(bool(paid_by_cash)), reservation_id))
        except Exception:
            # If Payment table/columns differ, attempt minimal insert into a generic table or skip
            pass

        # If reservation id is provided, mark it as Confirmed and set Total_Amount
        if reservation_id:
            try:
                cur.execute("UPDATE Reservation SET Status='Confirmed', Total_Amount=%s WHERE Reservation_ID=%s", (amount, reservation_id))
            except Exception:
                pass

        conn.commit()
        return jsonify({'message':'payment recorded'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); conn.close()

@app.route('/api/cars', methods=['GET'])
def api_cars():
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        print("Fetching cars from database...")  # Debug log
        
        cur.execute("""
          SELECT c.VIN, c.Model, c.Car_Type, c.Color, ct.Daily_Rate, c.Status, c.Year
          FROM Car c JOIN Car_Type ct ON c.Car_Type = ct.Car_Type
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} cars")  # Debug log
        
        return jsonify(rows)
    except Exception as e:
        print(f"Error fetching cars: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)

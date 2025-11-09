from flask import Blueprint, request, jsonify
from db import get_db_connection

reservation_bp = Blueprint('reservation_bp', __name__, url_prefix='/api/reservations')

@reservation_bp.route('/all', methods=['GET'])
def get_reservations():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.Reservation_ID, r.Start_Date, r.End_Date, r.Status, r.Total_Amount,
               r.License_No, u.FName, u.LName, r.VIN, c.Model
        FROM Reservation r
        LEFT JOIN User u ON r.License_No = u.License_No
        LEFT JOIN Car c ON r.VIN = c.VIN
        ORDER BY r.Reservation_ID DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)

@reservation_bp.route('/add', methods=['POST'])
def add_reservation():
    data = request.get_json()
    required = ['License_No','VIN','Start_Date','End_Date','Insurance_Type']
    for r in required:
        if r not in data:
            return jsonify({'error': f'Missing {r}'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    # Call stored procedure AddReservation
    cur.callproc('AddReservation', [
        data['License_No'],
        data['VIN'],
        data['Start_Date'],
        data['End_Date'],
        data['Insurance_Type']
    ])
    conn.commit()
    conn.close()
    return jsonify({'message':'Reservation added successfully'})

@reservation_bp.route('/<int:res_id>/cancel', methods=['PUT'])
def cancel_reservation(res_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE Reservation SET Status='Cancelled' WHERE Reservation_ID=%s", (res_id,))
    conn.commit()
    conn.close()
    return jsonify({'message':'Reservation cancelled'})

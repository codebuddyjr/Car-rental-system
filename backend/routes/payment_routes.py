from flask import Blueprint, request, jsonify
from db import get_db_connection

payment_bp = Blueprint('payment_bp', __name__, url_prefix='/api/payments')

@payment_bp.route('/all', methods=['GET'])
def get_payments():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Payment")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)

@payment_bp.route('/add', methods=['POST'])
def add_payment():
    data = request.get_json()
    fields = ['Amount','Card_No','Expiry_Date','Name_on_Card','CVV','Billing_Address','Paid_By_Cash']
    for f in fields:
        if f not in data:
            return jsonify({'error':f'Missing {f}'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Payment (Amount, Card_No, Expiry_Date, Name_on_Card, CVV, Billing_Address, Paid_By_Cash)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        data['Amount'],
        data['Card_No'],
        data['Expiry_Date'],
        data['Name_on_Card'],
        data['CVV'],
        data['Billing_Address'],
        int(bool(data['Paid_By_Cash']))
    ))
    conn.commit()
    conn.close()
    return jsonify({'message':'Payment recorded'})

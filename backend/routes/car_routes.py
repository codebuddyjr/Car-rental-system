from flask import Blueprint, jsonify, request
from db import get_db_connection

car_bp = Blueprint('car_bp', __name__, url_prefix='/api/cars')

@car_bp.route('/available', methods=['GET'])
def get_available_cars():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT VIN, Model, Car_Type, Year, Color, Seating_Capacity, Status FROM Car WHERE Status='Available'")
    cars = cur.fetchall()
    conn.close()
    return jsonify(cars)

@car_bp.route('/all', methods=['GET'])
def get_all_cars():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Car")
    cars = cur.fetchall()
    conn.close()
    return jsonify(cars)

@car_bp.route('/<vin>/status', methods=['PUT'])
def update_status(vin):
    data = request.get_json()
    status = data.get('Status')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE Car SET Status=%s WHERE VIN=%s", (status, vin))
    conn.commit()
    conn.close()
    return jsonify({"message":"Status updated"})

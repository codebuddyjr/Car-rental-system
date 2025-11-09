from flask import Blueprint, jsonify, request
from db import get_db_connection

user_bp = Blueprint('user_bp', __name__, url_prefix='/api/users')

@user_bp.route('/all', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT License_No, FName, MName, LName, Email, Address, DOB, User_Type FROM User")
    users = cur.fetchall()
    conn.close()
    return jsonify(users)

@user_bp.route('/add', methods=['POST'])
def add_user():
    data = request.get_json()
    fields = ['License_No','FName','LName','Email','Address','DOB','User_Type']
    for f in fields:
        if f not in data:
            return jsonify({'error':f'Missing {f}'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO User (License_No, FName, MName, LName, Email, Address, DOB, User_Type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data.get('License_No'),
        data.get('FName'),
        data.get('MName'),
        data.get('LName'),
        data.get('Email'),
        data.get('Address'),
        data.get('DOB'),
        data.get('User_Type')
    ))
    conn.commit()
    conn.close()
    return jsonify({'message':'User added'})


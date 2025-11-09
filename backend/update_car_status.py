from db import get_db_connection

def update_car_status_after_reservation():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        update_query = """
            UPDATE Car c
            JOIN Reservation r ON c.VIN = r.VIN
            SET c.Status = 'Available'
            WHERE r.Status = 'Confirmed' AND r.End_Date < CURDATE()
        """
        cur.execute(update_query)
        conn.commit()
        print(f"{cur.rowcount} cars updated to 'Available'")
    except Exception as e:
        print("Error updating car status:", e)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    update_car_status_after_reservation()

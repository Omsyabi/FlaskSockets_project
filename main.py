from flask import Flask, render_template, request, url_for, redirect,session, jsonify
from flask_socketio import SocketIO
from decimal import Decimal
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = "mamamo123"
socketio = SocketIO(app, cors_allowed_origins="*")

connection = pymysql.connect(
    host="127.0.0.1",
    port=3307, 
    user="root",
    password="Burgerkasakin11",
    database="payments",
    cursorclass=pymysql.cursors.DictCursor 
)

cursor = connection.cursor()

def get_website_name():
    cursor.execute("SELECT website_name FROM settings WHERE id_settings = 1")
    result = cursor.fetchone()
    return result['website_name'] if result else "Default Boarding House"

def update_website_name(new_name):
    cursor.execute("UPDATE settings SET website_name=%s WHERE id_settings=1", (new_name,))
    connection.commit()

@app.context_processor
def inject_settings():
    return dict(website_name=get_website_name())

@socketio.event
def connect(sid):
    print(f"Connected : {request.sid}")
    
@socketio.event
def disconnect(sid):
    print(f"Disconnected : {sid}")

#Arduinoroute
@app.route('/fire_event', methods=['POST'])
def fire_event():
    data = request.get_json()
    if data and data.get("status") == "FIRE":
        print("🔥 Fire detected from Arduino!")
        socketio.emit("sensor_update", data)  # broadcast to all clients
        return jsonify({"message": "Fire alert received"}), 200
    return jsonify({"message": "No fire"}), 200

#Login
@app.route("/")
def login_page():
    return render_template("index.html")



@app.route("/login", methods=["POST"])
def login_handler():
    user = request.form.get("userinp")
    password = request.form.get("passinp")
    
    sql = "SELECT * FROM account WHERE account_username=%s AND account_password=%s"
    cursor.execute(sql, (user, password))
    account_found = cursor.fetchone()

    if account_found:
        session['account_logged_in'] = True
        session['account_name'] = account_found['account_name']
        session['account_username'] = account_found['account_username']
        return redirect(url_for('dash_page'))
    else:
        return redirect(url_for('login_page'))
    
@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if not session.get("account_logged_in"):
        return redirect(url_for("login_page"))

    if request.method == "POST":
        new_name = request.form["website_name"]
        update_website_name(new_name)
        return redirect(url_for("dash_page"))

    current_name = get_website_name()
    return render_template("admin_settings.html", website_name=current_name)


# Register endpoint
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    room_number = data.get("roomNumber")

    if not username or not password:
        return jsonify({"status": "error", "message": "Missing fields"})

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password, email, room_number) VALUES (%s, %s, %s, %s)",
                (username, password, email, room_number)
            )
        connection.commit()
        return jsonify({"status": "success", "message": "Account created"})
    except Exception as e:
        return jsonify({"status": "error", "message": "Username already exists"})


# Login endpoint
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM account WHERE account_username=%s AND account_password=%s", (username, password))
        user = cursor.fetchone()

    if not user:
        return jsonify({"status": "error", "message": "Invalid username or password"})
    else:
        return jsonify({"status": "success", "message": "Login successful", "user": user})


@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/register_account", methods=["POST"])
def register_handler():
    username = request.form.get("userinp")
    password = request.form.get("passinp")

    # Check if username already exists
    check_sql = "SELECT * FROM account WHERE account_username=%s"
    cursor.execute(check_sql, (username,))
    existing = cursor.fetchone()

    if existing:
        return "Username already exists"

    # Insert new account
    sql = "INSERT INTO account (account_username, account_password) VALUES (%s, %s)"
    cursor.execute(sql, (username, password))
    connection.commit()

    return redirect(url_for('login_page'))



#Dashboard
@app.route("/dashboard")
def dash_page():

    if not session.get("account_logged_in"):
        return redirect(url_for("login_page"))

    username = session.get("account_username")

    # check if account still exists
    cursor.execute("SELECT * FROM account WHERE account_username=%s", (username,))
    account = cursor.fetchone()

    if not account:
        session.clear()  # user deleted from database
        return redirect(url_for("login_page"))

    return render_template(
        "dashboard.html",
        username=account['account_name'],
        email=account['account_username']
    )
    
#Tenant Section
@app.route("/tenants")
def tenant_page():
    return render_template("infotenants.html")

@app.route("/api/tenants")
def api_get_tenants():
    cursor.execute("""
        SELECT tenant_id, fullname, age, gender, room_number, room_price, contact_no
        FROM tenant_info
    """)
    tenants = cursor.fetchall()
    return jsonify({"tenants": tenants})


@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    try:
        with connection.cursor() as cursor:
            # Get all tenants
            cursor.execute("SELECT tenant_id, fullname, age, gender, room_number, room_price, contact_no, date_occupied FROM tenant_info")
            tenants = cursor.fetchall()

        # Map tenants by room_number
        tenant_by_room = {str(t["room_number"]): t for t in tenants}

        rooms = []
        # Example: 25 rooms total
        for i in range(1, 26):
            room_number = str(i)
            tenant = tenant_by_room.get(room_number)

            rooms.append({
                "room_number": room_number,
                "status": "occupied" if tenant else "available",
                "tenant": tenant if tenant else None
            })

        return jsonify({"status": "success", "rooms": rooms})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})





@app.route("/add_tenants", methods=["POST", "GET"])
def add_tenants():
    if request.method == "POST":
        fullname = request.form["fullname"]
        age = request.form["age"]
        gender = request.form["gender"]
        address = request.form["address"]
        contactno = request.form["contact_no"]
        roomno = request.form["room_number"]
        price = request.form["room_price"]
        dateoccupied = request.form["date_occupied"]

        sql = """INSERT INTO tenant_info 
                (fullname,
                age,
                gender,
                address,
                contact_no,
                room_number,
                room_price,
                date_occupied)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
        cursor.execute(sql, (fullname, age, gender, address, contactno, roomno, price, dateoccupied))
        connection.commit()
        return redirect(url_for('save_tenants'))

    return render_template("addtenants.html")

@app.route("/tenants_info")
def save_tenants():
    sql = """SELECT * FROM tenant_info"""
    cursor.execute(sql)
    result = cursor.fetchall()
    return render_template("infotenants.html", std=result)

@app.route('/edit_tenant/<int:tenant_id>', methods=["GET", "POST"])
def edit_tenant(tenant_id):
    if request.method == "POST":
        fullname = request.form["fullname"]
        age = request.form["age"]
        gender = request.form["gender"]
        address = request.form["address"]
        contactno = request.form["contact_no"]
        roomno = request.form["room_number"]
        price = request.form["room_price"]
        dateoccupied = request.form["date_occupied"]
        
        cursor.execute("""UPDATE tenant_info SET
            fullname=%s,
            age=%s,
            gender=%s,
            address=%s,
            contact_no=%s,
            room_number=%s,
            room_price=%s,
            date_occupied=%s
            WHERE tenant_id=%s
        """, (fullname, age, gender, address, contactno, roomno, price, dateoccupied, tenant_id))
        connection.commit()

        return redirect(url_for('save_tenants')) 

    cursor.execute("SELECT * FROM tenant_info WHERE tenant_id = %s", (tenant_id,))
    tenant = cursor.fetchone()

    if tenant:
        return render_template("edit_tenant.html", tenant=tenant)
    else:
        return "Tenant not found", 404
    
@app.route('/edit_tenantpay/<int:tenant_id>', methods=["GET", "POST"])
def edit_tenantpay(tenant_id):
    if request.method == "POST":
        fullname = request.form["fullname"]
        roomno = request.form["room_number"]
        price = request.form["room_price"]
        dateoccupied = request.form["date_occupied"]
        
        cursor.execute("""UPDATE tenant_info SET
            fullname=%s,
            room_number=%s,
            room_price=%s,
            date_occupied=%s
            WHERE tenant_id=%s
        """, (fullname, roomno, price, dateoccupied, tenant_id))
        connection.commit()
        
        return redirect(url_for('save_tenants')) 

    cursor.execute("SELECT * FROM tenant_info WHERE tenant_id = %s", (tenant_id,))
    tenant = cursor.fetchone()

    if tenant:
        return render_template("edit_tenantpay.html", tenant=tenant)
    else:
        return "Tenant not found", 404



@app.route('/delete_tenant/<int:tenant_id>')
def delete_tenant(tenant_id):
    cursor.execute("DELETE FROM tenant_info WHERE tenant_id = %s", (tenant_id,))
    connection.commit()
    return redirect(url_for('save_tenants'))





#Rooms
@app.route("/rooms")
def room_page():
    # Get all tenants from DB
    cursor.execute("SELECT * FROM tenant_info")
    tenants = cursor.fetchall()

    # Fixed range of rooms (1–24)
    room_numbers = range(1, 25)

    rooms = []
    for i in room_numbers:
        # Find tenant for this room number
        tenant = next((t for t in tenants if str(t['room_number']) == str(i)), None)
        status = "occupied" if tenant else "available"

        rooms.append({
            "room_number": str(i),
            "status": status,
            "tenant": tenant
        })

    return render_template("roomshowinfo.html", rooms=rooms)




@app.route("/edit_room", methods=["POST"])
def edit_room():
    old_room_number = request.form.get("old_room_number")
    new_room_number = request.form.get("new_room_number")

    cursor.execute("""
        UPDATE tenant_info
        SET room_number = %s
        WHERE room_number = %s
    """, (new_room_number, old_room_number))
    connection.commit()

    return redirect(url_for("room_page"))





# Payments
@app.route("/payments")
def payment_page():
    sql = """
        SELECT payments.payment_id,
        payments.payment_date,
        payments.payment_amount,
        payments.payment_status,
        tenant_info.tenant_id,
        tenant_info.fullname,
        tenant_info.room_number,
        tenant_info.room_price,
        tenant_info.date_occupied
        FROM payments
        JOIN tenant_info ON payments.tenant_id = tenant_info.tenant_id
        ORDER BY payments.payment_date DESC
    """
    cursor.execute(sql)
    result = cursor.fetchall()

    cursor.execute("SELECT tenant_id, fullname, room_number, room_price FROM tenant_info")
    tenants = cursor.fetchall()

    tenant_balances = {}

    for tenant in tenants:
        cursor.execute(
            "SELECT SUM(payment_amount) AS total_paid FROM payments WHERE tenant_id = %s",
            (tenant['tenant_id'],)
        )
        total_paid_row = cursor.fetchone()

        total_paid = Decimal(total_paid_row['total_paid'] or 0)
        room_price = Decimal(tenant['room_price'])

        if total_paid > room_price:
            remaining_balance = 0
            overpaid = float(total_paid - room_price)
            status = "OVERPAID"

        elif total_paid == room_price:
            remaining_balance = 0
            overpaid = 0
            status = "PAID"

        else:
            remaining_balance = float(room_price - total_paid)
            overpaid = 0
            status = "PENDING"

        tenant_balances[tenant['tenant_id']] = {
            "total_paid": float(total_paid),
            "remaining_balance": remaining_balance,
            "overpaid": overpaid,
            "status": status
        }

    return render_template(
        "payments.html",
        std=result,
        tenants=tenants,
        tenant_balances=tenant_balances
    )
    
@app.route("/api/payment_table", methods=["GET"])
def get_payment_table():
    cursor.execute("SELECT tenant_id, fullname, room_number, room_price FROM tenant_info")
    tenants = cursor.fetchall()

    table_data = []
    for tenant in tenants:
        # Get total paid for this tenant
        cursor.execute(
            "SELECT SUM(payment_amount) AS total_paid FROM payments WHERE tenant_id = %s",
            (tenant['tenant_id'],)
        )
        total_paid_row = cursor.fetchone()
        total_paid = Decimal(total_paid_row['total_paid'] or 0)
        room_price = Decimal(tenant['room_price'])

        if total_paid > room_price:
            remaining_balance = 0
            overpaid = float(total_paid - room_price)
            status = "OVERPAID"
        elif total_paid == room_price:
            remaining_balance = 0
            overpaid = 0
            status = "PAID"
        else:
            remaining_balance = float(room_price - total_paid)
            overpaid = 0
            status = "PENDING"

        table_data.append({
            "tenant_id": tenant['tenant_id'],
            "fullname": tenant['fullname'],
            "room_number": tenant['room_number'],
            "room_price": float(room_price),
            "total_paid": float(total_paid),
            "remaining_balance": remaining_balance,
            "overpaid": overpaid,
            "status": status
        })

    return jsonify({"payments": table_data})

    
@app.route("/addpayments", methods=["POST"])
def addpayments():
    tenant_id = request.form.get("tenant_id")
    payment_date = request.form.get("payment_date")
    payment_amount = request.form.get("payment_amount")

    # ✅ Insert only the columns that exist in payments
    cursor.execute(
        "INSERT INTO payments (tenant_id, payment_date, payment_amount, payment_status) "
        "VALUES (%s, %s, %s, %s)",
        (tenant_id, payment_date, payment_amount, "Paid")
    )
    connection.commit()

    return redirect(url_for("payment_page"))







@app.route("/api/payments", methods=["GET"])
def get_payments():
    tenant_id = request.args.get("tenant_id")
    try:
        cursor = connection.cursor()
        if tenant_id:
            # Get all payments for this tenant
            cursor.execute("""
                SELECT payment_id, tenant_id, payment_date, payment_amount
                FROM payments
                WHERE tenant_id = %s
                ORDER BY payment_date ASC
            """, (tenant_id,))
            payments = cursor.fetchall()

            # Get tenant's room price
            cursor.execute("SELECT room_price FROM tenant_info WHERE tenant_id = %s", (tenant_id,))
            tenant = cursor.fetchone()
            room_price = Decimal(tenant['room_price']) if tenant else Decimal(0)

            # Calculate running balance
            total_paid = Decimal(0)
            for p in payments:
                total_paid += Decimal(p['payment_amount'])
                p['balance'] = float(room_price - total_paid)

        else:
            cursor.execute("SELECT * FROM payments ORDER BY payment_date ASC")
            payments = cursor.fetchall()

        cursor.close()
        return jsonify({"payments": payments})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})



@app.route("/api/payments", methods=["POST"])
def add_payment():
    data = request.json
    tenant_id = data.get("tenant_id")
    payment_date = data.get("payment_date")
    payment_amount = data.get("payment_amount")

    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO payments (tenant_id, payment_date, payment_amount, payment_status) VALUES (%s, %s, %s, %s)",
            (tenant_id, payment_date, payment_amount, "Paid"),
        )
        connection.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "Payment added"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})



@app.route("/api/tenants", methods=["POST"])
def add_tenant():
    data = request.json
    fullname = data.get("fullname")
    age = data.get("age")
    gender = data.get("gender")
    room_number = data.get("room_number")
    room_price = data.get("room_price")
    contact_no = data.get("contact_no")

    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO tenants (fullname, age, gender, room_number, room_price, contact_no) VALUES (%s, %s, %s, %s, %s, %s)",
            (fullname, age, gender, room_number, room_price, contact_no),
        )
        connection.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "Tenant added"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})



@app.route("/about")
def about_page():
    return render_template("about.html")



@app.route('/delete_payment/<int:payment_id>')
def delete_payment(payment_id):
    cursor.execute("DELETE FROM payments WHERE payment_id = %s", (payment_id,))
    connection.commit()
    return redirect(url_for('payment_page'))

@app.route("/alert")
def alert():
    return render_template("alert.html")

@app.route("/exit-alert")
def exit_alert():
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))




if __name__ == "__main__":
    socketio.run(app=app, host="0.0.0.0", port=5000, debug=True)

    

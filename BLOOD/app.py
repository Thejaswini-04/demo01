from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret_key'

# Admin Credentials (hardcoded)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# --- Database setup ---
def init_db():
    conn = sqlite3.connect('blood_bank.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS blood_stock (
            blood_type TEXT PRIMARY KEY,
            units INTEGER NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            blood_type TEXT,
            units INTEGER,
            type TEXT,
            status TEXT DEFAULT 'Pending',
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Prepopulate blood stock
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    for bt in blood_types:
        c.execute("INSERT OR IGNORE INTO blood_stock (blood_type, units) VALUES (?, ?)", (bt, 0))

    conn.commit()
    conn.close()

# --- Home Page ---
@app.route('/')
def home():
    conn = sqlite3.connect('blood_bank.db')
    c = conn.cursor()
    c.execute("SELECT * FROM blood_stock")
    stock = c.fetchall()
    conn.close()
    return render_template('home.html', stock=stock)

# --- Register ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('blood_bank.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            flash("Registration successful!", "success")
            return redirect(url_for('login'))
        except:
            flash("Email already exists!", "danger")
        finally:
            conn.close()
    return render_template('register.html')

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Admin login
        if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))

        # User login
        conn = sqlite3.connect('blood_bank.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('home'))

# --- User Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's request history
    conn = sqlite3.connect('blood_bank.db')
    c = conn.cursor()
    c.execute("SELECT id, blood_type, units, type, status FROM requests WHERE user_id = ? ORDER BY id DESC", 
              (session['user_id'],))
    user_requests = c.fetchall()
    conn.close()
    
    return render_template('dashboard.html', user_requests=user_requests)


'''# --- Donate Blood ---
@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        blood_type = request.form['blood_type']
        units = int(request.form['units'])
        conn = sqlite3.connect('blood_bank.db')
        c = conn.cursor()
        c.execute("INSERT INTO requests (user_id, blood_type, units, type) VALUES (?, ?, ?, 'Donate')",
                  (session['user_id'], blood_type, units))
        conn.commit()
        conn.close()
        flash("Donation request sent!", "info")
        return redirect(url_for('dashboard'))
    return render_template('donate.html')

# --- Request Blood ---
@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        blood_type = request.form['blood_type']
        units = int(request.form['units'])
        conn = sqlite3.connect('blood_bank.db')
        c = conn.cursor()
        c.execute("INSERT INTO requests (user_id, blood_type, units, type) VALUES (?, ?, ?, 'Request')",
                  (session['user_id'], blood_type, units))
        conn.commit()
        conn.close()
        flash("Blood request sent!", "info")
        return redirect(url_for('dashboard'))
    return render_template('request.html')
'''

# --- Donate or Request Blood (Unified Page) ---
@app.route('/donate_request', methods=['GET', 'POST'])
def donate_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        blood_type = request.form['blood_type']
        units = int(request.form['units'])
        action_type = request.form['action_type']
        date = datetime.now().strftime('%Y-%m-%d')

        conn = sqlite3.connect('blood_bank.db')
        c = conn.cursor()
        c.execute("INSERT INTO requests (user_id, blood_type, units, type, date) VALUES (?, ?, ?, ?, ?)",
                  (session['user_id'], blood_type, units, action_type, date))
        conn.commit()
        conn.close()

        flash(f"{action_type} request sent!", "info")
        return redirect(url_for('dashboard'))

    return render_template('donate_request.html')


# --- Admin Dashboard ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('blood_bank.db')
    c = conn.cursor()
    c.execute("SELECT r.id, u.name, r.blood_type, r.units, r.type, r.status, r.date FROM requests r JOIN users u ON r.user_id = u.id")
    requests_data = c.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', requests=requests_data)

# --- Approve or Reject ---
@app.route('/update_request/<int:request_id>/<action>')
def update_request(request_id, action):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('blood_bank.db')
    c = conn.cursor()
    c.execute("SELECT blood_type, units, type FROM requests WHERE id=?", (request_id,))
    req = c.fetchone()

    if not req:
        flash("Request not found", "danger")
        return redirect(url_for('admin_dashboard'))

    blood_type, units, req_type = req

    if action == 'approve':
        # Update stock
        if req_type == 'Donate':
            c.execute("UPDATE blood_stock SET units = units + ? WHERE blood_type = ?", (units, blood_type))
        elif req_type == 'Request':
            c.execute("SELECT units FROM blood_stock WHERE blood_type = ?", (blood_type,))
            available = c.fetchone()[0]
            if available < units:
                flash("Not enough stock to approve", "danger")
                conn.close()
                return redirect(url_for('admin_dashboard'))
            c.execute("UPDATE blood_stock SET units = units - ? WHERE blood_type = ?", (units, blood_type))
        c.execute("UPDATE requests SET status = 'Approved' WHERE id=?", (request_id,))
    elif action == 'reject':
        c.execute("UPDATE requests SET status = 'Rejected' WHERE id=?", (request_id,))

    conn.commit()
    conn.close()
    flash("Request updated!", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

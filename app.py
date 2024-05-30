from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_mail import Mail, Message
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import io
import os
from secret import password,sender


app = Flask(__name__)

app.secret_key = os.urandom(12)  # Required for flashing messages

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = sender()
app.config['MAIL_PASSWORD'] = password()
app.config['MAIL_DEFAULT_SENDER'] = sender()

mail = Mail(app)


DATABASE = 'database.db'





def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            subject TEXT NOT NULL
        );
    ''')
    conn.close()

@app.route("/", methods=["GET", "POST"])
def vote():
    subjects = ["Maths", "English", "Kiswahili", "Physics", "Chemistry", "Biology"]
    
    if check_voter_threshold():
        return redirect(url_for("poll_results"))
    elif request.method == "POST":
        email = request.form.get("email")
        subject = request.form.get("subject").title().strip()
        
        if subject not in subjects:
            flash('The subject entered is INVALID. TRY AGAIN!')
            return redirect(url_for("vote", subjects=subjects))

        # Check if email already exists in the database
        conn = get_db_connection()
        existing_email = conn.execute('SELECT email FROM votes WHERE email = ?', (email,)).fetchone()
        conn.close()

        if existing_email:
            flash("This email has already been used to vote. Please use a different email.")
            return redirect(url_for("vote", subjects=subjects))

        # Save vote to database
        conn = get_db_connection()
        with conn:
            conn.execute('INSERT INTO votes (email, subject) VALUES (?, ?)', (email, subject))
        conn.close()
        
        try:
            # Send a confirmation email
            msg = Message("Thank you for voting!", recipients=[email])
            msg.body = f"Dear Voter,\n\nThank you for participating in our poll!\nYour vote for {subject} has been successfully recorded."
            mail.send(msg)
        except:
            return '<h2>Check Your Network</h2>'
        
        return redirect(url_for("thank_you"))
    
    return render_template('vote.html', subjects=subjects)

@app.route("/thank_you")
def thank_you():
    return render_template('thank_you.html')

@app.route("/poll_results")
def poll_results():
    conn = get_db_connection()
    votes = conn.execute('SELECT subject, COUNT(*) as count FROM votes GROUP BY subject').fetchall()
    conn.close()
    
    return render_template('poll_results.html', votes=votes)

@app.route("/download_poll_results")
def download_poll_results():
    conn = get_db_connection()
    votes = conn.execute('SELECT subject, COUNT(*) as count FROM votes GROUP BY subject').fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    data = [["Subject", "Votes"]]  # Table header
    for vote in votes:
        data.append([vote["subject"], vote["count"]])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    
    # Adding copyright notice
    elements.append(canvas.Canvas(buffer).drawString(100, 50, "© 2024 Your Organization. All rights reserved."))

    doc.build(elements)
    buffer.seek(0)
    reset_db()
    return send_file(buffer, as_attachment=True, download_name="poll_results.pdf", mimetype='application/pdf')

def check_voter_threshold():
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM votes').fetchone()[0]
    conn.close()
    required_voters = 10  # Set the required number of voters
    return count >= required_voters


def reset_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    reset= cursor.execute('DELETE FROM votes')  # Delete all rows from the votes table
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()  # Initialize the database before starting the app
    app.run(debug=False,host='0.0.0.0')

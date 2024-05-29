from flask import Flask, render_template, url_for, redirect, request, flash
from flask_mail import Mail, Message
import sqlite3
from secret import password,sender

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = sender()
app.config['MAIL_PASSWORD'] = password()
app.config['MAIL_DEFAULT_SENDER'] = sender()

mail = Mail(app)

# SQLite3 database setup
DATABASE = 'polls.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                subject TEXT NOT NULL
            )
        ''')
    conn.close()


subjects = ["Maths", "English", "Kiswahili", "Physics", "Chemistry", "Biology"]

@app.route("/", methods=["GET", "POST"])
def vote():
    if check_voter_threshold():
          return redirect(url_for("poll_results"))
    elif request.method == "POST":
        email = request.form.get("email")
        subject = request.form.get("subject")
        subject.title().strip("")
        if subject not in subjects:
           flash('The subject Entered is INVALID TRY AGAIN!')
           return redirect(url_for("vote",subjects=subjects))

        # Check if email already exists in the database
        conn = get_db_connection()
        existing_email = conn.execute('SELECT email FROM votes WHERE email = ?', (email,)).fetchone()
        conn.close()

        if existing_email:
            flash("This email has already been used to vote. Please use a different email.")
            return redirect(url_for("vote",subjects=subjects))

        # Save vote to database
        conn = get_db_connection()
        with conn:
            conn.execute('INSERT INTO votes (email, subject) VALUES (?, ?)', (email, subject))
        conn.close()
        try:
            # Send a confirmation email
            msg = Message("Thank you for voting!", recipients=[email])
            msg.body = f"Dear Voter,\n\nThank you for participating in our poll!\nYour vote for {subject} has been successfully recorded.\nYour contribution helps shape the outcome and is greatly appreciated.\n\nBest regards,\n Arvine ltd"
            mail.send(msg)
        except:
            return  '<h2>Check Your Network</h2>'
        return redirect(url_for("thank_you"))
    return render_template('vote.html',subjects=subjects)

@app.route("/thank_you")
def thank_you():
    return render_template('thank_you.html',subjects=subjects)

@app.route("/poll_results")
def poll_results():
    conn = get_db_connection()
    votes = conn.execute('SELECT subject, COUNT(*) as count FROM votes GROUP BY subject').fetchall()
    conn.close()
    reset_db()
    return render_template('poll_results.html', votes=votes)

def check_voter_threshold():
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM votes').fetchone()[0]
    conn.close()
    required_voters = 10  # Set the required number of voters
    return count >= required_voters

def check_mail():
    conn = get_db_connection()
    emails = conn.execute('SELECT email FROM votes').fetchall()
    conn.close()
    return [email['email'] for email in emails]

def reset_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM votes')  # Delete all rows from the votes table
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()  # Initialize the database before starting the app
    app.run(debug=True)

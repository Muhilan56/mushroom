from flask import Flask, request, render_template, redirect, url_for, flash, session, send_from_directory
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # You can change this to a random string for better security

# Load your pre-trained model (update the path to your model)
MODEL_PATH = 'keras_model.h5'  # Replace with your model file path
model = load_model(MODEL_PATH)

# Define allowed extensions for uploaded files
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Database configuration
DATABASE = 'users.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Define class labels
CLASS_LABELS = {
    0: 'almond_mushroom',
    1: 'amanita_gemmata',
    2: 'amethyst_chanterelle',
    3: 'amethyst_deceiver',
    4: 'aniseed_funnel',
    5: 'ascot_hat',
    6: 'bay_bolete',
    7: 'bearded_milkcap',
    8: 'beechwood_sickener',
    9: 'beefsteak_fungus',
    10: 'birch_polypore',
    11: 'birch_woodwart',
    12: 'bitter_beech_bolete',
    13: 'bitter_bolete',
    14: 'black_bulgar'
}

# Initialize the database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

# Register a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                               (username, email, hashed_password))
                conn.commit()
            flash('Registration successful, please log in!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists!', 'error')
    return render_template('register.html')

# Login a user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]  # Store user id in session
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

# Home page (only accessible to logged-in users)
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')  # The page where the upload form exists

# Prediction route
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return "No file part in the request", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if file and allowed_file(file.filename):
        # Save file to the uploads folder
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        # Preprocess the image
        img = image.load_img(file_path, target_size=(224, 224))  # Update target_size if needed
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0  # Normalize the image

        # Predict using the model
        predictions = model.predict(img_array)
        predicted_class = np.argmax(predictions[0])

        # Fetch the label for the predicted class
        predicted_label = CLASS_LABELS.get(predicted_class, "Unknown class")

        # Return the result with the predicted label and image
        return render_template('result.html', label=predicted_label, image_filename=file.filename)

    return "File not allowed", 400

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)
# Logout the user
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove the user_id from the session
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    # Ensure the uploads folder exists
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # Initialize the database
    init_db()

    # Run the app
    app.run(debug=True)

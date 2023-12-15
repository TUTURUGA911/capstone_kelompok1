from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from bson import ObjectId
import jwt
import hashlib
from datetime import datetime, timedelta

import os
from os.path import join, dirname
from dotenv import load_dotenv


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True

SECRET_KEY = 'SPARTA'

TOKEN_KEY = 'mytoken'

# Function to format schedule
def format_schedule(schedule):
    if schedule == 'pagi':
        return 'Pagi (08:00-11:30)'
    elif schedule == 'siang':
        return 'Siang (12:00-18:00)'
    elif schedule == 'malam':
        return 'Malam (19:00-22:00)'
    else:
        return schedule
    
def get_doctors_with_queue():
    doctors = list(db.dokter.find())
    for doctor in doctors:
        # Hitung jumlah pasien untuk dokter tertentu
        doctor['antrian'] = len(list(db.pasien.find({'dokter_id': doctor['_id']})))
    return doctors

def get_next_queue_number(dokter_id):
    # Dapatkan nomor antrian terakhir untuk dokter tertentu
    last_queue_number = db.pasien.find_one({'dokter_id': dokter_id}, sort=[('queue_number', -1)])

    # Jika nomor antrian ada, tingkatkan; sebaliknya, mulai dari 1
    if last_queue_number and 'queue_number' in last_queue_number:
        return last_queue_number['queue_number'] + 1
    else:
        return 1
    
def get_formatted_date(date_str):
    try:
        # Assuming date_str is a string in the format '%Y-%m-%d %H:%M:%S'
        date_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date_object.strftime('%d %B %Y %H:%M:%S')  # Format the date as needed
    except ValueError:
        return None


@app.route('/')
def home():
    queue_number = request.args.get('queue_number', None)

    return render_template('index.html', queue_number=queue_number)

@app.route('/artikel_detail5')
def artikel_detail5():
   return render_template('artikel_detail5.html')

@app.route('/artikel_detail4')
def artikel_detail4():
   return render_template('artikel_detail4.html')

@app.route('/artikel_detail3')
def artikel_detail3():
   return render_template('artikel_detail3.html')

@app.route('/artikel_detail2')
def artikel_detail2():
   return render_template('artikel_detail2.html')

@app.route('/artikel_detail')
def artikel_detail():
   return render_template('artikel_detail.html')

@app.route('/artikel')
def artikel():
   return render_template('artikel.html')

@app.route('/admin', methods=['GET'])
def admin():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.admin.find_one({"username": payload["id"]})
        doctors = get_doctors_with_queue()
        return render_template('admin.html', doctors=doctors, format_schedule=format_schedule, user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Session expired. Please login again."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Wrong token. Please login again."))
    
@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)


@app.route("/user/<username>")
def user(username):
    # an endpoint for retrieving a user's profile information
    # and all of their posts
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # if this is my own profile, True
        # if this is somebody else's profile, False
        status = username == payload["id"]

        user_info = db.admin.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("admin"))


@app.route("/sign_in", methods=["POST"])
def sign_in():
    # Sign in
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    print(username_receive, pw_hash)
    result = db.admin.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,  # Change to user ID or any unique identifier
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    doc = {
        "username": username_receive,  # id
        "password": password_hash,  # password
        "profile_name": username_receive,  # user's name is set to their id by default
        "profile_pic": "",  # profile image file name
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # a default profile image
        "profile_info": "",  # a profile description
    }
    db.admin.insert_one(doc)
    return jsonify({"result": "success"})


@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    # ID we should check whether or not the id is already taken
    username_receive = request.form["username_give"]
    exists = bool(db.admin.find_one({"username": username_receive}))
    return jsonify({"result": "success", "exists": exists})
    
    
@app.route('/data_dokter', methods=['GET', 'POST'])
def tambah_dokter():
    
    if request.method == 'POST':
        nama = request.form['nama']
        spesialis = request.form['spesialis']
        id_dokter = request.form['id_dokter']
        jadwal = request.form['jadwal']
        alamat = request.form['alamat']
        jenis_kelamin = request.form['jenis_kelamin']
        nomor_telepon = request.form['nomor_telepon']

        doc = {
            'nama': nama,
            'spesialis': spesialis,
            'id_dokter': id_dokter,
            'jadwal': jadwal,
            'alamat': alamat,
            'jenis_kelamin': jenis_kelamin,
            'nomor_telepon': nomor_telepon
        }
        db.dokter.insert_one(doc)
        return redirect(url_for('tambah_dokter'))

    doctors = db.dokter.find()

    return render_template('data_dokter.html', doctors=doctors, format_schedule=format_schedule)

# Route to handle editing a doctor's information
@app.route('/edit_dokter/<id>', methods=['GET', 'POST'])
def edit_dokter(id):
    doctor = db.dokter.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        nama = request.form['nama']
        spesialis = request.form['spesialis']
        jadwal = request.form['jadwal']
        alamat = request.form['alamat']
        jenis_kelamin = request.form['jenis_kelamin']
        nomor_telepon = request.form['nomor_telepon']

        db.dokter.update_one({'_id': ObjectId(id)}, {'$set': {'nama': nama, 'spesialis': spesialis, 'jadwal': jadwal, 'alamat': alamat, 'jenis_kelamin': jenis_kelamin, 'nomor_telepon': nomor_telepon}})
        return redirect(url_for('tambah_dokter'))

    return render_template('data_dokter.html', doctor=doctor, format_schedule=format_schedule)

# Route to handle deleting a doctor
@app.route('/delete_dokter/<id>')
def delete_dokter(id):
    db.dokter.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('tambah_dokter'))

@app.route('/rekam_medis', methods=['GET', 'POST'])
def rekam_medis():
    # Check if the form is submitted
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        nomor_telepon = request.form['nomor_telepon']
        keluhan = request.form['keluhan']
        umur = request.form['umur']
        jenis_kelamin = request.form['jenis_kelamin']
        rujuk = 'rujuk' in request.form 
        rawat_inap = 'rawat_inap' in request.form 

        medical_record = {
            'nik': nik,
            'nama': nama,
            'nomor_telepon': nomor_telepon,
            'keluhan': keluhan,
            'umur': umur,
            'jenis_kelamin': jenis_kelamin,
            'rujuk': rujuk,
            'rawat_inap': rawat_inap
        }

        db.rekam_medis.insert_one(medical_record)

    patients = list(db.rekam_medis.find())

    return render_template('rekam_medis.html', patients=patients)

@app.route('/edit_patient/<id>', methods=['GET', 'POST'])
def edit_patient(id):
    patients = db.rekam_medis.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        # Update patient information based on the submitted form
        nik = request.form['nik']
        nama = request.form['nama']
        nomor_telepon = request.form['nomor_telepon']
        keluhan = request.form['keluhan']
        umur = request.form['umur']
        jenis_kelamin = request.form['jenis_kelamin']
        rujuk = 'rujuk' in request.form 
        rawat_inap = 'rawat_inap' in request.form 

        db.rekam_medis.update_one({'_id': ObjectId(id)}, {'$set': {'nik': nik, 'nama': nama, 'nomor_telepon': nomor_telepon, 'keluhan': keluhan, 'umur': umur, 'jenis_kelamin': jenis_kelamin, 'rujuk': rujuk, 'rawat_inap': rawat_inap}})
        return redirect(url_for('rekam_medis'))

    return render_template('rekam_medis.html', patients=patients)

# Route to handle deleting patient record
@app.route('/delete_patient/<id>')
def delete_patient(id):
    # Delete patient record based on the provided ID
    db.rekam_medis.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('rekam_medis'))


@app.route('/ambil_antrian', methods=['GET', 'POST'])
def ambil_antrian():
    doctors = get_doctors_with_queue()
    queue_number = None

    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        nomor_telepon = request.form['nomor_telepon']
        alamat = request.form['alamat']
        dokter_id = ObjectId(request.form['dokter'])
        current_date = datetime.now()  # Get the current date and time

        queue_number = get_next_queue_number(dokter_id)

        patient_data = {
            'nik': nik,
            'nama': nama,
            'nomor_telepon': nomor_telepon,
            'alamat': alamat,
            'dokter_id': dokter_id,
            'queue_number': queue_number,
            'date': current_date.strftime('%Y-%m-%d'),  # Convert to string and store in the 'date' field
        }

        db.pasien.insert_one(patient_data)

        return redirect(url_for('home', queue_number=queue_number))

    return render_template('ambil_antrian.html', doctors=doctors, queue_number=queue_number, current_date=datetime.now())

@app.route('/data_pasien')
def data_pasien():
    doctors = get_doctors_with_queue()
    patients = list(db.pasien.find())

    for patient in patients:
        # Assuming your date information is stored in the 'date' field
        patient['formatted_date'] = get_formatted_date(patient.get('date', ''))

    return render_template('data_pasien.html', doctors=doctors, patients=patients)

@app.route('/cek_dokter')
def cek_dokter():
    doctors = get_doctors_with_queue()
    return render_template('cek_dokter.html', doctors=doctors, format_schedule=format_schedule)

@app.route('/delete_pasien/<id>', methods=['POST'])
def delete_pasien(id):
    # Delete patient record based on the provided ID
    db.pasien.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('rekam_medis'))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)

import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from mysql.connector import connect, Error
from dotenv import load_dotenv
from werkzeug.utils import secure_filename


# Load environment variables
load_dotenv()
UPLOAD_FOLDER = 'uploads'  # You can change this to any directory you want
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MySQL configurations
mysql_config = {
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'database': os.getenv('MYSQL_DB', 'blog_db')
}

CREATE_ROOMS_TABLE = """
CREATE TABLE IF NOT EXISTS rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name TEXT NOT NULL
);
"""

CREATE_TEMPS_TABLE = """
CREATE TABLE IF NOT EXISTS temperatures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT,
    temperature REAL,
    date TIMESTAMP,
    FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE
);
"""

INSERT_ROOM_RETURN_ID = "INSERT INTO rooms(name) VALUES (%s);"

INSERT_TEMP = "INSERT INTO temperatures(room_id, temperature, date) VALUES (%s, %s, %s);"

GLOBAL_NUMBER_OF_DAYS = "SELECT COUNT(DISTINCT DATE(date)) AS days FROM temperatures;"

GLOBAL_AVG = "SELECT AVG(temperature) AS average FROM temperatures;"

CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LIKES_TABLE = """
CREATE TABLE IF NOT EXISTS likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
"""

INSERT_POST = """
INSERT INTO posts (title, content, image_url, created_at) VALUES (%s, %s, %s, %s);
"""

INSERT_LIKE = """
INSERT INTO likes (post_id, liked_at) VALUES (%s, %s);
"""

GET_ALL_POSTS = """
SELECT id, title, content, image_url, created_at FROM posts ORDER BY created_at DESC;
"""

GET_POST_BY_ID = """
SELECT id, title, content, image_url, created_at FROM posts WHERE id = %s;
"""

initialized = False

@app.before_request
def initialize():
    global initialized
    if not initialized:
        try:
            with connect(**mysql_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(CREATE_ROOMS_TABLE)
                    cursor.execute(CREATE_TEMPS_TABLE)
                    cursor.execute(CREATE_POSTS_TABLE)
                    cursor.execute(CREATE_LIKES_TABLE)
                connection.commit()
            initialized = True
        except Error as e:
            print(e)

@app.get('/')
def home():
    return "Hello world222"

@app.post('/api/room')
def create_room():
    data = request.get_json()
    name = data["name"]
    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_ROOM_RETURN_ID, (name,))
                connection.commit()
                room_id = cursor.lastrowid
        return {"id": room_id, "message": f"Room {name} created"}, 201
    except Error as e:
        return {"error": str(e)}, 500

@app.post('/api/temperature')
def add_temp():
    data = request.get_json()
    temperature = data["temperature"]
    room_id = data["room"]
    try:
        date = datetime.strptime(data["date"], "%m-%d-%Y %H:%M:%S")
    except KeyError:
        date = datetime.now(timezone.utc)

    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_TEMP, (room_id, temperature, date))
                connection.commit()
        return {"message": "Temperature added"}, 201
    except Error as e:
        return {"error": str(e)}, 500

@app.get('/api/average')
def get_global_avg():
    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(GLOBAL_AVG)
                average = cursor.fetchone()[0]
                cursor.execute(GLOBAL_NUMBER_OF_DAYS)
                days = cursor.fetchone()[0]
        return {"average": round(average, 2), "days": days}
    except Error as e:
        return {"error": str(e)}, 500
    
@app.post('/api/post')
def create_post():
    if 'file' not in request.files:
        return jsonify({"message": "No file part222"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        data = request.form
        title = data.get("title")
        content = data.get("content")
        image_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        created_at = datetime.now(timezone.utc)
        
        try:
            with connect(**mysql_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(INSERT_POST, (title, content, image_url, created_at))
                    connection.commit()
                    post_id = cursor.lastrowid
            return jsonify({"id": post_id, "message": "Post created", "image_url": image_url}), 201
        except Error as e:
            return {"error": str(e)}, 500
    else:
        return jsonify({"message": "File type not allowed"}), 400

@app.get('/api/posts')
def get_posts():
    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_ALL_POSTS)
                posts = cursor.fetchall()
                posts_list = []
                for post in posts:
                    post_dict = {
                        "id": post[0],
                        "title": post[1],
                        "content": post[2],
                        "image_url": post[3],
                        "created_at": post[4]
                    }
                    posts_list.append(post_dict)
        return {"posts": posts_list}, 200
    except Error as e:
        return {"error": str(e)}, 500
    
@app.get('/api/post/<int:post_id>')
def get_post(post_id):
    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_POST_BY_ID, (post_id,))
                post = cursor.fetchone()
                if post:
                    post_dict = {
                        "id": post[0],
                        "title": post[1],
                        "content": post[2],
                        "image_url": post[3],
                        "created_at": post[4]
                    }
                    return jsonify(post_dict), 200
                else:
                    return jsonify({"message": "Post not found"}), 404
    except Error as e:
        return {"error": str(e)}, 500

@app.post('/api/like')
def like_post():
    data = request.get_json()
    post_id = data["post_id"]
    liked_at = datetime.now(timezone.utc)

    try:
        with connect(**mysql_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_LIKE, (post_id, liked_at))
                connection.commit()
        return {"message": "Post liked"}, 201
    except Error as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)

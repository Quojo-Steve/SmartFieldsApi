import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask import Flask, request, jsonify

CREATE_ROOMS_TABLE = (
    "CREATE TABLE IF NOT EXISTS rooms (id SERIAL PRIMARY KEY, name TEXT);"
)

CREATE_TEMPS_TABLE = """CREATE TABLE IF NOT EXISTS temperatures (room_id INTEGER, temperature REAL, 
                        date TIMESTAMP, FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);"""

INSERT_ROOM_RETURN_ID = "INSERT INTO rooms(name) VALUES (%s) RETURNING ID;"

INSERT_TEMP = "INSERT INTO temperatures(room_id,temperature,date) VALUES (%s,%s,%s) ;"

GLOBAL_NUMBER_OF_DAYS = """SELECT COUNT (DISTINCT DATE(date)) AS days FROM temperatures;"""

GLOBAL_AVG = """SELECT AVG(temperature) AS average FROM temperatures;"""

CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LIKES_TABLE = """
CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
"""

INSERT_POST = """
INSERT INTO posts (title, content, image_url, created_at) VALUES (%s, %s, %s, %s) RETURNING id;
"""

INSERT_LIKE = """
INSERT INTO likes (post_id, liked_at) VALUES (%s, %s) RETURNING id;
"""

GET_ALL_POSTS = """
SELECT id, title, content, image_url, created_at FROM posts ORDER BY created_at DESC;
"""

GET_POST_BY_ID = """
SELECT id, title, content, image_url, created_at FROM posts WHERE id = %s;
"""

load_dotenv()

app = Flask(__name__)
url = os.getenv("DATABASE_URL")
connection = psycopg2.connect(url)

@app.get('/')
def home():
    return "Hello world"

@app.post('/api/room')
def create_room():
    data = request.get_json()
    name = data["name"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_ROOMS_TABLE)
            cursor.execute(INSERT_ROOM_RETURN_ID, (name,))
            room_id = cursor.fetchone()[0]
    return {"id":room_id, "message": f"Room {name} created"}, 201

@app.post('/api/temperature')
def add_temp():
    data = request.get_json()
    temperature = data["temperature"]
    room_id = data["room"]
    try:
        date = datetime.strptime(data["date"], "%m-%d-%Y %H:%M:%S")
    except KeyError:
        date = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TEMPS_TABLE)
            cursor.execute(INSERT_TEMP, (room_id,temperature, date))

    return {"message": "Temperature added"}, 201
        
@app.get('/api/average')
def get_global_avg():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(GLOBAL_AVG)
            average = cursor.fetchone()[0]
            cursor.execute(GLOBAL_NUMBER_OF_DAYS)
            days = cursor.fetchone()[0]
    return {"average": round(average, 2), "days":days}

@app.post('/api/post')
def create_post():
    data = request.get_json()
    title = data["title"]
    content = data["content"]
    image_url = data.get("image_url")
    created_at = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_POSTS_TABLE)
            cursor.execute(INSERT_POST, (title, content, image_url, created_at))
            post_id = cursor.fetchone()[0]
    
    return {"id": post_id, "message": "Post created"}, 201

@app.get('/api/posts')
def get_posts():
    with connection:
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

@app.get('/api/post/<int:post_id>')
def get_post(post_id):
    try:
        with connection:
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
    except KeyError as e:
        return {"error": str(e)}, 500

@app.post('/api/like')
def like_post():
    data = request.get_json()
    post_id = data["post_id"]
    liked_at = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_LIKES_TABLE)
            cursor.execute(INSERT_LIKE, (post_id, liked_at))
    
    return {"message": "Post liked"}, 201
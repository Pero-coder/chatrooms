from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from secrets import token_urlsafe


app = FastAPI()


@app.get("/")
def homepage():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Home</title>
    <script>
        function createRoom() {
            console.log("Create room");
        }
        function joinRoom() {
            console.log("Join room");
        }
    </script>
</head>
<body>
    <h1>Chatrooms</h1>
    <button onclick="createRoom()">Create room</button>
    <button onclick="joinRoom()">Join room</button>
</body>
</html>
    """)


@app.get("/create")
def create_room_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Home</title>
</head>
<body>
    <h1>Create room</h1>
    <form action="/api/create" method="POST">
        <label for="name">Username:</label>
        <input type="text" id="name" name="name" autocomplete="off"/></br>
        <button type="submit">Create</button>
    </from>
</body>
</html>
    """)


@app.post("/api/create/")
def create(name: str = Form()):
    return name

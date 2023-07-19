from fastapi import FastAPI, WebSocket, Response, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from string import ascii_letters
from random import choice


app = FastAPI()


class SocketManager:
    def __init__(self) -> None:
        self.active_connections: list[tuple[WebSocket, str]] = []

    async def connect(self, websocket: WebSocket, user: str):
        await websocket.accept()
        self.active_connections.append((websocket, user))

    def disconnect(self, websocket: WebSocket, user: str):
        self.active_connections.remove((websocket, user))

    async def broadcast(self, data):
        for connection in self.active_connections:
            await connection[0].send_json(data) 


class Chat:
    def __init__(self) -> None:
        self.sessions: dict[str, SocketManager] = {}

chat = Chat()


def get_token() -> str:
    """Generates 5 character long token used for chat sessions

    Returns:
        str: 5 character long string representing session token
    """
    token = "".join(choice(ascii_letters + "0123456789") for _ in range(5))
    if token in chat.sessions:
        return get_token()
    return token


@app.get("/")
def homepage():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Home</title>
</head>
<body>
    <h1>Chatrooms</h1>
    <button onclick="window.location.href = '/create';">Create room</button>
    <button onclick="window.location.href = '/join';">Join room</button>
</body>
</html>
    """)


@app.get("/create")
def create_room_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Create room</title>
    <script>
        function createRoom(e) {
            e.preventDefault()
            fetch("/api/register", {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json;charset=utf-8'
                },
                body: JSON.stringify({ username: document.getElementById('name').value })
            }).then(async (res) => {
                const body = await res.json();
                window.location.href = `/${body.token}`;
            })
        }
    </script>
</head>
<body>
    <h1>Create room</h1>
    <form onsubmit="createRoom(event);">
        <label for="name">Username:</label>
        <input type="text" id="name" autocomplete="off" required/></br>
        <button type="submit">Create</button>
    </from>
</body>
</html>
    """)


@app.get("/join")
def join_room_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Join room</title>
    <script>
        function createRoom(e) {
            e.preventDefault()
            const token = document.getElementById('token').value;
            fetch(`/api/register?token=${token}`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json;charset=utf-8'
                },
                body: JSON.stringify({ username: document.getElementById('name').value })
            }).then(async (res) => {
                window.location.href = `/${token}`;
            })
        }
    </script>
</head>
<body>
    <h1>Join room</h1>
    <form onsubmit="createRoom(event);">
        <label for="name">Username:</label>
        <input type="text" id="name" autocomplete="off" required/></br>
        <label for="token">Room token:</label>
        <input type="text" id="token" autocomplete="off" required/></br>
        <button type="submit">Join</button>
    </from>
</body>
</html>
    """)


@app.get("/{token}")
def join_room(token: str, response: Response):
    if token not in chat.sessions:
        response.status_code = 404
        return "Room not found"
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Chat</title>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
    <script>
        $(document).ready(function(){
            var current_user;
            $.get("/api/current_user",function(response){
                current_user = response;
            });
            var receiver = "";
            // create websocket
            const token = window.location.href.split("/")[3];
            var socket = new WebSocket(`ws://127.0.0.1:8000/api/${token}`);
            socket.onmessage = function(event) {
                var parent = $("#messages");
                var data = JSON.parse(event.data);
                var sender = data['sender'];
                if (sender == current_user)
                    sender = "You";
                var message = data['message']
                var content = "<p><strong>"+sender+" </strong> <span> "+message+"</span></p>";
                parent.append(content);
            };
            $("#chat-form").on("submit", function(e){
                e.preventDefault();
                var message = $("input").val();
                if (message){
                    data = {
                        "sender": current_user,
                        "message": message
                    };
                    socket.send(JSON.stringify(data));
                    $("input").val("");
                    document.cookie = 'X-Authorization=; path=/;';
                }
            });
        });
    </script>
</head>
<body>
    <div class="chat-body card">
        <div class="card-body">
            <strong id="profile"></strong><h4 class="card-title text-center"> Chat App </h4>
            <hr>
            <div id="messages">
            </div>
            <form class="form-inline" id="chat-form">
                <input type="text" class="form-control" placeholder="Write your message">
                <button id="send" type="submit" class="btn btn-primary">Send</button>
            </form>
        </div>
    </div>
</body>
</html>
    """)


@app.get("/api/current_user")
def get_user(request: Request):
    return request.cookies.get("X-Authorization")


class RegisterValidator(BaseModel):
    username: str


@app.post("/api/register")
def register_user(response: Response, user: RegisterValidator, token: str | None = None):
    response.set_cookie(key="X-Authorization", value=user.username, httponly=True)
    if not token:
        token = get_token()
        chat.sessions[token] = SocketManager()
        return {"token": token}


@app.websocket("/api/{token}")
async def chat_websocket(websocket: WebSocket, token: str):
    sender = websocket.cookies.get("X-Authorization")
    manager = chat.sessions.get(token)
    if not manager:
        return "Session does not exist"
    if sender:
        await manager.connect(websocket, sender)
        response = {
            "sender": sender,
            "message": "got connected"
        }
        await manager.broadcast(response)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.broadcast(data)
        except WebSocketDisconnect:
            manager.disconnect(websocket, sender)
            response['message'] = "left"
            await manager.broadcast(response)
            if not manager.active_connections:
                chat.sessions.pop(token)

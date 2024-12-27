from fastapi import WebSocket
from backend.database import get_latest_contact

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Fetch the latest contact data from the database
        data = get_latest_contact()
        
        # Send the data to the WebSocket client
        await websocket.send_json(data)

# backend/app.py
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from backend.markdown_parser import parse_markdown
from backend.database import create_database, store_in_database, get_latest_contact, get_all_contacts
import asyncio
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except WebSocketDisconnect:
                dead_connections.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                dead_connections.append(connection)
        
        for dead_connection in dead_connections:
            self.disconnect(dead_connection)

manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize the database and any other startup tasks"""
    try:
        create_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process_report/")
async def process_report(file: UploadFile = File(...)):
    try:
        content = await file.read()
        structured_data = parse_markdown(content.decode('utf-8'))
        logger.info(f"Processing structured data with {len(structured_data)} entries")

        for data in structured_data:
            try:
                contact_data = {
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'speed': data.get('speed', 0),
                    'type': data.get('type', 'unknown'),
                    'timestamp': data.get('timestamp', 'N/A'),
                    'significance': data.get('significance', 'N/A')
                }
                
                store_in_database(contact_data)
                
                
                if contact_data['latitude'] is not None and contact_data['longitude'] is not None:
                    await manager.broadcast(data)
                    
            except Exception as e:
                logger.error(f"Error processing contact: {e}")
                continue  
        
        return {
            "status": "success",
            "message": "Processed successfully", 
            "contact_count": len(structured_data)
        }
        
    except Exception as e:
        logger.error(f"Error processing report: {e}")
        return {"status": "error", "message": str(e)}, 500

@router.get("/initial_contacts")
async def get_initial_contacts():
    try:
        contacts = get_all_contacts()
        return contacts
    except Exception as e:
        logger.error(f"Error fetching initial contacts: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = get_latest_contact()
            if data:
                await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        latest = get_latest_contact()
        return {
            "status": "healthy",
            "database": "connected",
            "latest_contact": latest,
            "active_connections": len(manager.active_connections)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

app.include_router(router)
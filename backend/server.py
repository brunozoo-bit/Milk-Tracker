from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from bson import ObjectId
import io
import csv
from fastapi.responses import StreamingResponse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Helper to convert ObjectId to string
def serialize_doc(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# ========================
# MODELS
# ========================

class UserRole:
    ADMIN = "admin"
    FACTORY = "factory"
    PRODUCER = "producer"
    COLLECTOR = "collector"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str
    name: str
    nickname: Optional[str] = None
    photo: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    nickname: Optional[str] = None
    photo: Optional[str] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ProducerCreate(BaseModel):
    name: str
    nickname: str
    email: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    address: Optional[str] = None

class ProducerUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    address: Optional[str] = None

class ProducerResponse(BaseModel):
    id: str
    name: str
    nickname: str
    email: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    address: Optional[str] = None
    created_by: str
    created_at: datetime

class CollectorCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None

class CollectorResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    assigned_by: str
    created_at: datetime

class CollectionCreate(BaseModel):
    producer_id: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    quantity: float  # in liters
    day_of_week: str
    photo: Optional[str] = None
    notes: Optional[str] = None

class CollectionUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    quantity: Optional[float] = None
    day_of_week: Optional[str] = None
    photo: Optional[str] = None
    notes: Optional[str] = None

class CollectionResponse(BaseModel):
    id: str
    producer_id: str
    producer_name: str
    collector_id: str
    collector_name: str
    date: str
    time: str
    quantity: float
    day_of_week: str
    photo: Optional[str] = None
    notes: Optional[str] = None
    synced: bool
    created_at: datetime

class SyncCollectionCreate(BaseModel):
    producer_id: str
    date: str
    time: str
    quantity: float
    day_of_week: str
    photo: Optional[str] = None
    notes: Optional[str] = None
    offline_id: str

# ========================
# AUTH FUNCTIONS
# ========================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return serialize_doc(user)

def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

# ========================
# AUTH ROUTES
# ========================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_dict = {
        "email": user.email,
        "password": get_password_hash(user.password),
        "role": user.role,
        "name": user.name,
        "nickname": user.nickname,
        "photo": user.photo,
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    return UserResponse(
        id=str(result.inserted_id),
        email=user.email,
        role=user.role,
        name=user.name,
        nickname=user.nickname,
        photo=user.photo,
        created_at=user_dict["created_at"]
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_login: UserLogin):
    user = await db.users.find_one({"email": user_login.email})
    if not user or not verify_password(user_login.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            name=user["name"],
            nickname=user.get("nickname"),
            photo=user.get("photo"),
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["_id"],
        email=current_user["email"],
        role=current_user["role"],
        name=current_user["name"],
        nickname=current_user.get("nickname"),
        photo=current_user.get("photo"),
        created_at=current_user["created_at"]
    )

# ========================
# PRODUCER ROUTES
# ========================

@api_router.post("/producers", response_model=ProducerResponse)
async def create_producer(
    producer: ProducerCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    producer_dict = producer.dict()
    producer_dict["created_by"] = current_user["_id"]
    producer_dict["created_at"] = datetime.utcnow()
    
    result = await db.producers.insert_one(producer_dict)
    producer_dict["_id"] = result.inserted_id
    
    return ProducerResponse(
        id=str(result.inserted_id),
        **producer.dict(),
        created_by=current_user["_id"],
        created_at=producer_dict["created_at"]
    )

@api_router.get("/producers", response_model=List[ProducerResponse])
async def get_producers(current_user: dict = Depends(get_current_user)):
    producers = await db.producers.find().to_list(1000)
    return [
        ProducerResponse(
            id=str(p["_id"]),
            name=p["name"],
            nickname=p["nickname"],
            email=p.get("email"),
            phone=p.get("phone"),
            photo=p.get("photo"),
            address=p.get("address"),
            created_by=str(p["created_by"]),
            created_at=p["created_at"]
        )
        for p in producers
    ]

@api_router.get("/producers/{producer_id}", response_model=ProducerResponse)
async def get_producer(
    producer_id: str,
    current_user: dict = Depends(get_current_user)
):
    producer = await db.producers.find_one({"_id": ObjectId(producer_id)})
    if not producer:
        raise HTTPException(status_code=404, detail="Producer not found")
    
    return ProducerResponse(
        id=str(producer["_id"]),
        name=producer["name"],
        nickname=producer["nickname"],
        email=producer.get("email"),
        phone=producer.get("phone"),
        photo=producer.get("photo"),
        address=producer.get("address"),
        created_by=str(producer["created_by"]),
        created_at=producer["created_at"]
    )

@api_router.put("/producers/{producer_id}", response_model=ProducerResponse)
async def update_producer(
    producer_id: str,
    producer_update: ProducerUpdate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    update_data = {k: v for k, v in producer_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.producers.update_one(
        {"_id": ObjectId(producer_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Producer not found")
    
    updated_producer = await db.producers.find_one({"_id": ObjectId(producer_id)})
    return ProducerResponse(
        id=str(updated_producer["_id"]),
        name=updated_producer["name"],
        nickname=updated_producer["nickname"],
        email=updated_producer.get("email"),
        phone=updated_producer.get("phone"),
        photo=updated_producer.get("photo"),
        address=updated_producer.get("address"),
        created_by=str(updated_producer["created_by"]),
        created_at=updated_producer["created_at"]
    )

@api_router.delete("/producers/{producer_id}")
async def delete_producer(
    producer_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    result = await db.producers.delete_one({"_id": ObjectId(producer_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producer not found")
    return {"message": "Producer deleted successfully"}

# ========================
# COLLECTOR ROUTES
# ========================

@api_router.post("/collectors", response_model=CollectorResponse)
async def create_collector(
    collector: CollectorCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    collector_dict = collector.dict()
    collector_dict["assigned_by"] = current_user["_id"]
    collector_dict["created_at"] = datetime.utcnow()
    
    result = await db.collectors.insert_one(collector_dict)
    
    return CollectorResponse(
        id=str(result.inserted_id),
        **collector.dict(),
        assigned_by=current_user["_id"],
        created_at=collector_dict["created_at"]
    )

@api_router.get("/collectors", response_model=List[CollectorResponse])
async def get_collectors(current_user: dict = Depends(get_current_user)):
    collectors = await db.collectors.find().to_list(1000)
    return [
        CollectorResponse(
            id=str(c["_id"]),
            name=c["name"],
            email=c.get("email"),
            phone=c.get("phone"),
            photo=c.get("photo"),
            assigned_by=str(c["assigned_by"]),
            created_at=c["created_at"]
        )
        for c in collectors
    ]

@api_router.delete("/collectors/{collector_id}")
async def delete_collector(
    collector_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    result = await db.collectors.delete_one({"_id": ObjectId(collector_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Collector not found")
    return {"message": "Collector deleted successfully"}

# ========================
# COLLECTION ROUTES
# ========================

@api_router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    current_user: dict = Depends(require_roles([UserRole.COLLECTOR, UserRole.ADMIN, UserRole.FACTORY]))
):
    # Verify producer exists
    producer = await db.producers.find_one({"_id": ObjectId(collection.producer_id)})
    if not producer:
        raise HTTPException(status_code=404, detail="Producer not found")
    
    collection_dict = collection.dict()
    collection_dict["collector_id"] = current_user["_id"]
    collection_dict["synced"] = True
    collection_dict["created_at"] = datetime.utcnow()
    
    result = await db.collections.insert_one(collection_dict)
    
    return CollectionResponse(
        id=str(result.inserted_id),
        producer_id=collection.producer_id,
        producer_name=f"{producer['name']} ({producer['nickname']})",
        collector_id=current_user["_id"],
        collector_name=current_user["name"],
        date=collection.date,
        time=collection.time,
        quantity=collection.quantity,
        day_of_week=collection.day_of_week,
        photo=collection.photo,
        notes=collection.notes,
        synced=True,
        created_at=collection_dict["created_at"]
    )

@api_router.get("/collections", response_model=List[CollectionResponse])
async def get_collections(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    producer_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    # Filter by producer for producer role
    if current_user["role"] == UserRole.PRODUCER:
        # Find producer linked to user
        producer = await db.producers.find_one({"email": current_user["email"]})
        if producer:
            query["producer_id"] = str(producer["_id"])
    elif producer_id:
        query["producer_id"] = producer_id
    
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    collections = await db.collections.find(query).sort("created_at", -1).to_list(1000)
    
    result = []
    for c in collections:
        producer = await db.producers.find_one({"_id": ObjectId(c["producer_id"])})
        collector = await db.users.find_one({"_id": ObjectId(c["collector_id"])})
        
        result.append(CollectionResponse(
            id=str(c["_id"]),
            producer_id=c["producer_id"],
            producer_name=f"{producer['name']} ({producer['nickname']})" if producer else "Unknown",
            collector_id=str(c["collector_id"]),
            collector_name=collector["name"] if collector else "Unknown",
            date=c["date"],
            time=c["time"],
            quantity=c["quantity"],
            day_of_week=c["day_of_week"],
            photo=c.get("photo"),
            notes=c.get("notes"),
            synced=c.get("synced", True),
            created_at=c["created_at"]
        ))
    
    return result

@api_router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
):
    collection = await db.collections.find_one({"_id": ObjectId(collection_id)})
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    producer = await db.producers.find_one({"_id": ObjectId(collection["producer_id"])})
    collector = await db.users.find_one({"_id": ObjectId(collection["collector_id"])})
    
    return CollectionResponse(
        id=str(collection["_id"]),
        producer_id=collection["producer_id"],
        producer_name=f"{producer['name']} ({producer['nickname']})" if producer else "Unknown",
        collector_id=str(collection["collector_id"]),
        collector_name=collector["name"] if collector else "Unknown",
        date=collection["date"],
        time=collection["time"],
        quantity=collection["quantity"],
        day_of_week=collection["day_of_week"],
        photo=collection.get("photo"),
        notes=collection.get("notes"),
        synced=collection.get("synced", True),
        created_at=collection["created_at"]
    )

@api_router.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    collection_update: CollectionUpdate,
    current_user: dict = Depends(require_roles([UserRole.COLLECTOR, UserRole.ADMIN, UserRole.FACTORY]))
):
    update_data = {k: v for k, v in collection_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return await get_collection(collection_id, current_user)

@api_router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    result = await db.collections.delete_one({"_id": ObjectId(collection_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Collection deleted successfully"}

# ========================
# SYNC ROUTE (for offline data)
# ========================

@api_router.post("/collections/sync")
async def sync_collections(
    collections: List[SyncCollectionCreate],
    current_user: dict = Depends(require_roles([UserRole.COLLECTOR, UserRole.ADMIN, UserRole.FACTORY]))
):
    synced_ids = []
    errors = []
    
    for collection in collections:
        try:
            # Verify producer exists
            producer = await db.producers.find_one({"_id": ObjectId(collection.producer_id)})
            if not producer:
                errors.append({"offline_id": collection.offline_id, "error": "Producer not found"})
                continue
            
            collection_dict = collection.dict(exclude={"offline_id"})
            collection_dict["collector_id"] = current_user["_id"]
            collection_dict["synced"] = True
            collection_dict["created_at"] = datetime.utcnow()
            
            result = await db.collections.insert_one(collection_dict)
            synced_ids.append({"offline_id": collection.offline_id, "server_id": str(result.inserted_id)})
        except Exception as e:
            errors.append({"offline_id": collection.offline_id, "error": str(e)})
    
    return {"synced": synced_ids, "errors": errors}

# ========================
# REPORTS
# ========================

@api_router.get("/reports/export")
async def export_report(
    start_date: str,
    end_date: str,
    producer_id: Optional[str] = None,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    query = {
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    if producer_id:
        query["producer_id"] = producer_id
    
    collections = await db.collections.find(query).sort("date", 1).to_list(10000)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Hora", "Dia da Semana", "Produtor", "Apelido", "Quantidade (L)", "Coletor", "Observações"])
    
    for c in collections:
        producer = await db.producers.find_one({"_id": ObjectId(c["producer_id"])})
        collector = await db.users.find_one({"_id": ObjectId(c["collector_id"])})
        
        writer.writerow([
            c["date"],
            c["time"],
            c["day_of_week"],
            producer["name"] if producer else "Unknown",
            producer["nickname"] if producer else "Unknown",
            c["quantity"],
            collector["name"] if collector else "Unknown",
            c.get("notes", "")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=relatorio_{start_date}_{end_date}.csv"}
    )

@api_router.get("/reports/summary")
async def get_report_summary(
    start_date: str,
    end_date: str,
    producer_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    # Filter by producer for producer role
    if current_user["role"] == UserRole.PRODUCER:
        producer = await db.producers.find_one({"email": current_user["email"]})
        if producer:
            query["producer_id"] = str(producer["_id"])
    elif producer_id:
        query["producer_id"] = producer_id
    
    collections = await db.collections.find(query).to_list(10000)
    
    total_quantity = sum(c["quantity"] for c in collections)
    total_collections = len(collections)
    avg_quantity = total_quantity / total_collections if total_collections > 0 else 0
    
    # Group by producer
    by_producer = {}
    for c in collections:
        pid = c["producer_id"]
        if pid not in by_producer:
            producer = await db.producers.find_one({"_id": ObjectId(pid)})
            by_producer[pid] = {
                "producer_name": producer["name"] if producer else "Unknown",
                "producer_nickname": producer["nickname"] if producer else "Unknown",
                "total_quantity": 0,
                "collection_count": 0
            }
        by_producer[pid]["total_quantity"] += c["quantity"]
        by_producer[pid]["collection_count"] += 1
    
    return {
        "total_quantity": total_quantity,
        "total_collections": total_collections,
        "average_quantity": round(avg_quantity, 2),
        "by_producer": list(by_producer.values())
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # Create default admin if not exists
    admin = await db.users.find_one({"email": "admin@milktracker.com"})
    if not admin:
        admin_dict = {
            "email": "admin@milktracker.com",
            "password": get_password_hash("admin123"),
            "role": UserRole.ADMIN,
            "name": "Administrator",
            "nickname": "Admin",
            "photo": None,
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(admin_dict)
        logger.info("Default admin created: admin@milktracker.com / admin123")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

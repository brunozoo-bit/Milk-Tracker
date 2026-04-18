from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from bson import ObjectId
import io
import csv
from fastapi.responses import StreamingResponse
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection for registry (master database)
mongo_url = os.environ['MONGO_URL']
registry_client = AsyncIOMotorClient(mongo_url)
registry_db = registry_client['factory_registry']

# Cache for tenant database connections
tenant_db_connections: Dict[str, AsyncIOMotorClient] = {}

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

# Helper to get tenant database
async def get_tenant_db(factory_code: str):
    """Get or create database connection for a specific factory"""
    if factory_code not in tenant_db_connections:
        client = AsyncIOMotorClient(mongo_url)
        tenant_db_connections[factory_code] = client
    
    db_name = f"factory_{factory_code}"
    return tenant_db_connections[factory_code][db_name]

# ========================
# MODELS
# ========================

class UserRole:
    ADMIN = "admin"
    FACTORY = "factory"
    PRODUCER = "producer"
    COLLECTOR = "collector"

class FactoryRegister(BaseModel):
    name: str
    code: str  # Unique slug/code
    admin_name: str
    admin_email: EmailStr
    admin_password: str

class FactoryResponse(BaseModel):
    id: str
    name: str
    code: str
    admin_email: str
    created_at: datetime
    is_active: bool

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str
    name: str
    nickname: Optional[str] = None
    photo: Optional[str] = None

class UserLogin(BaseModel):
    factory_code: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    nickname: Optional[str] = None
    photo: Optional[str] = None
    factory_code: str
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
    email: EmailStr  # Required for login
    password: str  # Admin sets password for collector
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

class PasswordResetRequest(BaseModel):
    email: EmailStr
    name: str
    user_type: str  # "collector" or "producer"

class PasswordResetResponse(BaseModel):
    id: str
    email: str
    name: str
    user_type: str
    status: str  # "pending" or "completed"
    requested_at: datetime
    completed_at: Optional[datetime] = None

class SetNewPassword(BaseModel):
    request_id: str
    new_password: str

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
        factory_code: str = payload.get("factory_code")
        
        if user_id is None or factory_code is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Get tenant database
    db = await get_tenant_db(factory_code)
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    user["factory_code"] = factory_code
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
# FACTORY REGISTRATION
# ========================

@api_router.post("/factories/register", response_model=FactoryResponse)
async def register_factory(factory: FactoryRegister):
    # Validate factory code (alphanumeric and dashes only)
    if not re.match(r'^[a-z0-9-]+$', factory.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código deve conter apenas letras minúsculas, números e hífens"
        )
    
    # Check if factory code already exists
    existing_factory = await registry_db.factories.find_one({"code": factory.code})
    if existing_factory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de fábrica já está em uso"
        )
    
    # Check if admin email already exists in this factory
    existing_email = await registry_db.factories.find_one({"admin_email": factory.admin_email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está cadastrado"
        )
    
    # Create factory in registry
    factory_dict = {
        "name": factory.name,
        "code": factory.code,
        "admin_email": factory.admin_email,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    result = await registry_db.factories.insert_one(factory_dict)
    
    # Create tenant database and admin user
    tenant_db = await get_tenant_db(factory.code)
    
    admin_user = {
        "email": factory.admin_email,
        "password": get_password_hash(factory.admin_password),
        "role": UserRole.ADMIN,
        "name": factory.admin_name,
        "nickname": "Admin",
        "photo": None,
        "created_at": datetime.utcnow()
    }
    
    await tenant_db.users.insert_one(admin_user)
    
    return FactoryResponse(
        id=str(result.inserted_id),
        name=factory.name,
        code=factory.code,
        admin_email=factory.admin_email,
        created_at=factory_dict["created_at"],
        is_active=True
    )

@api_router.get("/factories/check/{code}")
async def check_factory_code(code: str):
    """Check if factory code exists"""
    factory = await registry_db.factories.find_one({"code": code})
    return {
        "exists": factory is not None,
        "name": factory.get("name") if factory else None
    }

# ========================
# AUTH ROUTES
# ========================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    factory_code = current_user["factory_code"]
    db = await get_tenant_db(factory_code)
    
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
    
    return UserResponse(
        id=str(result.inserted_id),
        email=user.email,
        role=user.role,
        name=user.name,
        nickname=user.nickname,
        photo=user.photo,
        factory_code=factory_code,
        created_at=user_dict["created_at"]
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_login: UserLogin):
    # Check if factory exists
    factory = await registry_db.factories.find_one({"code": user_login.factory_code})
    if not factory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fábrica não encontrada"
        )
    
    if not factory.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fábrica inativa"
        )
    
    # Get tenant database
    db = await get_tenant_db(user_login.factory_code)
    
    user = await db.users.find_one({"email": user_login.email})
    if not user or not verify_password(user_login.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )
    
    access_token = create_access_token(data={
        "sub": str(user["_id"]),
        "factory_code": user_login.factory_code
    })
    
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
            factory_code=user_login.factory_code,
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
        factory_code=current_user["factory_code"],
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
    db = await get_tenant_db(current_user["factory_code"])
    
    producer_dict = producer.dict()
    producer_dict["created_by"] = current_user["_id"]
    producer_dict["created_at"] = datetime.utcnow()
    
    result = await db.producers.insert_one(producer_dict)
    
    return ProducerResponse(
        id=str(result.inserted_id),
        **producer.dict(),
        created_by=current_user["_id"],
        created_at=producer_dict["created_at"]
    )

@api_router.get("/producers", response_model=List[ProducerResponse])
async def get_producers(current_user: dict = Depends(get_current_user)):
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": collector.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Create user account for collector
    user_dict = {
        "email": collector.email,
        "password": get_password_hash(collector.password),
        "role": UserRole.COLLECTOR,
        "name": collector.name,
        "nickname": None,
        "photo": collector.photo,
        "created_at": datetime.utcnow()
    }
    
    user_result = await db.users.insert_one(user_dict)
    
    # Create collector record
    collector_dict = {
        "name": collector.name,
        "email": collector.email,
        "phone": collector.phone,
        "photo": collector.photo,
        "user_id": str(user_result.inserted_id),
        "assigned_by": current_user["_id"],
        "created_at": datetime.utcnow()
    }
    
    result = await db.collectors.insert_one(collector_dict)
    
    return CollectorResponse(
        id=str(result.inserted_id),
        name=collector.name,
        email=collector.email,
        phone=collector.phone,
        photo=collector.photo,
        assigned_by=current_user["_id"],
        created_at=collector_dict["created_at"]
    )

@api_router.get("/collectors", response_model=List[CollectorResponse])
async def get_collectors(current_user: dict = Depends(get_current_user)):
    db = await get_tenant_db(current_user["factory_code"])
    
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    
    # Batch fetch all producers and collectors to avoid N+1 queries
    producer_ids = list(set([ObjectId(c["producer_id"]) for c in collections]))
    collector_ids = list(set([ObjectId(c["collector_id"]) for c in collections]))
    
    producers_cursor = db.producers.find({"_id": {"$in": producer_ids}})
    collectors_cursor = db.users.find({"_id": {"$in": collector_ids}})
    
    producers_list = await producers_cursor.to_list(None)
    collectors_list = await collectors_cursor.to_list(None)
    
    # Create lookup dictionaries
    producers_map = {str(p["_id"]): p for p in producers_list}
    collectors_map = {str(c["_id"]): c for c in collectors_list}
    
    result = []
    for c in collections:
        producer = producers_map.get(c["producer_id"])
        collector = collectors_map.get(str(c["collector_id"]))
        
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    db = await get_tenant_db(current_user["factory_code"])
    
    query = {
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    if producer_id:
        query["producer_id"] = producer_id
    
    collections = await db.collections.find(query).sort("date", 1).to_list(10000)
    
    # Batch fetch all producers and collectors to avoid N+1 queries
    producer_ids = list(set([ObjectId(c["producer_id"]) for c in collections]))
    collector_ids = list(set([ObjectId(c["collector_id"]) for c in collections]))
    
    producers_cursor = db.producers.find({"_id": {"$in": producer_ids}})
    collectors_cursor = db.users.find({"_id": {"$in": collector_ids}})
    
    producers_list = await producers_cursor.to_list(None)
    collectors_list = await collectors_cursor.to_list(None)
    
    # Create lookup dictionaries
    producers_map = {str(p["_id"]): p for p in producers_list}
    collectors_map = {str(c["_id"]): c for c in collectors_list}
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Hora", "Dia da Semana", "Produtor", "Apelido", "Quantidade (L)", "Coletor", "Observações"])
    
    for c in collections:
        producer = producers_map.get(c["producer_id"])
        collector = collectors_map.get(str(c["collector_id"]))
        
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
    db = await get_tenant_db(current_user["factory_code"])
    
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
    
    # Batch fetch all producers to avoid N+1 queries
    producer_ids = list(set([ObjectId(c["producer_id"]) for c in collections]))
    producers_cursor = db.producers.find({"_id": {"$in": producer_ids}})
    producers_list = await producers_cursor.to_list(None)
    producers_map = {str(p["_id"]): p for p in producers_list}
    
    # Group by producer
    by_producer = {}
    for c in collections:
        pid = c["producer_id"]
        if pid not in by_producer:
            producer = producers_map.get(pid)
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

# ========================
# PASSWORD RESET ROUTES
# ========================

@api_router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(request: PasswordResetRequest):
    """Public endpoint - anyone can request password reset"""
    # Verificar se existe na fábrica principal por enquanto
    factory_code = "principal"
    db = await get_tenant_db(factory_code)
    
    # Verificar se o email existe
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email não encontrado no sistema"
        )
    
    # Verificar se já existe uma solicitação pendente
    existing_request = await db.password_reset_requests.find_one({
        "email": request.email,
        "status": "pending"
    })
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma solicitação pendente para este email"
        )
    
    # Criar solicitação
    request_dict = {
        "email": request.email,
        "name": request.name,
        "user_type": request.user_type,
        "user_role": user["role"],
        "factory_code": factory_code,
        "status": "pending",
        "requested_at": datetime.utcnow(),
        "completed_at": None
    }
    
    result = await db.password_reset_requests.insert_one(request_dict)
    
    return PasswordResetResponse(
        id=str(result.inserted_id),
        email=request.email,
        name=request.name,
        user_type=request.user_type,
        status="pending",
        requested_at=request_dict["requested_at"]
    )

@api_router.get("/password-reset/requests", response_model=List[PasswordResetResponse])
async def get_password_reset_requests(
    status_filter: Optional[str] = "pending",
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    """Admin and Factory can view password reset requests"""
    db = await get_tenant_db(current_user["factory_code"])
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    requests = await db.password_reset_requests.find(query).sort("requested_at", -1).to_list(1000)
    
    return [
        PasswordResetResponse(
            id=str(r["_id"]),
            email=r["email"],
            name=r["name"],
            user_type=r["user_type"],
            status=r["status"],
            requested_at=r["requested_at"],
            completed_at=r.get("completed_at")
        )
        for r in requests
    ]

@api_router.post("/password-reset/set")
async def set_new_password(
    reset_data: SetNewPassword,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.FACTORY]))
):
    """Admin and Factory can set new password for users"""
    db = await get_tenant_db(current_user["factory_code"])
    
    # Buscar a solicitação
    reset_request = await db.password_reset_requests.find_one({
        "_id": ObjectId(reset_data.request_id)
    })
    
    if not reset_request:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    
    if reset_request["status"] != "pending":
        raise HTTPException(status_code=400, detail="Esta solicitação já foi processada")
    
    # Validar senha
    if len(reset_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve ter pelo menos 6 caracteres"
        )
    
    # Atualizar senha do usuário
    result = await db.users.update_one(
        {"email": reset_request["email"]},
        {"$set": {"password": get_password_hash(reset_data.new_password)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Marcar solicitação como concluída
    await db.password_reset_requests.update_one(
        {"_id": ObjectId(reset_data.request_id)},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "completed_by": current_user["_id"]
        }}
    )
    
    return {
        "message": "Senha redefinida com sucesso",
        "email": reset_request["email"],
        "new_password": reset_data.new_password
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
    logger.info("Multi-tenant milk tracking system started")
    logger.info("Factory registry database: factory_registry")

@app.on_event("shutdown")
async def shutdown_db_client():
    registry_client.close()
    for client in tenant_db_connections.values():
        client.close()

# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import Annotated, Optional, List, Dict, Any
from sqlalchemy.orm import Session
import json, re, os, io, shutil, uuid

from app.core.database import get_db
from app.services import agent_service, user_service, viz_service, report_service, rag_service, redis_service
from app.schemas.user import UserCreate, Token, TokenData, UserInDB
from app.core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM

app = FastAPI(title="InsightGPT Pro API", version="1.0.0")
agent_executor = agent_service.create_agent()

class QueryRequest(BaseModel): query: str
class QueryResponse(BaseModel):
    answer: str
    chart_json: Optional[str] = None
class HistoryRequest(BaseModel): chat_history: List[Dict[str, Any]]
class ReportRequest(HistoryRequest): pass
class SessionCreationResponse(BaseModel): session_id: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub");
        if username is None: raise credentials_exception
    except JWTError: raise credentials_exception
    if username.startswith("guest_"): return UserInDB(id=0, username=username, hashed_password="")
    user = user_service.get_user(db=db, username=username);
    if user is None: raise credentials_exception
    return user

@app.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = user_service.get_user(db=db, username=user.username);
    if db_user: raise HTTPException(status_code=400, detail="Username already registered")
    return user_service.create_user(db=db, user=user)

@app.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = user_service.get_user(db=db, username=form_data.username);
    if not user or not verify_password(form_data.password, user.hashed_password): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": user.username});
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/guest-token", response_model=Token, tags=["Authentication"])
async def login_as_guest():
    guest_username = f"guest_{uuid.uuid4()}";
    access_token = create_access_token(data={"sub": guest_username});
    return {"access_token": access_token, "token_type": "bearer"}

# --- NEW SESSION/HISTORY ENDPOINTS ---
@app.get("/sessions", tags=["History"])
async def get_sessions(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.username.startswith("guest_"): return []
    return redis_service.get_sessions_for_user(current_user.username)

@app.get("/sessions/{session_id}", tags=["History"])
async def get_session_history(session_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if not session_id.startswith(current_user.username) and not current_user.username.startswith("guest_"):
        raise HTTPException(status_code=403, detail="Not authorized to view this session")
    return redis_service.get_session(session_id)

@app.post("/sessions", response_model=SessionCreationResponse, tags=["History"])
async def create_session(request: HistoryRequest, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.username.startswith("guest_"): raise HTTPException(status_code=403, detail="Guests cannot save sessions.")
    session_id = redis_service.create_new_session(current_user.username, request.chat_history)
    if not session_id: raise HTTPException(status_code=500, detail="Could not create session.")
    return SessionCreationResponse(session_id=session_id)

@app.put("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["History"])
async def update_session_history(session_id: str, request: HistoryRequest, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if not session_id.startswith(current_user.username) and not current_user.username.startswith("guest_"):
        raise HTTPException(status_code=403, detail="Not authorized to update this session")
    redis_service.update_session(session_id, request.chat_history)
    return

@app.post("/upload", tags=["RAG"])
async def upload_document(file: UploadFile = File(...), current_user: Annotated[UserInDB, Depends(get_current_user)] = None):
    temp_file_path = os.path.join("data", file.filename)
    try:
        with open(temp_file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        rag_service.process_and_load_pdf(temp_file_path)
        return {"status": "success", "message": f"Document '{file.filename}' processed successfully."}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        if os.path.exists(temp_file_path): os.remove(temp_file_path)

@app.post("/report", tags=["Reporting"])
async def generate_report_endpoint(request: ReportRequest, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.username.startswith("guest_"): raise HTTPException(status_code=403, detail="Guests cannot generate reports.")
    try:
        pdf_bytes = report_service.generate_report_from_history(request.chat_history)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": "attachment;filename=InsightGPT_Report.pdf"})
    except Exception as e: raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def handle_query(request: QueryRequest, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    agent_response = agent_service.run_query(request.query)
    chart_json, answer_text = None, agent_response
    json_match = re.search(r"\{.*\}", agent_response, re.DOTALL)
    if json_match:
        json_string = json_match.group(0)
        try:
            response_data = json.loads(json_string)
            if "chart_details" in response_data and "data" in response_data:
                details = response_data["chart_details"]; chart_type = details.get("type")
                if chart_type == "bar": chart_json = viz_service.create_bar_chart(data=response_data["data"], x_col=details["x_col"], y_col=details["y_col"], title=details["title"])
                elif chart_type == "pie": chart_json = viz_service.create_pie_chart(data=response_data["data"], names_col=details["names_col"], values_col=details["values_col"], title=details["title"])
                answer_text = response_data.get("comment", "Here is the chart you requested.")
        except (json.JSONDecodeError, TypeError): pass
    return QueryResponse(answer=answer_text, chart_json=chart_json)

@app.get("/", tags=["Health Check"])
async def root(): return {"status": "ok", "message": "InsightGPT Pro API is running."}
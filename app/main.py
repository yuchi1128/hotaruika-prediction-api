from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List

from app.services.prediction_service import PredictionService
from app.schemas import PredictionResponse
from app.core.logging_config import setup_logging

# --- アプリケーションの起動・終了時に実行する処理 ---
service_container = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    setup_logging()
    service_container["prediction_service"] = PredictionService()
    yield
    # 終了時
    service_container.clear()

# --- FastAPIアプリケーションのインスタンス化 ---
app = FastAPI(
    title="Prediction API",
    description="気象情報と月齢からavg_amountを予測するAPI",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORSミドルウェアの設定 ---
origins = [
    "http://localhost:3001",
    "https://bakuwaki-yoho.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# (これ以降のエンドポイント定義は変更ありません)
@app.get("/predict/week", response_model=List[PredictionResponse], tags=["Prediction"])
async def get_weekly_prediction():
    prediction_service = service_container.get("prediction_service")
    if not prediction_service:
        raise HTTPException(status_code=500, detail="予測サービスが初期化されていません。")
    try:
        predictions = await prediction_service.predict_weekly()
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"予測の処理中にエラーが発生しました: {e}")

@app.get("/", tags=["General"])
def read_root():
    return {"status": "ok"}
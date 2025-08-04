from pydantic import BaseModel, Field
from typing import List, Dict

# --- 外部APIのレスポンス形式を定義 ---

class HourlyWeather(BaseModel):
    """Open-Meteo APIの毎時データのスキーマ"""
    time: List[str]
    temperature_2m: List[float] = Field(..., alias='temperature_2m')
    precipitation: List[float]
    wind_speed_10m: List[float] = Field(..., alias='wind_speed_10m')
    wind_direction_10m: List[int] = Field(..., alias='wind_direction_10m')

class DailyWeather(BaseModel):
    """Open-Meteo APIの日次データのスキーマ"""
    time: List[str]
    weather_code: List[int] = Field(..., alias='weather_code')
    temperature_2m_max: List[float] = Field(..., alias='temperature_2m_max')
    temperature_2m_min: List[float] = Field(..., alias='temperature_2m_min')
    precipitation_probability_max: List[int] = Field(..., alias='precipitation_probability_max')
    wind_direction_10m_dominant: List[int] = Field(..., alias='wind_direction_10m_dominant')

class WeatherApiResponse(BaseModel):
    """Open-Meteo APIの全体レスポンスのスキーマ"""
    latitude: float
    longitude: float
    hourly: HourlyWeather
    daily: DailyWeather

class MoonInfo(BaseModel):
    """tide736.net APIの月齢情報のスキーマ"""
    age: float

class ChartDetail(BaseModel):
    """tide736.net APIのチャート詳細スキーマ"""
    moon: MoonInfo

class TideChart(BaseModel):
    """tide736.net APIのチャート部分のスキーマ"""
    chart: Dict[str, ChartDetail]

class TideApiResponse(BaseModel):
    """tide736.net APIの全体レスポンスのスキーマ"""
    tide: TideChart


# --- このAPIがクライアントに返すレスポンス形式を定義 ---

class PredictionResponse(BaseModel):
    """APIの最終的なレスポンスのスキーマ"""
    date: str
    predicted_amount: float
    moon_age: float
    weather_code: int
    temperature_max: float
    temperature_min: float
    precipitation_probability_max: int
    dominant_wind_direction: int
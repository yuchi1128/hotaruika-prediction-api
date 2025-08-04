import httpx
import asyncio # リトライの待ち時間のために追加
from datetime import date, timedelta
from logging import getLogger

from app.schemas import WeatherApiResponse, TideApiResponse

# ロガーの設定
logger = getLogger(__name__)

class DataFetcher:
    """
    外部APIから気象データと月齢データを取得するためのクラス
    """
    # タイムアウトを設定し、リトライ回数を定義
    _client = httpx.AsyncClient(timeout=10.0) # 10秒でタイムアウト
    MAX_RETRIES = 3 # 最大3回リトライ
    RETRY_DELAY = 1 # 初期遅延1秒

    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    TIDE_API_URL = "https://tide736.net/api/get_tide.php"
    
    LATITUDE = 36.6959
    LONGITUDE = 137.2136
    TIMEZONE = "Asia/Tokyo"
    PREFECTURE_CODE = 16
    HARBOR_CODE = 3

    async def get_weather_data(self, start_date: date, end_date: date) -> WeatherApiResponse | None:
        """
        指定された期間の気象データを取得する（こちらもリトライ処理を追加）
        """
        params = {
            "latitude": self.LATITUDE, "longitude": self.LONGITUDE,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_direction_10m_dominant",
            "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m",
            "timezone": self.TIMEZONE, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        }
        
        delay = self.RETRY_DELAY
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.get(self.WEATHER_API_URL, params=params)
                response.raise_for_status()
                return WeatherApiResponse.parse_obj(response.json())
            except httpx.RequestError as e:
                logger.warning(f"気象APIへのリクエストでエラー (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt + 1 == self.MAX_RETRIES:
                    logger.error("気象APIの取得に最終的に失敗しました。")
                    return None
                await asyncio.sleep(delay)
                delay *= 2 # 待ち時間を倍にする
            except Exception as e:
                logger.error(f"気象API処理中に予期せぬエラー: {e}")
                return None
        return None

    async def get_moon_age(self, target_date: date) -> float | None:
        """
        指定された日付の月齢を取得する（リトライ処理を追加）
        """
        params = {
            "pc": self.PREFECTURE_CODE, "hc": self.HARBOR_CODE,
            "yr": target_date.year, "mn": target_date.month, "dy": target_date.day,
            "rg": "day"
        }

        delay = self.RETRY_DELAY
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.get(self.TIDE_API_URL, params=params)
                response.raise_for_status()
                data = TideApiResponse.parse_obj(response.json())
                date_str = target_date.isoformat()
                if date_str in data.tide.chart:
                    return data.tide.chart[date_str].moon.age
                logger.warning(f"月齢APIのレスポンスに日付 '{date_str}' が見つかりませんでした。")
                return None
            except httpx.RequestError as e: # タイムアウトや接続エラーをキャッチ
                logger.warning(f"月齢APIへのリクエストでエラー (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt + 1 == self.MAX_RETRIES:
                    logger.error("月齢APIの取得に最終的に失敗しました。")
                    return None
                await asyncio.sleep(delay)
                delay *= 2
            except Exception as e:
                logger.error(f"月齢API処理中に予期せぬエラー: {e}")
                return None
        return None
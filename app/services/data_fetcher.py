import httpx
from datetime import date, timedelta
from logging import getLogger

from app.schemas import WeatherApiResponse, TideApiResponse

# ロガーの設定
logger = getLogger(__name__)

class DataFetcher:
    """
    外部APIから気象データと月齢データを取得するためのクラス
    """
    # 非同期HTTPクライアントをクラス変数として保持し、コネクションを再利用する
    _client = httpx.AsyncClient()

    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    TIDE_API_URL = "https://tide736.net/api/get_tide.php"
    
    # 固定のパラメータ
    LATITUDE = 36.6959
    LONGITUDE = 137.2136
    TIMEZONE = "Asia/Tokyo"
    PREFECTURE_CODE = 16 # 富山県
    HARBOR_CODE = 3      # 伏木富山港

    async def get_weather_data(self, start_date: date, end_date: date) -> WeatherApiResponse | None:
        """
        指定された期間の過去・未来の気象データをOpen-Meteo APIから取得する
        """
        params = {
            "latitude": self.LATITUDE,
            "longitude": self.LONGITUDE,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_direction_10m_dominant",
            "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m",
            "timezone": self.TIMEZONE,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        try:
            response = await self._client.get(self.WEATHER_API_URL, params=params)
            response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
            
            # Pydanticモデルを使ってレスポンスを検証・パースする
            return WeatherApiResponse.parse_obj(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"気象APIへのリクエストでHTTPエラーが発生しました: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"気象APIからのデータ取得中に予期せぬエラーが発生しました: {e}")
            return None

    async def get_moon_age(self, target_date: date) -> float | None:
        """
        指定された日付の月齢をtide736.net APIから取得する
        """
        params = {
            "pc": self.PREFECTURE_CODE,
            "hc": self.HARBOR_CODE,
            "yr": target_date.year,
            "mn": target_date.month,
            "dy": target_date.day,
            "rg": "day"
        }
        try:
            response = await self._client.get(self.TIDE_API_URL, params=params)
            response.raise_for_status()
            
            data = TideApiResponse.parse_obj(response.json())
            
            # 指定した日付の月齢を抽出
            date_str = target_date.isoformat()
            if date_str in data.tide.chart:
                return data.tide.chart[date_str].moon.age
            else:
                logger.warning(f"月齢APIのレスポンスに日付 '{date_str}' が見つかりませんでした。")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"月齢APIへのリクエストでHTTPエラーが発生しました: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"月齢APIからのデータ取得中に予期せぬエラーが発生しました: {e}")
            return None
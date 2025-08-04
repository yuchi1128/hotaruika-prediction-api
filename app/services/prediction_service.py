import pandas as pd
import numpy as np
import joblib
import holidays
from datetime import date, timedelta
from pathlib import Path
from logging import getLogger
from typing import List
import json

from app.services.data_fetcher import DataFetcher
from app.services.utils import degree_to_direction
from app.schemas import PredictionResponse

# ロガー設定
logger = getLogger(__name__)

# --- 学習時と同じ前処理関数群を定義 ---
jp_holidays = holidays.country_holidays("JP")
DIRECTION_MAP = {
    '北': 0, '北北東': 1, '北東': 2, '東北東': 3, '東': 4, '東南東': 5, '南東': 6, '南南東': 7,
    '南': 8, '南南西': 9, '南西': 10, '西南西': 11, '西': 12, '西北西': 13, '北西': 14, '北北西': 15
}

def direction_to_radian(direction):
    idx = DIRECTION_MAP.get(direction)
    return 2 * np.pi * idx / 16 if idx is not None else np.nan

def mean_wind_direction(directions):
    radians = np.array([direction_to_radian(d) for d in directions if d in DIRECTION_MAP])
    if len(radians) == 0: return np.nan
    sin_sum = np.sin(radians).mean()
    cos_sum = np.cos(radians).mean()
    mean_rad = np.arctan2(sin_sum, cos_sum)
    if mean_rad < 0: mean_rad += 2 * np.pi
    return int(np.round(mean_rad * 16 / (2 * np.pi))) % 16

class PredictionService:
    def __init__(self, model_dir: Path = Path("app/ml/models")):
        try:
            self.model = joblib.load(model_dir / "lgbm_model.joblib")
            self.scaler_X = joblib.load(model_dir / "scaler_x.joblib")
            self.scaler_y = joblib.load(model_dir / "scaler_y.joblib")
            self.le = joblib.load(model_dir / "label_encoder.joblib")
            self.features_list = joblib.load(model_dir / "features.joblib")
            logger.info("MLモデルと関連ファイルの読み込みに成功しました。")
        except FileNotFoundError as e:
            logger.error(f"モデルファイルが見つかりません: {e.filename}")
            raise

        self.data_fetcher = DataFetcher()

    # <<< この関数を全面的に修正しました >>>
    async def create_features_for_day(self, target_date: date, full_hourly_df: pd.DataFrame, moon_age: float) -> pd.Series:
        """
        指定された1日分の特徴量を生成する。
        全期間の気象データ(`full_hourly_df`)から必要な部分を都度抽出する方式に変更。
        """
        date_dt = pd.to_datetime(target_date)
        row = {
            'date': date_dt, 'year': date_dt.year, 'month': date_dt.month, 'day': date_dt.day,
            'weekday': date_dt.weekday(), 'week_of_year': date_dt.isocalendar().week,
            'week_of_month': (date_dt.day - 1) // 7 + 1, 'day_of_year': date_dt.dayofyear,
            'is_weekend': 1 if date_dt.weekday() in [5, 6] else 0,
            'is_holiday': 1 if date_dt.strftime('%Y-%m-%d') in jp_holidays else 0,
            'moon_age': moon_age
        }

        # 1. 気温・降水量用の時間帯データを抽出 (当日10:00から翌日04:00まで)
        tp_start = pd.to_datetime(f"{target_date} 10:00:00")
        tp_end = pd.to_datetime(f"{target_date + timedelta(days=1)} 04:00:00")
        temp_precip_weather = full_hourly_df[(full_hourly_df['time'] >= tp_start) & (full_hourly_df['time'] <= tp_end)]

        # 2. 風用の時間帯データを抽出 (当日20:00から翌日04:00まで)
        wind_start = pd.to_datetime(f"{target_date} 20:00:00")
        wind_end = pd.to_datetime(f"{target_date + timedelta(days=1)} 04:00:00")
        wind_weather = full_hourly_df[(full_hourly_df['time'] >= wind_start) & (full_hourly_df['time'] <= wind_end)]

        # 3. 時間帯別の特徴量用データを抽出
        tp_10_13 = full_hourly_df[full_hourly_df['time'].dt.date == target_date][full_hourly_df['time'].dt.hour.between(10, 13)]
        tp_14_17 = full_hourly_df[full_hourly_df['time'].dt.date == target_date][full_hourly_df['time'].dt.hour.between(14, 17)]
        tp_18_21 = full_hourly_df[full_hourly_df['time'].dt.date == target_date][full_hourly_df['time'].dt.hour.between(18, 21)]
        tp_22_00 = full_hourly_df[(full_hourly_df['time'].dt.date == target_date) & (full_hourly_df['time'].dt.hour >= 22) | (full_hourly_df['time'].dt.date == target_date + timedelta(days=1)) & (full_hourly_df['time'].dt.hour == 0)]
        tp_01_04 = full_hourly_df[(full_hourly_df['time'].dt.date == target_date + timedelta(days=1)) & (full_hourly_df['time'].dt.hour.between(1, 4))]

        # --- 気象特徴量の計算 ---
        temps = temp_precip_weather['temperature_2m'].dropna()
        row['temperature_mean'] = temps.mean()
        row['temperature_max'] = temps.max()
        row['temperature_min'] = temps.min()
        row['temperature_std'] = temps.std()

        row['temperature_mean_10_13'] = tp_10_13['temperature_2m'].mean()
        row['temperature_mean_14_17'] = tp_14_17['temperature_2m'].mean()
        row['temperature_mean_18_21'] = tp_18_21['temperature_2m'].mean()
        row['temperature_mean_22_0'] = tp_22_00['temperature_2m'].mean()
        row['temperature_mean_1_4'] = tp_01_04['temperature_2m'].mean()
        
        precs = temp_precip_weather['precipitation'].dropna()
        row['precipitation_sum'] = precs.sum()
        row['precipitation_binary'] = 1 if row['precipitation_sum'] > 0 else 0

        row['precipitation_sum_10_13'] = tp_10_13['precipitation'].sum()
        row['precipitation_sum_14_17'] = tp_14_17['precipitation'].sum()
        row['precipitation_sum_18_21'] = tp_18_21['precipitation'].sum()
        row['precipitation_sum_22_0'] = tp_22_00['precipitation'].sum()
        row['precipitation_sum_1_4'] = tp_01_04['precipitation'].sum()
        
        winds = wind_weather['wind_speed_ms'].dropna()
        row['wind_speed_mean'] = winds.mean()
        row['wind_speed_max'] = winds.max()
        row['wind_speed_min'] = winds.min()
        row['wind_speed_std'] = winds.std()
        
        wind_dirs = wind_weather['wind_direction_str'].dropna().tolist()
        row['wind_direction_mean'] = mean_wind_direction(wind_dirs)
        
        return pd.Series(row).fillna(0) # 最後にnanを0で埋める処理を追加して頑健にする

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df['moon_age_sin'] = np.sin(2 * np.pi * df['moon_age'] / 29.53)
        df['moon_age_cos'] = np.cos(2 * np.pi * df['moon_age'] / 29.53)
        df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
        df['temp_x_wind'] = df['temperature_mean'] * df['wind_speed_mean']
        
        known_labels = set(self.le.classes_)
        df['wind_direction_mean'] = df['wind_direction_mean'].apply(
            lambda x: x if x in known_labels else pd.Series(self.le.classes_).mode()[0]
        )
        df['wind_direction_encoded'] = self.le.transform(df['wind_direction_mean'])
        
        cols_for_lag = [c for c in self.features_list if '_lag' not in c and c in df.columns]
        cols_for_lag = [c for c in cols_for_lag if c not in ['year', 'month', 'week_of_month', 'is_weekend', 'is_holiday', 'weekday_sin', 'weekday_cos']]
        for col in cols_for_lag:
            df[f'{col}_lag1'] = df[col].shift(1)
            df[f'{col}_lag2'] = df[col].shift(2)
        return df

    async def predict_weekly(self) -> List[PredictionResponse]:
        today = date.today()
        start_date_fetch = today - timedelta(days=2)
        end_date_fetch = today + timedelta(days=7)
        weather_api_data = await self.data_fetcher.get_weather_data(start_date_fetch, end_date_fetch)
        if not weather_api_data:
            raise Exception("気象データの取得に失敗しました。")
            
        hourly_df = pd.DataFrame(weather_api_data.hourly.dict())
        hourly_df['time'] = pd.to_datetime(hourly_df['time'])
        hourly_df['wind_speed_ms'] = (hourly_df['wind_speed_10m'] * 1000 / 3600).round(1)
        hourly_df['wind_direction_str'] = hourly_df['wind_direction_10m'].apply(degree_to_direction)
        daily_df = pd.DataFrame(weather_api_data.daily.dict())
        daily_df['time'] = pd.to_datetime(daily_df['time']).dt.date
        
        all_days_features = []
        total_days_to_process = (end_date_fetch - start_date_fetch).days + 1
        for i in range(total_days_to_process):
            target_date = start_date_fetch + timedelta(days=i)
            moon_age = await self.data_fetcher.get_moon_age(target_date)
            if moon_age is None: moon_age = 15.0
            
            # <<< 呼び出し方を修正しました >>>
            # 全期間の hourly_df をそのまま渡す
            feature_series = await self.create_features_for_day(target_date, hourly_df, moon_age)
            all_days_features.append(feature_series)
            
        feature_df = pd.DataFrame(all_days_features)
        feature_df.ffill(inplace=True)
        feature_df.bfill(inplace=True)
        engineered_df = self._engineer_features(feature_df)
        predict_df = engineered_df.iloc[2:9].copy()
        
        input_data_json = json.dumps(
            predict_df[self.features_list].to_dict(orient='records'),
            indent=2, ensure_ascii=False
        )
        logger.info(f"モデルへの入力データ(スケーリング前):\n{input_data_json}")

        X_scaled = self.scaler_X.transform(predict_df[self.features_list])
        y_pred_scaled = self.model.predict(X_scaled)
        y_pred = self.scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
        
        predictions = []
        for i, pred_value in enumerate(y_pred):
            target_date = today + timedelta(days=i)
            daily_info = daily_df[daily_df['time'] == target_date].iloc[0]
            response = PredictionResponse(
                date=target_date.isoformat(),
                predicted_amount=pred_value,
                moon_age=predict_df.iloc[i]['moon_age'],
                weather_code=daily_info['weather_code'],
                temperature_max=daily_info['temperature_2m_max'],
                temperature_min=daily_info['temperature_2m_min'],
                precipitation_probability_max=daily_info['precipitation_probability_max'],
                dominant_wind_direction=daily_info['wind_direction_10m_dominant']
            )
            predictions.append(response)
        return predictions
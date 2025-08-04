# 1. ベースとなるPython環境を選択
FROM python:3.12-slim

# 2. コンテナのタイムゾーンをアジア/東京に設定
ENV TZ=Asia/Tokyo

# 2. OSのパッケージリストを更新し、LightGBMが必要とする共有ライブラリをインストール
#    -y でインストールの確認を自動化
#    --no-install-recommends で不要な推奨パッケージを省き、イメージを軽量に保つ
#    最後にキャッシュを削除してイメージサイズをさらに削減する
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# 3. OSのパッケージリストを更新し、LightGBMが必要とする共有ライブラリをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# 4. 作業ディレクトリをコンテナ内に作成
WORKDIR /app

# 5. 依存ライブラリの定義ファイルを先にコピー
COPY requirements.txt .

# 6. 依存ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# 7. アプリケーションのソースコードをコピー
COPY ./app /app/app

# 8. APIが使用するポートを外部に公開
EXPOSE 8000

# 9. コンテナ起動時に実行するコマンドを指定
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
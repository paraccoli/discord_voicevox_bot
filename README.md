# VOICEVOX Discord 読み上げボット

VOICEVOXエンジンを使用してDiscordのテキストチャンネルの内容を音声に変換し、ボイスチャンネルで自動読み上げする機能を提供するボットです。

## 機能

- 様々な話者（キャラクター）による音声合成
- テキストチャンネルの自動読み上げ機能
- ユーザー毎・サーバー毎のデフォルト話者設定
- 音声キャッシュ機能による高速な応答

## セットアップ手順

### 前提条件

- Python 3.8以上
- [VOICEVOX ENGINE](https://voicevox.hiroshiba.jp/) がインストールされ、実行されていること
- Discordボットトークン

### VOICEVOXのインストール

#### Windows

1. [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)から「VOICEVOX」をダウンロードします
2. ダウンロードしたインストーラーを実行し、指示に従ってインストールします
3. インストール完了後、VOICEVOXを起動します
4. 「設定」タブで「エンジンのみを起動」を選択できます（UIが必要ない場合）
5. デフォルトでは`http://localhost:50021`でエンジンが起動します

#### Mac

1. [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)からMac版をダウンロードします
2. ダウンロードしたdmgファイルを開き、アプリケーションフォルダにドラッグ＆ドロップします
3. VOICEVOXを起動し、「設定」で「エンジンのみを起動」を選択できます

#### Linux (Docker)

1. Dockerをインストールします
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   ```

2. VOICEVOXのDockerイメージを取得して実行します
   ```bash
   docker pull voicevox/voicevox_engine:cpu-ubuntu20.04-latest
   docker run --rm -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
   ```

3. 起動後、`http://localhost:50021/docs`にアクセスしてエンジンが正常に動作しているか確認できます

#### Linux (CLI/コマンドライン版)

VOICEVOXエンジンをGUI無しでコマンドラインから直接使用する方法:

1. 依存パッケージをインストール
   ```bash
   sudo apt update
   sudo apt install -y wget p7zip-full python3 python3-pip
   ```

2. VOICEVOXエンジンをダウンロードして展開
   ```bash
   # 最新バージョンのエンジンをダウンロード (最新バージョン番号は公式サイトで確認してください)
   wget https://github.com/VOICEVOX/voicevox_engine/releases/download/0.23.0/voicevox_engine-linux-cpu-x64-0.23.0.7z.001
   wget https://github.com/VOICEVOX/voicevox_engine/releases/download/0.23.0/voicevox_engine-linux-cpu-x64-0.23.0.7z.002
   wget https://github.com/VOICEVOX/voicevox_engine/releases/download/0.23.0/voicevox_engine-linux-cpu-x64-0.23.0.7z.003
   
   # 7z形式のファイルを展開 (分割されたファイルは自動的に結合されます)
   7z x voicevox_engine-linux-cpu-x64-0.23.0.7z.001 -ovoicevox_engine
   
   # VOICEVOXエンジンのディレクトリに移動
   cd voicevox_engine
   ```

3. 必要なPythonパッケージをインストール
   ```bash
   pip3 install -r requirements.txt
   ```

4. VOICEVOXエンジンを起動
   ```bash
   # バックグラウンドで実行する場合
   python3 run.py --host localhost --port 50021 > voicevox.log 2>&1 &
   # または、フォアグラウンドで実行する場合
   python3 run.py --host localhost --port 50021
   ```

5. エンジンが正常に動作しているか確認
   ```bash
   curl http://localhost:50021/version
   ```

6. エンジン使用後、バックグラウンド実行の場合は以下のコマンドで停止できます
   ```bash
   # プロセスIDを検索
   ps aux | grep run.py
   # 見つかったプロセスIDを使って停止
   kill [プロセスID]
   ```

### Discordボットのインストール

1. リポジトリをクローンまたはダウンロード

2. 必要なパッケージをインストール
   ```
   pip install -r requirements.txt
   ```

3. `.env`ファイルを作成し、Discordトークンを設定
   ```
   DISCORD_TOKEN=あなたのDiscordボットトークン
   VOICEVOX_API_URL=http://localhost:50021
   ```

4. VOICEVOXエンジンを起動

5. ボットを起動
   ```
   python bot.py
   ```

## 使い方

### 基本的な流れ

1. `/join` コマンドでボットをボイスチャンネルに参加させます
2. `/setup #チャンネル名` コマンドで読み上げるテキストチャンネルを指定します
3. 指定したチャンネルに投稿されたメッセージが自動で読み上げられます
4. `/leave` コマンドでボットを退出させます

### 基本コマンド

- `/join` - ボットをあなたのボイスチャンネルに参加させる
- `/leave` - ボットをボイスチャンネルから退出させる
- `/setup <テキストチャンネル> [有効化/無効化]` - 自動読み上げするチャンネルを設定する (チャンネル管理権限が必要)
- `/help` - コマンドの使い方を表示する

### 音声設定コマンド

- `/list_speakers` - 利用可能な話者のリストを表示
- `/set_speaker <話者ID> [個人用/サーバー全体]` - デフォルト話者を設定 (サーバー全体設定にはサーバー管理権限が必要)

### 音声制御

- `/pause` - 読み上げを一時停止
- `/resume` - 一時停止中の読み上げを再開

## 設定

- `config/settings.ini` - ボットの基本設定
- `config/permissions.json` - コマンド実行権限の設定
- `config/read_channels.json` - 読み上げチャンネルの設定（自動生成）

## 必要な権限

- `/setup` コマンドを使用するには、サーバーでの「チャンネル管理」権限が必要です
- `/set_speaker` コマンドでサーバー全体の設定を変更するには「サーバーの管理」権限が必要です
- 権限設定は `config/permissions.json` ファイルで調整できます

## トラブルシューティング

### VOICEVOXエンジンが起動しない場合
- ポート50021が他のアプリケーションで使用されていないか確認します
- VOICEVOXの公式サイトから最新版をダウンロードして再インストールしてください
- Dockerを使用している場合は、Dockerが正常に動作しているか確認してください

### 音声が生成されない場合
- VOICEVOXエンジンが起動しているか確認します
- `.env`ファイルのVOICEVOX_API_URLが正しいか確認します
- コンソールログでエラーメッセージを確認し、対応するエラーを修正します

### CLI版での一般的な問題
- 「モジュールが見つからない」エラーが発生した場合は、必要なPythonパッケージがすべてインストールされているか確認してください
- ポート競合が発生する場合は、`--port`引数で別のポートを指定してください
- メモリ不足エラーが発生する場合は、`--cpu-num-threads`引数でCPUスレッド数を制限してください

## ライセンス

このプロジェクトは[MITライセンス](LICENSE)のもとで公開されています。

---

VOICEVOXは[ヒホ](https://twitter.com/hiho_karuta)さんによるフリーソフトウェアです。
各話者の利用規約については[VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)をご確認ください。
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import logging
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import datetime
import sys
import configparser

# utils モジュールへのパスを追加
sys.path.insert(0, os.getcwd())
from utils.voicevox_api import VoicevoxAPI
from utils.audio_cache import cache_manager

# 環境変数の読み込み
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ロギング設定
def setup_logger():
    """アプリケーション全体のロギング設定"""
    # ログディレクトリの作成
    os.makedirs("logs", exist_ok=True)
    
    # 現在の日時を使ってログファイル名を設定
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    log_file = f"logs/discord_bot_{timestamp}.log"
    
    # ロガーの設定
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)  # INFOからWARNINGに変更（本番環境用）
    
    # コンソールへの出力設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # INFOからWARNINGに変更
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # ファイルへの出力設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)  # ファイルにはINFOレベルでログを残す
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # ハンドラをロガーに追加
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# インテントの設定 (必要な権限を有効化)
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容へのアクセスを有効化
intents.voice_states = True     # ボイスステートへのアクセスを有効化

# Botの初期化
bot = commands.Bot(command_prefix='!', intents=intents)
logger = setup_logger()

# テキスト読み上げの設定
voicevox_api = VoicevoxAPI()
config = configparser.ConfigParser()
config.read('config/settings.ini')
max_message_length = config.getint('DEFAULT', 'max_message_length', fallback=100)

async def load_extensions():
    """Cogを読み込む"""
    # audio_control Cogを読み込み
    try:
        await bot.load_extension('cogs.audio_control')
        logger.info("audio_control Cogを読み込みました")
    except Exception as e:
        logger.error(f"audio_control Cogの読み込みに失敗: {e}")
    
    # スラッシュコマンドの読み込み（slash_commandsはすべてのコマンドを自動で読み込む）
    try:
        await bot.load_extension('interactions.slash_commands')
        logger.info("slash_commands Cogを読み込みました")
    except Exception as e:
        logger.error(f"slash_commands Cogの読み込みに失敗: {e}")
    
    # 注: stats.pyコマンドは個別に読み込まない
    # slash_commands.pyがすべてのコマンドを自動で読み込むため、
    # ここで個別に読み込むとCommandAlreadyRegisteredエラーになる
    
@bot.event
async def on_ready():
    """Botの起動完了時に実行"""
    logger.info(f'{bot.user.name} ({bot.user.id}) としてログインしました。')
    logger.info('------')
    
    # スラッシュコマンドをDiscordに同期
    logger.info("スラッシュコマンドを同期中...")
    try:
        synced = await bot.tree.sync()
        logger.info(f"{len(synced)} 個のコマンドを同期しました")
    except Exception as e:
        logger.error(f"コマンド同期エラー: {e}")
    
    # タスクモジュールの読み込みと初期化
    try:
        from interactions.tasks.task import setup as setup_tasks
        tasks_module = setup_tasks(bot)
        await tasks_module.setup()
        logger.info("タスクモジュールを初期化しました")
    except Exception as e:
        logger.error(f"タスクモジュールの初期化に失敗: {e}")

@bot.event
async def on_message(message):
    """メッセージ受信時に実行"""
    # 自分自身のメッセージは無視
    if message.author == bot.user:
        return
        
    # コマンドの処理
    await bot.process_commands(message)
    
    # 自動読み上げ処理
    await process_auto_reading(message)

async def process_auto_reading(message):
    """自動読み上げ処理を行う"""
    # DMの場合は無視
    if not message.guild:
        return
        
    # setup_commandがまだ初期化されていない場合
    if not hasattr(bot, 'setup_command'):
        return
        
    # このチャンネルが読み上げ対象か確認
    if not bot.setup_command.is_read_channel(message.guild.id, message.channel.id):
        return
        
    # オーディオコントローラを取得
    audio_control = bot.get_cog('AudioControl')
    if not audio_control:
        logger.error("オーディオ制御システムが利用できません")
        return
        
    # ボットがボイスチャンネルに接続しているか確認
    if not audio_control.is_connected(message.guild.id):
        return
    
    # メッセージ内容を取得
    text = message.content
    
    # 空のメッセージは無視
    if not text.strip():
        return
    
    # URLやコードブロックなど読み上げ不要な部分を除外
    # TODO: 必要に応じてメッセージのフィルタリングを実装
    
    # テキストの最大長をチェック
    if len(text) > max_message_length:
        text = text[:max_message_length] + "..."
    
    try:
        # 話者ID設定
        speaker_id = None
        
        # set_speaker_commandから話者ID設定を取得
        if hasattr(bot, 'set_speaker_command'):
            speaker_id = bot.set_speaker_command.get_default_speaker(
                message.author.id, 
                message.guild.id
            )
        else:
            # デフォルト値を使用
            speaker_id = 1
        
        # キャッシュキーを生成
        cache_key = cache_manager.generate_cache_key(text, speaker_id)
        cache_path = cache_manager.get_cache_path(cache_key)
        
        # システム統計オブジェクトがあれば、メッセージ処理をカウント
        if hasattr(bot, 'system_stats'):
            bot.system_stats.increment_messages()
            # 読み上げる単語数をカウント
            bot.system_stats.add_words(text)
            
            # メッセージ処理時のステータス更新は削除（定期タスクに任せる）
        
        audio_path = None
        if cache_path:
            # キャッシュがある場合はそれを使用
            audio_path = cache_path
            # キャッシュヒットを記録
            if hasattr(bot, 'system_stats'):
                bot.system_stats.record_cache_hit()
        else:
            # 音声合成リクエスト
            audio_path = await voicevox_api.create_audio(text, speaker_id)
            # キャッシュミスを記録
            if hasattr(bot, 'system_stats'):
                bot.system_stats.record_cache_miss()
                
            if audio_path:
                # キャッシュに追加
                await cache_manager.add_to_cache(cache_key, audio_path, text, speaker_id)
        
        if not audio_path:
            logger.error(f"音声の生成に失敗: {text}")
            return
        
        # オーディオをキューに追加
        await audio_control.play_audio(message.guild.id, audio_path, message.author.id, text)
        
        logger.info(f"自動読み上げ: \"{text}\" (話者ID: {speaker_id}, ユーザー: {message.author.name})")
        
    except Exception as e:
        logger.error(f"自動読み上げエラー: {e}")

async def main():
    """メイン関数"""
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# Botを起動
if __name__ == '__main__':
    if not TOKEN:
        logger.error("エラー: DISCORD_TOKENが設定されていません。.envファイルを確認してください。")
        exit(1)
    
    # 一時ディレクトリが存在することを確認
    os.makedirs("temp", exist_ok=True)
    os.makedirs("temp/cache", exist_ok=True)
    
    # 統計・タスク用ディレクトリの作成
    os.makedirs("stats", exist_ok=True)
    os.makedirs("stats/hourly", exist_ok=True)
    
    # Botを起動
    asyncio.run(main())
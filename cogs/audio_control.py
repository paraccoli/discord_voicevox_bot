import discord
from discord.ext import commands
import asyncio
import os
import logging
import sys
from collections import deque
import traceback

# utils/audio_cacheをインポートするためのパス設定
sys.path.insert(0, os.getcwd())
from utils.audio_cache import AudioCache

class AudioControl(commands.Cog):
    """音声制御クラス"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # サーバーIDごとのVoiceClientを管理
        self.audio_queues = {}   # サーバーIDごとの音声キューを管理
        self.is_playing = {}     # サーバーIDごとの再生状態を管理
        self.logger = logging.getLogger("audio_control")
        self.cache_manager = AudioCache()
        self.auto_disconnect_tasks = {}  # 自動切断タスクを管理

    async def connect_to_voice(self, guild_id, channel_id):
        """指定されたボイスチャンネルに接続"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                self.logger.error(f"サーバーが見つかりません: {guild_id}")
                return False
                
            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                self.logger.error(f"ボイスチャンネルが見つかりません: {channel_id}")
                return False
                
            # 既に接続している場合は切断
            if guild_id in self.voice_clients and self.voice_clients[guild_id]:
                await self.disconnect_from_voice(guild_id)
                
            # ボイスチャンネルに接続
            voice_client = await channel.connect()
            self.voice_clients[guild_id] = voice_client
            self.audio_queues[guild_id] = deque()
            self.is_playing[guild_id] = False
            
            self.logger.info(f"ボイスチャンネルに接続: {channel.name} (サーバー: {guild.name})")
            return True
            
        except Exception as e:
            self.logger.error(f"ボイスチャンネル接続エラー: {e}")
            traceback.print_exc()
            return False

    async def disconnect_from_voice(self, guild_id):
        """ボイスチャンネルから切断"""
        try:
            if guild_id in self.voice_clients and self.voice_clients[guild_id]:
                if self.voice_clients[guild_id].is_connected():
                    await self.voice_clients[guild_id].disconnect()
                    
                # 自動切断タスクをキャンセル
                if guild_id in self.auto_disconnect_tasks and self.auto_disconnect_tasks[guild_id]:
                    self.auto_disconnect_tasks[guild_id].cancel()
                    self.auto_disconnect_tasks[guild_id] = None
                    
                self.voice_clients[guild_id] = None
                self.audio_queues[guild_id] = deque()
                self.is_playing[guild_id] = False
                self.logger.info(f"ボイスチャンネルから切断 (サーバーID: {guild_id})")
                return True
                
        except Exception as e:
            self.logger.error(f"ボイスチャンネル切断エラー: {e}")
            traceback.print_exc()
            
        return False

    def is_connected(self, guild_id):
        """ボイスチャンネルに接続しているかどうかを確認"""
        return (guild_id in self.voice_clients and 
                self.voice_clients[guild_id] is not None and 
                self.voice_clients[guild_id].is_connected())

    async def play_audio(self, guild_id, audio_path, user_id=None, message_text=None):
        """音声ファイルを再生キューに追加"""
        if not self.is_connected(guild_id):
            self.logger.warning(f"ボイスチャンネルに接続していません (サーバーID: {guild_id})")
            return False
            
        # 既に同じテキストがキューにある場合はスキップ（重複読み上げ防止）
        if message_text:
            for item in self.audio_queues.get(guild_id, []):
                if item.get("text") == message_text:
                    self.logger.debug(f"重複メッセージをスキップ: {message_text[:20]}...")
                    return True
        
        # キューに追加
        self.audio_queues[guild_id].append({
            "path": audio_path,
            "user_id": user_id,
            "text": message_text
        })
        
        # 再生中でなければ再生を開始
        if not self.is_playing[guild_id]:
            asyncio.create_task(self._play_next(guild_id))
            
        return True

    async def _play_next(self, guild_id):
        """キューの次の音声を再生"""
        if not self.is_connected(guild_id) or not self.audio_queues[guild_id]:
            self.is_playing[guild_id] = False
            return
            
        self.is_playing[guild_id] = True
        
        # キューから次の音声を取得
        audio_data = self.audio_queues[guild_id].popleft()
        audio_path = audio_data["path"]
        
        try:
            # 音声ファイルが存在するか確認
            if not os.path.exists(audio_path):
                self.logger.error(f"音声ファイルが見つかりません: {audio_path}")
                await self._play_next(guild_id)  # 次の音声へ
                return
                
            # 音声を再生
            voice_client = self.voice_clients[guild_id]
            
            # FFmpegオプションを設定
            ffmpeg_options = {
                'options': '-vn -loglevel error'
            }
            
            source = discord.FFmpegPCMAudio(audio_path, **ffmpeg_options)
            voice_client.play(source, after=lambda e: self._audio_finished(e, guild_id, audio_path))
            
        except Exception as e:
            self.logger.error(f"オーディオ再生エラー: {e}")
            traceback.print_exc()
            # エラーが発生した場合でも次の音声を再生
            await self._play_next(guild_id)

    def _audio_finished(self, error, guild_id, audio_path):
        """音声再生が終了したときに呼ばれるコールバック"""
        # エラーが発生した場合はログに記録
        if error:
            self.logger.error(f"オーディオ再生エラー: {error}")
            
        # テンポラリディレクトリのファイルを削除（キャッシュは保持）
        try:
            if audio_path and os.path.exists(audio_path) and "temp/" in audio_path:
                # キャッシュファイルなら削除しない（キャッシュマネージャが管理）
                if not audio_path.startswith(self.cache_manager.cache_dir):
                    os.remove(audio_path)
                    self.logger.debug(f"一時ファイルを削除: {audio_path}")
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {e}")
            
        # 次の音声を再生
        asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.bot.loop)

    def clear_queue(self, guild_id):
        """再生キューをクリア"""
        if guild_id in self.audio_queues:
            self.audio_queues[guild_id].clear()
            self.logger.info(f"再生キューをクリア (サーバーID: {guild_id})")
            return True
        return False

async def setup(bot):
    """Cogを登録"""
    await bot.add_cog(AudioControl(bot))
    return bot.get_cog('AudioControl')
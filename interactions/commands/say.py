#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging
import sys
import os

# utils/voicevox_apiをインポートするためのパス設定
sys.path.insert(0, os.getcwd())
from utils.voicevox_api import VoicevoxAPI
from utils.audio_cache import cache_manager

class SayCommand:
    """テキスト読み上げコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.say")
        self.voicevox_api = VoicevoxAPI()
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="say",
            description="指定したテキストを読み上げます"
        )
        @app_commands.describe(
            text="読み上げるテキスト",
            speaker_id="話者ID（指定しない場合はデフォルト）"
        )
        async def say(
            interaction: discord.Interaction,
            text: str,
            speaker_id: int = None
        ):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "say"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
                
            # ボットがボイスチャンネルに接続しているか確認
            audio_control = self.bot.get_cog('AudioControl')
            if not audio_control:
                await interaction.response.send_message("オーディオ制御システムが利用できません。", ephemeral=True)
                return
                
            if not audio_control.is_connected(interaction.guild.id):
                await interaction.response.send_message("ボットはボイスチャンネルに参加していません。`/join`コマンドを使用してください。", ephemeral=True)
                return
                
            # テキストの最大長をチェック
            max_length = 200  # 最大文字数
            if len(text) > max_length:
                await interaction.response.send_message(f"テキストが長すぎます。{max_length}文字以内にしてください。", ephemeral=True)
                return
                
            try:
                # 処理中表示
                await interaction.response.defer(ephemeral=True)
                
                # 話者IDが指定されていない場合、ユーザー設定を使用
                if speaker_id is None and hasattr(self.bot, 'set_speaker_command'):
                    speaker_id = self.bot.set_speaker_command.get_default_speaker(
                        interaction.user.id,
                        interaction.guild.id
                    )
                # さらにデフォルト値
                if speaker_id is None:
                    speaker_id = 1
                
                # キャッシュキーを生成
                cache_key = cache_manager.generate_cache_key(text, speaker_id)
                cache_path = cache_manager.get_cache_path(cache_key)
                
                # システム統計に反映
                if hasattr(self.bot, 'system_stats'):
                    self.bot.system_stats.add_words(text)
                
                audio_path = None
                if cache_path:
                    # キャッシュがある場合はそれを使用
                    audio_path = cache_path
                    # キャッシュヒットを記録
                    if hasattr(self.bot, 'system_stats'):
                        self.bot.system_stats.record_cache_hit()
                else:
                    # 音声合成リクエスト
                    audio_path = await self.voicevox_api.create_audio(text, speaker_id)
                    # キャッシュミスを記録
                    if hasattr(self.bot, 'system_stats'):
                        self.bot.system_stats.record_cache_miss()
                    
                    if audio_path and cache_key:
                        # キャッシュに追加
                        await cache_manager.add_to_cache(cache_key, audio_path, text, speaker_id)
                
                if not audio_path:
                    await interaction.followup.send("音声の生成に失敗しました。", ephemeral=True)
                    return
                
                # オーディオをキューに追加
                await audio_control.play_audio(interaction.guild.id, audio_path, interaction.user.id, text)
                
                await interaction.followup.send(f"「{text}」を読み上げています。", ephemeral=True)
                self.logger.info(f"テキスト読み上げ: \"{text}\" (話者ID: {speaker_id}, ユーザー: {interaction.user.name})")
                
            except Exception as e:
                self.logger.error(f"読み上げエラー: {e}")
                await interaction.followup.send(f"読み上げ処理中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    SayCommand(bot)
    return True
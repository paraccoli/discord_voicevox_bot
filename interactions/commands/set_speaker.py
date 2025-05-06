#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging
import json
import os
import sys

# utils/voicevox_apiをインポートするためのパス設定
sys.path.insert(0, os.getcwd())
from utils.voicevox_api import VoicevoxAPI

class SetSpeakerCommand:
    """デフォルト話者設定コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.set_speaker")
        self.voicevox_api = VoicevoxAPI()
        
        # ユーザー・サーバー別の話者設定ファイルのパス
        self.user_settings_path = "config/user_speakers.json"
        self.server_settings_path = "config/server_speakers.json"
        
        # 設定を読み込み
        self.user_settings = self._load_settings(self.user_settings_path)
        self.server_settings = self._load_settings(self.server_settings_path)
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="set_speaker",
            description="デフォルトの話者を設定します"
        )
        @app_commands.describe(
            speaker_id="話者ID (/list_speakers で確認できます)",
            scope="設定の適用範囲 (個人用またはサーバー全体)"
        )
        @app_commands.choices(scope=[
            app_commands.Choice(name="個人用", value="user"),
            app_commands.Choice(name="サーバー全体", value="server")
        ])
        async def set_speaker(
            interaction: discord.Interaction,
            speaker_id: int,
            scope: app_commands.Choice[str] = None
        ):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "set_speaker"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            # DMではサーバー全体設定を許可しない
            if scope and scope.value == "server" and not interaction.guild:
                await interaction.response.send_message("DMでは個人用設定のみ可能です。", ephemeral=True)
                return
            
            # スコープが指定されていない場合のデフォルト値
            if not scope:
                scope = app_commands.Choice(name="個人用", value="user")
            
            try:
                # レスポンスをディファード
                await interaction.response.defer(ephemeral=True)
                
                # 話者IDの検証
                speaker_info = await self._validate_speaker_id(speaker_id)
                if not speaker_info:
                    await interaction.followup.send(f"話者ID {speaker_id} は無効です。`/list_speakers` で有効なIDを確認してください。", ephemeral=True)
                    return
                
                # 設定の保存
                if scope.value == "user":
                    self.user_settings[str(interaction.user.id)] = speaker_id
                    await self._save_settings(self.user_settings_path, self.user_settings)
                    await interaction.followup.send(
                        f"あなたのデフォルト話者を [{speaker_info}] (ID: {speaker_id}) に設定しました。",
                        ephemeral=True
                    )
                else:  # server
                    # サーバー管理権限チェック
                    if not interaction.user.guild_permissions.manage_guild:
                        await interaction.followup.send("サーバー全体の設定を変更するには、サーバー管理権限が必要です。", ephemeral=True)
                        return
                        
                    self.server_settings[str(interaction.guild.id)] = speaker_id
                    await self._save_settings(self.server_settings_path, self.server_settings)
                    await interaction.followup.send(
                        f"サーバーのデフォルト話者を [{speaker_info}] (ID: {speaker_id}) に設定しました。",
                        ephemeral=False  # サーバー設定は全員に表示
                    )
                
                self.logger.info(f"{scope.value} スコープで話者 {speaker_id} を設定しました (ユーザー: {interaction.user.name})")
                
            except Exception as e:
                self.logger.error(f"話者設定エラー: {e}")
                await interaction.followup.send(f"話者設定中にエラーが発生しました: {e}", ephemeral=True)
    
    def _load_settings(self, path):
        """設定ファイルを読み込む"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"設定ファイルの読み込みに失敗: {e}")
        return {}
    
    async def _save_settings(self, path, settings):
        """設定ファイルを保存する"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"設定ファイルの保存に失敗: {e}")
            return False
    
    async def _validate_speaker_id(self, speaker_id):
        """話者IDが有効かどうか確認する"""
        speakers = await self.voicevox_api.get_speakers()
        for speaker in speakers:
            styles = speaker.get("styles", [])
            for style in styles:
                if style.get("id") == speaker_id:
                    return f"{speaker.get('name')} ({style.get('name')})"
        return None
    
    def get_user_speaker(self, user_id):
        """ユーザーのデフォルト話者IDを取得"""
        return self.user_settings.get(str(user_id))
    
    def get_server_speaker(self, server_id):
        """サーバーのデフォルト話者IDを取得"""
        return self.server_settings.get(str(server_id))
    
    def get_default_speaker(self, user_id, server_id=None):
        """
        ユーザーまたはサーバーのデフォルト話者IDを取得
        優先順位: ユーザー設定 > サーバー設定 > デフォルト設定(1)
        """
        user_speaker = self.get_user_speaker(user_id)
        if user_speaker is not None:
            return user_speaker
            
        if server_id:
            server_speaker = self.get_server_speaker(server_id)
            if server_speaker is not None:
                return server_speaker
                
        # コンフィグからデフォルト値を取得
        import configparser
        config = configparser.ConfigParser()
        config.read('config/settings.ini')
        return config.getint('DEFAULT', 'default_speaker_id', fallback=1)

def setup(bot):
    """コマンドの初期化"""
    bot.set_speaker_command = SetSpeakerCommand(bot)
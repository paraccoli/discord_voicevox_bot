#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging
import sys
import os
import json

class SetupCommand:
    """読み上げチャンネル設定コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.setup")
        
        # 読み上げチャンネル設定ファイルのパス
        self.settings_path = "config/read_channels.json"
        
        # 設定を読み込み
        self.read_channels = self._load_settings()
        
        # ボットにチャンネル設定を保存（他のモジュールからアクセス用）
        self.bot.read_channels = self.read_channels
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="setup",
            description="自動読み上げを行うテキストチャンネルを設定します"
        )
        @app_commands.describe(
            channel="読み上げるテキストチャンネル（指定しない場合は現在のチャンネル）",
            enable="有効化 / 無効化の切り替え"
        )
        @app_commands.choices(enable=[
            app_commands.Choice(name="有効化", value="enable"),
            app_commands.Choice(name="無効化", value="disable")
        ])
        async def setup(
            interaction: discord.Interaction,
            channel: discord.TextChannel = None,
            enable: app_commands.Choice[str] = None
        ):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "setup"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            # DMでの使用を禁止
            if not interaction.guild:
                await interaction.response.send_message("このコマンドはサーバー内でのみ使用できます。", ephemeral=True)
                return
                
            # サーバー管理権限チェック
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("このコマンドを実行するにはチャンネル管理権限が必要です。", ephemeral=True)
                return
                
            # パラメータの処理
            if channel is None:
                channel = interaction.channel
                
            if enable is None:
                # 現在の設定を確認して反転
                guild_id = str(interaction.guild.id)
                channel_id = str(channel.id)
                
                if guild_id in self.read_channels and channel_id in self.read_channels[guild_id]:
                    enable = app_commands.Choice(name="無効化", value="disable")
                else:
                    enable = app_commands.Choice(name="有効化", value="enable")
            
            try:
                # レスポンスをディファード
                await interaction.response.defer(ephemeral=True)
                
                guild_id = str(interaction.guild.id)
                channel_id = str(channel.id)
                
                # ギルド設定の初期化
                if guild_id not in self.read_channels:
                    self.read_channels[guild_id] = {}
                
                if enable.value == "enable":
                    # チャンネルを読み上げリストに追加
                    self.read_channels[guild_id][channel_id] = {
                        "name": channel.name,
                        "enabled": True,
                        "last_updated": discord.utils.utcnow().isoformat()
                    }
                    
                    await interaction.followup.send(
                        f"✅ {channel.mention} での自動読み上げを有効化しました。ボットがボイスチャンネルに参加している間、このチャンネルのメッセージを読み上げます。"
                    )
                    self.logger.info(f"自動読み上げチャンネルを設定: {channel.name} (サーバー: {interaction.guild.name})", ephemeral=True)
                else:
                    # チャンネルを読み上げリストから削除
                    if guild_id in self.read_channels and channel_id in self.read_channels[guild_id]:
                        del self.read_channels[guild_id][channel_id]
                        
                    await interaction.followup.send(
                        f"❌ {channel.mention} での自動読み上げを無効化しました。"
                    )
                    self.logger.info(f"自動読み上げチャンネルを解除: {channel.name} (サーバー: {interaction.guild.name})", ephemeral=True)
                
                # 設定を保存
                await self._save_settings()
                
            except Exception as e:
                self.logger.error(f"読み上げチャンネル設定エラー: {e}")
                await interaction.followup.send(f"設定中にエラーが発生しました: {e}", ephemeral=True)
    
    def _load_settings(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"設定ファイルの読み込みに失敗: {e}")
                
        return {}
    
    async def _save_settings(self):
        """設定ファイルを保存する"""
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.read_channels, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"設定ファイルの保存に失敗: {e}")
            return False
    
    def is_read_channel(self, guild_id, channel_id):
        """指定されたチャンネルが読み上げチャンネルとして設定されているかを確認"""
        guild_id_str = str(guild_id)
        channel_id_str = str(channel_id)
        
        return (guild_id_str in self.read_channels and 
                channel_id_str in self.read_channels[guild_id_str] and 
                self.read_channels[guild_id_str][channel_id_str].get("enabled", False))

def setup(bot):
    """コマンドの初期化"""
    setup_command = SetupCommand(bot)
    bot.setup_command = setup_command
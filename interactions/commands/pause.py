#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging

class PauseCommand:
    """読み上げ一時停止コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.pause")
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="pause",
            description="読み上げを一時停止します"
        )
        async def pause(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "pause"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            # オーディオコントローラを取得
            audio_control = self.bot.get_cog('AudioControl')
            if not audio_control:
                await interaction.response.send_message("オーディオ制御システムが利用できません。", ephemeral=True)
                return
            
            # ボットがボイスチャンネルに接続しているか確認
            if not audio_control.is_connected(interaction.guild.id):
                await interaction.response.send_message("ボットはボイスチャンネルに参加していません。", ephemeral=True)
                return
                
            try:
                # 一時停止を実行
                result = audio_control.pause_audio(interaction.guild.id)
                
                if result:
                    await interaction.response.send_message("⏸️ 読み上げを一時停止しました。`/resume`で再開できます。")
                    self.logger.info(f"読み上げを一時停止しました (サーバー: {interaction.guild.name})")
                else:
                    await interaction.response.send_message("現在再生中の音声はありません。", ephemeral=True)
                    
            except Exception as e:
                self.logger.error(f"一時停止エラー: {e}")
                await interaction.response.send_message(f"一時停止処理中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    PauseCommand(bot)
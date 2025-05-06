#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging

class ResumeCommand:
    """読み上げ再開コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.resume")
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="resume",
            description="一時停止中の読み上げを再開します"
        )
        async def resume(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "resume"):
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
                # 再生再開を実行
                result = audio_control.resume_audio(interaction.guild.id)
                
                if result:
                    await interaction.response.send_message("▶️ 読み上げを再開しました。")
                    self.logger.info(f"読み上げを再開しました (サーバー: {interaction.guild.name})")
                else:
                    await interaction.response.send_message("一時停止中の音声はありません。", ephemeral=True)
                    
            except Exception as e:
                self.logger.error(f"再開エラー: {e}")
                await interaction.response.send_message(f"再開処理中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    ResumeCommand(bot)
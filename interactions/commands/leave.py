#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging

class LeaveCommand:
    """ボイスチャンネル退出コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.leave")
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="leave",
            description="ボットをボイスチャンネルから退出させます"
        )
        async def leave(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "leave"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            # オーディオコントローラを取得
            audio_control = self.bot.get_cog('AudioControl')
            if not audio_control:
                await interaction.response.send_message("オーディオ制御システムが利用できません。", ephemeral=True)
                return
            
            # ボットが接続中かどうか確認
            if not audio_control.is_connected(interaction.guild.id):
                await interaction.response.send_message("ボットはボイスチャンネルに参加していません。", ephemeral=True)
                return
            
            # 接続中のチャンネルを取得（修正部分）
            # get_connected_channelメソッドの代わりに、直接voice_clientから取得
            channel_mention = "ボイスチャンネル"
            try:
                if (interaction.guild.id in audio_control.voice_clients and 
                    audio_control.voice_clients[interaction.guild.id] and
                    audio_control.voice_clients[interaction.guild.id].channel):
                    channel_mention = audio_control.voice_clients[interaction.guild.id].channel.mention
            except Exception:
                # チャンネル情報の取得に失敗しても処理を続行
                pass
            
            try:
                # レスポンスをディファード
                await interaction.response.defer(ephemeral=True)
                
                # ボイスチャンネルから切断
                # メソッド名を修正 - disconnect_from_guild → disconnect_from_voice
                success = await audio_control.disconnect_from_voice(interaction.guild.id)
                
                if success:
                    await interaction.followup.send(f"👋 {channel_mention} から退出しました", ephemeral=True)
                    self.logger.info(f"ボイスチャンネルから退出しました (サーバー: {interaction.guild.name})")
                else:
                    await interaction.followup.send("退出処理中にエラーが発生しました。", ephemeral=True)
                    
            except Exception as e:
                self.logger.error(f"ボイスチャンネル退出エラー: {e}")
                await interaction.followup.send(f"退出処理中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    LeaveCommand(bot)
    return True
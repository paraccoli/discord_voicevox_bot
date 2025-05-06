#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging

class JoinCommand:
    """ボイスチャンネル参加コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.join")
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="join",
            description="ボットをあなたのボイスチャンネルに参加させます"
        )
        async def join(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "join"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            # ユーザーがボイスチャンネルに接続しているか確認
            if not interaction.user.voice:
                await interaction.response.send_message("先にボイスチャンネルに接続してください。", ephemeral=True)
                return
            
            voice_channel = interaction.user.voice.channel
            
            try:
                # オーディオコントローラを取得
                audio_control = self.bot.get_cog('AudioControl')
                if not audio_control:
                    await interaction.response.send_message("オーディオ制御システムが利用できません。", ephemeral=True)
                    return
                
                # レスポンスをディファード (Botの応答が30秒以内に返らない場合に備える)
                await interaction.response.defer(ephemeral=True)
                
                # ボイスチャンネルに接続 - ここを修正
                # メソッド名を connect_to_channel から connect_to_voice に変更
                # さらに必要なパラメータを追加
                success = await audio_control.connect_to_voice(interaction.guild.id, voice_channel.id)
                
                if success:
                    await interaction.followup.send(f"👋 {voice_channel.mention} に参加しました！", ephemeral=True)
                    self.logger.info(f"ボイスチャンネル {voice_channel.name} に参加しました (サーバー: {interaction.guild.name})")
                else:
                    await interaction.followup.send("ボイスチャンネルへの接続に失敗しました。", ephemeral=True)
                
            except Exception as e:
                self.logger.error(f"ボイスチャンネル接続エラー: {e}")
                await interaction.followup.send(f"ボイスチャンネルへの接続中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    JoinCommand(bot)
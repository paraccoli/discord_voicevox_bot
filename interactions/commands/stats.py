#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands
import logging
import sys
import os
import psutil
import platform
import datetime
import time
import math

# utils/sistema_statsをインポート
sys.path.insert(0, os.getcwd())
from utils.system_stats import SystemStats

class StatsCommand:
    """システム統計情報コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.stats")
        self.sys_stats = SystemStats()
        
        # ボットにシステム統計オブジェクトを保存（他のモジュールからアクセス用）
        self.bot.system_stats = self.sys_stats
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="stats",
            description="ボットとシステムの統計情報を表示します"
        )
        async def stats(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "stats"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            try:
                # 処理中表示
                await interaction.response.defer(ephemeral=True)
                
                # システム統計情報を取得
                cpu_percent = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
                
                # ネットワーク統計
                net_io = psutil.net_io_counters()
                
                # Discordボット統計
                bot_uptime = datetime.datetime.now() - self.sys_stats.start_time
                bot_uptime_str = self._format_timedelta(bot_uptime)
                
                # 埋め込みを作成
                embed = discord.Embed(
                    title="VOICEVOX読み上げBot - システム統計",
                    description="システムとボットの統計情報",
                    color=discord.Color.blue()
                )
                
                # ボット情報
                bot_info = (
                    f"**起動時間:** {bot_uptime_str}\n"
                    f"**読み上げ単語数:** {self.sys_stats.words_read:,} 単語\n"
                    f"**読み上げメッセージ数:** {self.sys_stats.messages_processed:,} メッセージ\n"
                    f"**キャッシュヒット率:** {self.sys_stats.get_cache_hit_ratio():.1f}%"
                )
                embed.add_field(name="ボット統計", value=bot_info, inline=False)
                
                # ネットワーク情報
                net_info = (
                    f"**送信:** {self._format_bytes(net_io.bytes_sent)}\n"
                    f"**受信:** {self._format_bytes(net_io.bytes_recv)}\n"
                    f"**現在の通信速度:** {self._format_bytes(self.sys_stats.get_network_speed())}/秒"
                )
                embed.add_field(name="ネットワーク", value=net_info, inline=True)
                
                # システム情報
                sys_info = (
                    f"**CPU使用率:** {cpu_percent}%\n"
                    f"**メモリ使用率:** {mem.percent}%\n"
                    f"**システム起動時間:** {self._format_timedelta(uptime)}"
                )
                embed.add_field(name="システム", value=sys_info, inline=True)
                
                # ハードウェア情報
                hw_info = (
                    f"**OS:** {platform.system()} {platform.release()}\n"
                    f"**Python:** {platform.python_version()}\n"
                    f"**Discord.py:** {discord.__version__}"
                )
                embed.add_field(name="環境", value=hw_info, inline=True)
                
                # フッター
                embed.set_footer(text="統計情報は1秒ごとに更新されます")
                
                # 結果を送信
                await interaction.followup.send(embed=embed, ephemeral=True)
                self.logger.info(f"システム統計を表示しました (ユーザー: {interaction.user.name})")
                
            except Exception as e:
                self.logger.error(f"統計情報取得エラー: {e}")
                await interaction.followup.send(f"統計情報の取得中にエラーが発生しました: {e}", ephemeral=True)
    
    def _format_bytes(self, num_bytes):
        """バイト数を読みやすい形式に変換"""
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024**2:
            return f"{num_bytes/1024:.1f} KB"
        elif num_bytes < 1024**3:
            return f"{num_bytes/(1024**2):.1f} MB"
        else:
            return f"{num_bytes/(1024**3):.2f} GB"
    
    def _format_timedelta(self, td):
        """時間差を読みやすい形式に変換"""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}日 {hours}時間 {minutes}分"
        elif hours > 0:
            return f"{hours}時間 {minutes}分 {seconds}秒"
        else:
            return f"{minutes}分 {seconds}秒"

def setup(bot):
    """コマンドの初期化"""
    bot.stats_command = StatsCommand(bot)
    return bot.stats_command
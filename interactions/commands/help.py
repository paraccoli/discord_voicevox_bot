import discord
from discord import app_commands
import logging

class HelpCommand:
    """ヘルプコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.help")
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="help",
            description="利用可能なコマンドと使い方を表示します"
        )
        async def help(interaction: discord.Interaction):
            try:
                # ヘルプ情報を表示
                embed = discord.Embed(
                    title="VOICEVOX読み上げBot - ヘルプ",
                    description="VOICEVOXを使用してテキストを音声に変換するBotです。",
                    color=discord.Color.blue()
                )
                
                # 基本コマンド
                embed.add_field(
                    name="基本コマンド",
                    value=(
                        "`/join` - ボイスチャンネルにBotを参加させます\n"
                        "`/leave` - ボイスチャンネルからBotを退出させます\n"
                        "`/setup <テキストチャンネル> [有効化/無効化]` - 自動読み上げするチャンネルを設定します\n"
                    ),
                    inline=False
                )
                
                # 音声制御コマンド
                embed.add_field(
                    name="音声制御",
                    value=(
                        "`/pause` - 読み上げを一時停止します\n"
                        "`/resume` - 一時停止中の読み上げを再開します\n"
                    ),
                    inline=False
                )
                
                # 設定コマンド
                embed.add_field(
                    name="設定",
                    value=(
                        "`/list_speakers` - 利用可能な話者のリストを表示します\n"
                        "`/set_speaker <話者ID> [個人用/サーバー全体]` - デフォルトの話者を設定します\n"
                    ),
                    inline=False
                )
                
                # 使用例
                embed.add_field(
                    name="使用例",
                    value=(
                        "1. `/join` でボイスチャンネルに参加\n"
                        "2. `/setup #一般` で #一般 チャンネルの自動読み上げを有効化\n"
                        "3. `/list_speakers` で利用可能な話者を確認\n"
                        "4. `/set_speaker 8 個人用` で自分のデフォルト話者をID 8に設定する\n"
                    ),
                    inline=False
                )
                
                # フッター
                embed.set_footer(text="ボイスチャンネルに参加して、/setup コマンドで読み上げチャンネルを設定してください")
                
                # ヘルプ情報を送信 (ephemeral=Trueで本人にのみ表示)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.logger.info(f"ヘルプを表示しました (ユーザー: {interaction.user.name})")
                
            except Exception as e:
                self.logger.error(f"ヘルプ表示エラー: {e}")
                await interaction.response.send_message(f"ヘルプ情報の表示中にエラーが発生しました: {e}", ephemeral=True)

def setup(bot):
    """コマンドの初期化"""
    HelpCommand(bot)
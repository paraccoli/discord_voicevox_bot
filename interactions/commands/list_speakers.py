#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord import app_commands, ui
import logging
import sys
import os
import json
import math
from typing import List

# utils/voicevox_apiをインポートするためのパス設定
sys.path.insert(0, os.getcwd())
from utils.voicevox_api import VoicevoxAPI

class SpeakerPaginationView(ui.View):
    """話者リストのページネーション用View"""
    
    def __init__(self, embeds: List[discord.Embed], author_id: int):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.embeds = embeds
        self.author_id = author_id  # ページネーションを操作できるユーザーのID
        self.current_page = 0
        self.total_pages = len(embeds)
        
        # 最初のページだけ前ボタンを無効化
        self.update_button_state()
    
    def update_button_state(self):
        """ページに応じてボタンの有効/無効を設定"""
        # 前ページボタン
        self.prev_button.disabled = (self.current_page == 0)
        # 次ページボタン
        self.next_button.disabled = (self.current_page == self.total_pages - 1)
        
        # 現在のページ/総ページ数を表示
        self.page_info.label = f"{self.current_page + 1}/{self.total_pages}"
    
    @ui.button(emoji="⬅️", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        """前ページボタン"""
        # 権限チェック（コマンド実行者のみ操作可能）
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("このページネーションはあなたが操作できません", ephemeral=True)
            return
        
        self.current_page -= 1
        self.update_button_state()
        
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: ui.Button):
        """ページ情報表示（クリックできないボタン）"""
        pass
    
    @ui.button(emoji="➡️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        """次ページボタン"""
        # 権限チェック（コマンド実行者のみ操作可能）
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("このページネーションはあなたが操作できません", ephemeral=True)
            return
        
        self.current_page += 1
        self.update_button_state()
        
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    async def on_timeout(self):
        """タイムアウト時にボタンを無効化"""
        for item in self.children:
            item.disabled = True
        
        # メッセージが存在すれば編集（viewだけ更新）
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except:
            pass


class ListSpeakersCommand:
    """話者リスト表示コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("commands.list_speakers")
        self.voicevox_api = VoicevoxAPI()
        
        # スラッシュコマンドを登録
        @bot.tree.command(
            name="list_speakers",
            description="VOICEVOXで利用可能な話者のリストを表示します"
        )
        async def list_speakers(interaction: discord.Interaction):
            # 権限チェック
            slash_commands = self.bot.get_cog('SlashCommands')
            if slash_commands and not slash_commands.check_permission(interaction, "list_speakers"):
                await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            try:
                # レスポンスをディファード
                await interaction.response.defer(ephemeral=True)
                
                # 話者リストを取得
                speakers = await self.voicevox_api.get_speakers()
                
                if not speakers:
                    await interaction.followup.send("VOICEVOXから話者情報を取得できませんでした。VOICEVOXエンジンが起動しているか確認してください。", ephemeral=True)
                    return
                
                # スピーカー情報を整理
                speaker_dict = {}
                
                for speaker in speakers:
                    speaker_name = speaker.get("name", "不明")
                    styles = speaker.get("styles", [])
                    
                    if speaker_name not in speaker_dict:
                        speaker_dict[speaker_name] = []
                        
                    for style in styles:
                        style_id = style.get("id", -1)
                        style_name = style.get("name", "不明")
                        speaker_dict[speaker_name].append((style_id, style_name))
                
                # 最大25フィールドずつに分割して複数のEmbedを作成
                embeds = []
                current_embed = discord.Embed(
                    title="VOICEVOX 話者一覧",
                    description="以下の話者IDを `/set_speaker` コマンドで使用できます。",
                    color=discord.Color.blue()
                )
                
                field_count = 0
                
                # 話者をEmbedに追加
                for speaker_name, styles in speaker_dict.items():
                    # 25フィールド制限に達したら、新しいEmbedを作成
                    if field_count >= 25:
                        embeds.append(current_embed)
                        current_embed = discord.Embed(
                            title="VOICEVOX 話者一覧",
                            description="以下の話者IDを `/set_speaker` コマンドで使用できます。",
                            color=discord.Color.blue()
                        )
                        field_count = 0
                    
                    # スタイル情報をテキスト形式で作成
                    value_text = "\n".join([f"ID: `{style_id}` - {style_name}" for style_id, style_name in styles])
                    
                    # フィールドを追加
                    current_embed.add_field(
                        name=speaker_name,
                        value=value_text,
                        inline=False
                    )
                    field_count += 1
                
                # 最後のEmbedを追加
                if field_count > 0:
                    embeds.append(current_embed)
                
                # フッターを全てのEmbedに追加
                for i, embed in enumerate(embeds):
                    embed.set_footer(text=f"話者IDを設定すると、自動読み上げ時にその声で読み上げられます")
                
                # ページネーションビューを作成
                if embeds:
                    pagination_view = SpeakerPaginationView(embeds, interaction.user.id)
                    # 初期ページを送信
                    message = await interaction.followup.send(embed=embeds[0], view=pagination_view)
                    pagination_view.message = message  # タイムアウト用に参照を保存
                    
                    self.logger.info(f"話者リストを表示しました (ユーザー: {interaction.user.name})")
                else:
                    await interaction.followup.send("話者情報が見つかりませんでした。", ephemeral=True)
                
            except Exception as e:
                self.logger.error(f"話者リスト取得エラー: {e}")
                await interaction.followup.send(f"話者情報の取得中にエラーが発生しました: {e}", ephemeral=True)


def setup(bot):
    """コマンドの初期化"""
    bot.list_speakers_command = ListSpeakersCommand(bot)
    return bot.list_speakers_command
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from discord.ext import commands
from discord import app_commands
import discord
import os
import importlib
import sys
import logging
import json

class SlashCommands(commands.Cog):
    """スラッシュコマンド機能を管理するCog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("slash_commands")
        self.permissions = self._load_permissions()
        
        # コマンドモジュールを動的にロード
        self._load_command_modules()
    
    def _load_permissions(self):
        """permissions.jsonから権限設定を読み込む"""
        try:
            with open('config/permissions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"権限ファイルの読み込みに失敗: {e}")
            return {"commands": {}}
    
    def _load_command_modules(self):
        """commands/ ディレクトリから全てのコマンドモジュールを読み込む"""
        commands_dir = "interactions/commands"
        sys.path.insert(0, os.getcwd())  # カレントディレクトリをPythonパスに追加
        
        if not os.path.exists(commands_dir):
            self.logger.error(f"コマンドディレクトリが見つかりません: {commands_dir}")
            return
        
        for file in os.listdir(commands_dir):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = f"interactions.commands.{file[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    setup_func = getattr(module, "setup", None)
                    
                    if setup_func and callable(setup_func):
                        setup_func(self.bot)
                        self.logger.info(f"コマンドモジュール '{module_name}' を読み込みました")
                    else:
                        self.logger.warning(f"コマンドモジュール '{module_name}' にsetup関数がありません")
                except Exception as e:
                    self.logger.error(f"コマンドモジュール '{module_name}' の読み込みに失敗: {e}")
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        """スラッシュコマンド実行完了時のロギング"""
        guild_name = interaction.guild.name if interaction.guild else "DM"
        self.logger.info(f"{interaction.user} が {guild_name} で {command.name} コマンドを実行")
    
    def check_permission(self, ctx_or_interaction, command_name):
        """コマンド実行権限をチェック"""
        user_id = ctx_or_interaction.user.id
        
        # 管理者リストチェック
        admin_users = self.permissions.get("admin_users", [])
        if user_id in admin_users:
            return True
        
        # コマンド権限チェック
        command_perms = self.permissions.get("commands", {}).get(command_name, {})
        default_allow = command_perms.get("default", True)
        
        # ロール制限がある場合
        if "roles" in command_perms and command_perms["roles"]:
            if not hasattr(ctx_or_interaction.user, "roles"):
                return default_allow
                
            user_roles = [role.id for role in ctx_or_interaction.user.roles]
            allowed_roles = command_perms["roles"]
            
            # 1つでも許可ロールを持っていれば許可
            for role_id in allowed_roles:
                if role_id in user_roles:
                    return True
                    
            # 特定のロール制限があるが、該当ロールがない場合は拒否
            return False
        
        # 特に制限がなければデフォルト値を返す
        return default_allow

async def setup(bot):
    """Cogのセットアップ"""
    await bot.add_cog(SlashCommands(bot))
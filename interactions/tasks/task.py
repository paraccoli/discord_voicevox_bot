#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import discord
import logging
from datetime import datetime, timedelta
import os
import psutil
import sys
import time

# 親ディレクトリをパスに追加
sys.path.insert(0, os.getcwd())
from utils.tasks import setup as setup_background_tasks

class TasksModule:
    """
    タスク管理モジュール
    定期実行タスク、バックグラウンドプロセス、スケジュール済みタスクを管理
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("tasks.module")
        
        # バックグラウンドタスク管理
        self.background_tasks = setup_background_tasks(bot)
        
        # 自動実行タスクリスト
        self.scheduled_tasks = {}
        
        # 自動タスク実行用ループ
        self.task_loop = None
    
    async def setup(self):
        """タスクモジュールの初期化と起動"""
        self.logger.info("タスクモジュールを初期化しています...")
        
        # バックグラウンドタスクの起動
        await self.background_tasks.start()
        
        # 自動タスクの登録
        self._register_scheduled_tasks()
        
        # タスクループの起動
        self.task_loop = asyncio.create_task(self._task_scheduler_loop())
        
        self.logger.info("タスクモジュールの初期化が完了しました")
    
    def _register_scheduled_tasks(self):
        """スケジュール済みタスクの登録"""
        # タスクの登録例（毎時実行、毎日実行など）
        self.scheduled_tasks["hourly_stats"] = {
            "func": self._collect_hourly_stats,
            "interval": 3600,  # 1時間ごと
            "last_run": 0,
            "description": "毎時の統計情報収集"
        }
        
        self.scheduled_tasks["daily_cleanup"] = {
            "func": self._daily_cleanup,
            "interval": 86400,  # 24時間ごと
            "last_run": 0,
            "description": "日次のクリーンアップ処理"
        }
    
    async def _task_scheduler_loop(self):
        """スケジュールされたタスクを実行するループ"""
        try:
            # Botの準備が完了するまで待機
            await self.bot.wait_until_ready()
            
            while True:
                current_time = time.time()
                
                # スケジュール済みの各タスクをチェック
                for task_name, task_info in self.scheduled_tasks.items():
                    try:
                        # 実行時間になったか確認
                        if current_time - task_info["last_run"] >= task_info["interval"]:
                            self.logger.debug(f"スケジュールされたタスクを実行: {task_name}")
                            
                            # タスク関数を実行
                            await task_info["func"]()
                            
                            # 最終実行時間を更新
                            self.scheduled_tasks[task_name]["last_run"] = current_time
                    except Exception as e:
                        self.logger.error(f"スケジュールされたタスク '{task_name}' の実行中にエラー: {e}")
                
                # 短い間隔で確認（10秒から30秒に変更）
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            self.logger.info("スケジュールタスクループが停止されました")
        except Exception as e:
            self.logger.error(f"スケジュールタスクループでエラー: {e}")
    
    async def shutdown(self):
        """タスクモジュールの終了処理"""
        self.logger.info("タスクモジュールを終了しています...")
        
        # タスクループをキャンセル
        if self.task_loop:
            self.task_loop.cancel()
            try:
                await self.task_loop
            except asyncio.CancelledError:
                pass
        
        # バックグラウンドタスクの停止
        await self.background_tasks.stop()
        
        self.logger.info("タスクモジュールを終了しました")
    
    # --- スケジュール済みタスクの実装 ---
    
    async def _collect_hourly_stats(self):
        """1時間ごとに統計情報を収集・記録"""
        try:
            if hasattr(self.bot, 'system_stats'):
                stats_dir = "stats/hourly"
                os.makedirs(stats_dir, exist_ok=True)
                
                # 現在時刻をファイル名に使用
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # システムリソース情報の取得
                cpu_percent = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # ボット固有の統計
                words_read = self.bot.system_stats.words_read
                messages = self.bot.system_stats.messages_processed
                
                # ファイルに記録
                with open(f"{stats_dir}/stats_{timestamp}.log", "w", encoding="utf-8") as f:
                    f.write(f"時刻: {datetime.now().isoformat()}\n")
                    f.write(f"CPU使用率: {cpu_percent}%\n")
                    f.write(f"メモリ使用率: {mem.percent}%\n")
                    f.write(f"ディスク使用率: {disk.percent}%\n")
                    f.write(f"総読み上げ単語数: {words_read}\n")
                    f.write(f"総処理メッセージ数: {messages}\n")
                
                self.logger.info("時間ごとの統計情報を記録しました")
        except Exception as e:
            self.logger.error(f"時間ごとの統計収集中にエラー: {e}")
    
    async def _daily_cleanup(self):
        """日次のクリーンアップ処理"""
        try:
            # 古いログファイルのクリーンアップ
            logs_dir = "logs"
            if os.path.exists(logs_dir):
                current_time = time.time()
                # 7日以上前のログファイルを削除
                max_age = 7 * 86400
                deleted_count = 0
                
                for filename in os.listdir(logs_dir):
                    file_path = os.path.join(logs_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age:
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except OSError:
                                continue
                
                if deleted_count > 0:
                    self.logger.info(f"古いログファイル {deleted_count} 件を削除しました")
            
            # 古い統計ファイルのクリーンアップ
            stats_dir = "stats/hourly"
            if os.path.exists(stats_dir):
                current_time = time.time()
                # 30日以上前の統計ファイルを削除
                max_age = 30 * 86400
                deleted_count = 0
                
                for filename in os.listdir(stats_dir):
                    file_path = os.path.join(stats_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age:
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except OSError:
                                continue
                
                if deleted_count > 0:
                    self.logger.info(f"古い統計ファイル {deleted_count} 件を削除しました")
                    
        except Exception as e:
            self.logger.error(f"日次クリーンアップ処理中にエラー: {e}")

# Botにタスクモジュールを設定する関数
def setup(bot):
    """タスクモジュールを初期化してBotにアタッチ"""
    tasks_module = TasksModule(bot)
    bot.tasks_module = tasks_module
    
    return tasks_module
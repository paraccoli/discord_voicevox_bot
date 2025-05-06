#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import time
import psutil
import discord
from datetime import datetime, timedelta
import json

class BackgroundTasks:
    """
    バックグラウンドタスクを管理するクラス
    ステータス更新、キャッシュ管理、システム監視など
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("tasks")
        self.cache_cleanup_interval = 24 * 3600  # キャッシュ掃除間隔（秒）
        self.status_update_interval = 120  # ステータス更新間隔（秒）
        self.system_check_interval = 300  # システム監視間隔（秒）
        self.tasks = []
        self.running = False
    
    async def start(self):
        """すべてのバックグラウンドタスクを開始"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("バックグラウンドタスクを開始します")
        
        # タスクを作成して管理リストに追加
        self.tasks = [
            asyncio.create_task(self._update_status_loop()),
            asyncio.create_task(self._clean_cache_loop()),
            asyncio.create_task(self._system_monitor_loop())
        ]
    
    async def stop(self):
        """すべてのバックグラウンドタスクを停止"""
        if not self.running:
            return
        
        self.running = False
        
        # すべてのタスクをキャンセル
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # キャンセルが完了するのを待つ
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        self.tasks = []
        self.logger.info("バックグラウンドタスクを停止しました")
    
    async def _update_status_loop(self):
        """ボットのステータスを定期的に更新するループ"""
        try:
            # Botが準備完了するまで待機
            await self.bot.wait_until_ready()
            
            while self.running:
                try:
                    if hasattr(self.bot, 'system_stats'):
                        # システム統計がある場合
                        words_count = self.bot.system_stats.words_read
                        net_speed = self.bot.system_stats.get_network_speed()
                        net_speed_str = f"{net_speed/1024:.1f} KB/s" if net_speed < 1024*1024 else f"{net_speed/(1024*1024):.1f} MB/s"
                        
                        await self.bot.change_presence(
                            activity=discord.Activity(
                                type=discord.ActivityType.listening, 
                                name=f"{words_count}単語読み上げ | {net_speed_str}"
                            )
                        )
                        self.logger.debug(f"ステータス更新: {words_count}単語, {net_speed_str}")
                        
                        # 統計情報をファイルに保存
                        await self._save_stats()
                except Exception as e:
                    self.logger.error(f"ステータス更新エラー: {e}")
                
                # 次の更新まで待機
                await asyncio.sleep(self.status_update_interval)
                
        except asyncio.CancelledError:
            self.logger.debug("ステータス更新タスクが停止されました")
        except Exception as e:
            self.logger.error(f"ステータス更新ループで予期しないエラー: {e}")
    
    async def _clean_cache_loop(self):
        """キャッシュを定期的にクリーンアップするループ"""
        try:
            # Botが準備完了するまで待機
            await self.bot.wait_until_ready()
            
            while self.running:
                try:
                    # キャッシュディレクトリをチェック
                    cache_dir = "temp/cache"
                    if os.path.exists(cache_dir):
                        # アクセスされていない古いキャッシュファイルを削除
                        files = os.listdir(cache_dir)
                        current_time = time.time()
                        deleted_count = 0
                        
                        # 最大キャッシュサイズ（デフォルト500MB）
                        max_cache_size = 500 * 1024 * 1024
                        
                        # 現在のキャッシュサイズを計算
                        total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in files if os.path.isfile(os.path.join(cache_dir, f)))
                        
                        # サイズが大きすぎる場合、一部のキャッシュを削除
                        if total_size > max_cache_size:
                            # ファイルを最終アクセス時間でソート
                            file_stats = [(f, os.path.getatime(os.path.join(cache_dir, f))) for f in files if os.path.isfile(os.path.join(cache_dir, f))]
                            file_stats.sort(key=lambda x: x[1])  # 古い順にソート
                            
                            # キャッシュサイズが上限以下になるまで古いファイルを削除
                            for filename, _ in file_stats:
                                file_path = os.path.join(cache_dir, filename)
                                file_size = os.path.getsize(file_path)
                                try:
                                    os.remove(file_path)
                                    deleted_count += 1
                                    total_size -= file_size
                                    if total_size <= max_cache_size * 0.8:  # 20%のマージンを残す
                                        break
                                except OSError:
                                    continue
                        
                        if deleted_count > 0:
                            self.logger.info(f"キャッシュクリーンアップ: {deleted_count}ファイルを削除しました")
                except Exception as e:
                    self.logger.error(f"キャッシュクリーンアップエラー: {e}")
                
                # 次のクリーンアップまで待機
                await asyncio.sleep(self.cache_cleanup_interval)
                
        except asyncio.CancelledError:
            self.logger.debug("キャッシュクリーンアップタスクが停止されました")
        except Exception as e:
            self.logger.error(f"キャッシュクリーンアップループで予期しないエラー: {e}")
    
    async def _system_monitor_loop(self):
        """システムリソースを定期的に監視するループ"""
        try:
            # Botが準備完了するまで待機
            await self.bot.wait_until_ready()
            
            # カウンターの初期化（15分ごとにGC実行用）
            gc_counter = 0
            
            while self.running:
                try:
                    # CPU・メモリ使用率を取得
                    cpu_percent = psutil.cpu_percent(interval=1)
                    mem = psutil.virtual_memory()
                    
                    # 高負荷の場合は警告ログを出力
                    if cpu_percent > 90:
                        self.logger.warning(f"CPU使用率が高負荷です: {cpu_percent}%")
                    if mem.percent > 90:
                        self.logger.warning(f"メモリ使用率が高負荷です: {mem.percent}%")
                    
                    # 15分ごとに明示的にガベージコレクションを実行
                    gc_counter += 1
                    if gc_counter >= 3:  # 5分間隔 × 3 = 15分
                        import gc
                        collected = gc.collect()
                        self.logger.debug(f"ガベージコレクション実行: {collected} オブジェクトを回収")
                        gc_counter = 0
                    
                    # 詳細なシステム情報をデバッグログに出力
                    self.logger.debug(f"システムステータス - CPU: {cpu_percent}%, メモリ: {mem.percent}%")
                except Exception as e:
                    self.logger.error(f"システム監視エラー: {e}")
                
                # 次の監視まで待機
                await asyncio.sleep(self.system_check_interval)
                
        except asyncio.CancelledError:
            self.logger.debug("システム監視タスクが停止されました")
        except Exception as e:
            self.logger.error(f"システム監視ループで予期しないエラー: {e}")
    
    async def _save_stats(self):
        """統計情報を定期的にファイルに保存"""
        if not hasattr(self.bot, 'system_stats'):
            return
        
        try:
            stats_dir = "stats"
            os.makedirs(stats_dir, exist_ok=True)
            
            stats_data = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.bot.system_stats.start_time).total_seconds(),
                "words_read": self.bot.system_stats.words_read,
                "messages_processed": self.bot.system_stats.messages_processed,
                "cache_hits": self.bot.system_stats.cache_hits,
                "cache_misses": self.bot.system_stats.cache_misses,
                "network_speed_bytes": self.bot.system_stats.get_network_speed(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent
            }
            
            stats_file = f"{stats_dir}/stats.json"
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"統計情報の保存エラー: {e}")

def setup(bot):
    """Botに機能を設定"""
    background_tasks = BackgroundTasks(bot)
    bot.background_tasks = background_tasks
    
    # bot.pyのon_ready内からstart()を呼び出す用にメソッドを追加
    bot.start_background_tasks = background_tasks.start
    bot.stop_background_tasks = background_tasks.stop
    
    return background_tasks
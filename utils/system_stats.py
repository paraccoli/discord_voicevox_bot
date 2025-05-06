#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import datetime
import psutil
import re
import threading

class SystemStats:
    """システム統計情報を管理するクラス"""
    
    def __init__(self):
        # 基本統計
        self.start_time = datetime.datetime.now()
        self.messages_processed = 0
        self.words_read = 0
        self.audio_files_generated = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # ネットワーク統計
        self.last_net_io = psutil.net_io_counters()
        self.last_check_time = time.time()
        self.current_net_speed = 0
        
        # 定期的な統計更新用スレッド
        self._start_update_thread()
    
    def _start_update_thread(self):
        """定期的にネットワーク速度などの統計を更新するスレッドを開始"""
        def update_stats():
            while True:
                try:
                    # ネットワーク速度を計算
                    self._update_network_speed()
                    time.sleep(3)  # 1秒から3秒に変更してCPU負荷を軽減
                except Exception:
                    # スレッド内でのエラーを抑止
                    pass
        
        # デーモンスレッドとして実行（メインプログラム終了時に自動終了）
        thread = threading.Thread(target=update_stats, daemon=True)
        thread.start()
    
    def _update_network_speed(self):
        """現在のネットワーク速度を計算"""
        current_time = time.time()
        current_net_io = psutil.net_io_counters()
        
        # 前回の測定からの差分を計算
        time_diff = current_time - self.last_check_time
        bytes_sent_diff = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv_diff = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        
        # 現在の速度を更新（送信と受信の合計）
        if time_diff > 0:
            self.current_net_speed = (bytes_sent_diff + bytes_recv_diff) / time_diff
        
        # 現在の値を保存
        self.last_net_io = current_net_io
        self.last_check_time = current_time
    
    def get_network_speed(self):
        """現在のネットワーク速度を取得（バイト/秒）"""
        return self.current_net_speed
    
    def increment_messages(self):
        """処理したメッセージ数をカウント"""
        self.messages_processed += 1
    
    def add_words(self, text):
        """読み上げた単語数をカウント"""
        # 簡易的な単語カウント（日本語の場合は文字数の1/2程度に設定）
        # 英数字のみの場合は空白で区切って単語としてカウント
        if re.search(r'[a-zA-Z0-9]', text):
            words = len(re.findall(r'\S+', text))
        else:
            # 日本語など - 文字数÷2を近似的に単語数とする
            words = len(text) // 2
            if words == 0 and len(text) > 0:
                words = 1
        
        self.words_read += words
        return words
    
    def record_cache_hit(self):
        """キャッシュヒットを記録"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """キャッシュミスを記録"""
        self.cache_misses += 1
    
    def get_cache_hit_ratio(self):
        """キャッシュヒット率を計算"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0
        return (self.cache_hits / total) * 100
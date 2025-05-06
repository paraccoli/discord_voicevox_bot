#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import hashlib
import logging
import shutil
from datetime import datetime
import configparser
import aiofiles


MAX_CACHE_SIZE = 1024 * 1024 * 1024  # 1GB

class AudioCache:
    """音声ファイルのキャッシュを管理するクラス"""
    
    def __init__(self):
        """初期化"""
        # 設定を読み込み
        config = configparser.ConfigParser()
        config.read('config/settings.ini')
        
        # キャッシュ設定
        self.cache_enabled = config.getboolean('DEFAULT', 'cache_enabled', fallback=True)
        self.cache_dir = config.get('PATHS', 'cache_directory', fallback='temp/cache')
        
        # キャッシュ情報を保存するJSONファイルのパス
        self.cache_info_path = os.path.join(self.cache_dir, 'cache_info.json')
        
        # ディレクトリの存在確認
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # キャッシュ情報の読み込み
        self.cache_info = self._load_cache_info()
        
        # ロガー設定
        self.logger = logging.getLogger("audio_cache")
        
    def _load_cache_info(self):
        """キャッシュ情報をJSONから読み込む"""
        if os.path.exists(self.cache_info_path):
            try:
                with open(self.cache_info_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # 読み込みに失敗した場合は新規作成
                return {"files": {}}
        else:
            return {"files": {}}
    
    async def _save_cache_info(self):
        """キャッシュ情報をJSONに保存する"""
        try:
            async with aiofiles.open(self.cache_info_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.cache_info, ensure_ascii=False, indent=2))
        except IOError as e:
            self.logger.error(f"キャッシュ情報の保存に失敗: {e}")
    
    def generate_cache_key(self, text, speaker_id):
        """テキストと話者IDからキャッシュキーを生成"""
        return hashlib.sha256(f"{text}_{speaker_id}".encode()).hexdigest()
    
    def get_cache_path(self, cache_key):
        """キャッシュキーからファイルパスを取得"""
        if not self.cache_enabled:
            return None
            
        if cache_key in self.cache_info["files"]:
            file_path = self.cache_info["files"][cache_key]["path"]
            if os.path.exists(file_path):
                # 最終アクセス日時を更新
                self.cache_info["files"][cache_key]["last_accessed"] = datetime.now().isoformat()
                return file_path
            else:
                # ファイルが存在しない場合はキャッシュ情報から削除
                del self.cache_info["files"][cache_key]
        
        return None
    
    async def add_to_cache(self, cache_key, file_path, text, speaker_id):
        """ファイルをキャッシュに追加"""
        if not self.cache_enabled:
            return
        
        # キャッシュディレクトリ内のファイルパス
        cache_filename = f"{cache_key}.wav"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        try:
            # ファイルをキャッシュディレクトリにコピー
            if file_path != cache_path and os.path.exists(file_path):
                shutil.copy2(file_path, cache_path)
                
            # キャッシュ情報を更新
            self.cache_info["files"][cache_key] = {
                "text": text,
                "speaker_id": speaker_id,
                "path": cache_path,
                "created": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            }
            
            # キャッシュ情報を保存
            await self._save_cache_info()
            self.logger.info(f"ファイルをキャッシュに追加: {cache_path}")
            
        except (IOError, shutil.Error) as e:
            self.logger.error(f"キャッシュへの追加に失敗: {e}")
    
    async def cleanup_old_cache(self, max_age_days=30):
        """古いキャッシュファイルを削除"""
        if not self.cache_enabled:
            return
            
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, info in self.cache_info["files"].items():
            try:
                last_accessed = datetime.fromisoformat(info["last_accessed"])
                age_days = (current_time - last_accessed).days
                
                if age_days > max_age_days:
                    # 古いファイルを削除
                    if os.path.exists(info["path"]):
                        os.remove(info["path"])
                    keys_to_remove.append(key)
                    self.logger.info(f"古いキャッシュファイルを削除: {info['path']}")
            except (ValueError, KeyError) as e:
                self.logger.error(f"キャッシュ情報の解析エラー: {e}")
                keys_to_remove.append(key)
        
        # キャッシュ情報から削除したキーを削除
        for key in keys_to_remove:
            del self.cache_info["files"][key]
        
        # キャッシュ情報を保存
        if keys_to_remove:
            await self._save_cache_info()
            self.logger.info(f"{len(keys_to_remove)}個の古いキャッシュエントリを削除")

# シングルトンインスタンス
cache_manager = AudioCache()
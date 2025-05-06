#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import aiohttp
import json
import logging
import hashlib
import configparser
from dotenv import load_dotenv
import re

# 環境変数の読み込み
load_dotenv()

class VoicevoxAPI:
    """VOICEVOX APIとの連携を行うクラス"""
    
    def __init__(self):
        """初期化"""
        # 設定を読み込み
        config = configparser.ConfigParser()
        config.read('config/settings.ini')
        
        # APIのURL設定
        self.api_url = os.getenv("VOICEVOX_API_URL", "http://localhost:50021")
        
        # キャッシュ設定
        self.cache_enabled = config.getboolean('DEFAULT', 'cache_enabled', fallback=True)
        self.temp_dir = config.get('PATHS', 'temp_directory', fallback='temp')
        self.cache_dir = config.get('PATHS', 'cache_directory', fallback='temp/cache')
        
        # 音声設定
        self.audio_format = config.get('AUDIO', 'audio_format', fallback='wav')
        
        # ロガー設定
        self.logger = logging.getLogger("voicevox_api")
    
    async def get_speakers(self):
        """使用可能な話者一覧を取得する"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.api_url}/speakers") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"話者一覧の取得に失敗: HTTP {response.status}")
                        return []
            except aiohttp.ClientError as e:
                self.logger.error(f"VOICEVOX API接続エラー: {e}")
                return []
    
    def _generate_cache_filename(self, text, speaker_id):
        """キャッシュ用のファイル名を生成"""
        # テキストとspeaker_idからハッシュを生成
        text_hash = hashlib.sha256(f"{text}_{speaker_id}".encode()).hexdigest()[:16]
        return f"{self.cache_dir}/{text_hash}.{self.audio_format}"
    
    async def create_audio(self, text, speaker_id=1, output_path=None):
        """
        テキストから音声を生成する
        
        Args:
            text (str): 合成するテキスト
            speaker_id (int): 話者ID
            output_path (str, optional): 保存先ファイルパス
            
        Returns:
            str: 生成された音声ファイルのパス、失敗時はNone
        """
        # 出力パスが指定されていなければキャッシュパスを使用
        if not output_path:
            output_path = self._generate_cache_filename(text, speaker_id)
        
        # キャッシュが有効で、既にファイルが存在する場合は再利用
        if self.cache_enabled and os.path.exists(output_path):
            self.logger.info(f"キャッシュされた音声ファイルを使用: {output_path}")
            return output_path
        
        # ディレクトリの存在確認
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        # 音声合成リクエスト
        async with aiohttp.ClientSession() as session:
            try:
                # 1. オーディオクエリの作成
                params = {"text": text, "speaker": speaker_id}
                async with session.post(f"{self.api_url}/audio_query", params=params) as response:
                    if response.status != 200:
                        self.logger.error(f"オーディオクエリ作成失敗: HTTP {response.status}")
                        return None
                    query_data = await response.json()
                
                # 2. 音声合成
                params = {"speaker": speaker_id}
                async with session.post(
                    f"{self.api_url}/synthesis", 
                    params=params,
                    json=query_data,
                    headers={"Accept": f"audio/{self.audio_format}"}
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"音声合成失敗: HTTP {response.status}")
                        return None
                    
                    # 音声ファイルの保存
                    with open(output_path, "wb") as f:
                        f.write(await response.read())
                    
                    self.logger.info(f"音声ファイル生成: {output_path}")
                    return output_path
                    
            except aiohttp.ClientError as e:
                self.logger.error(f"VOICEVOXリクエストエラー: {e}")
                return None
    
    async def get_speaker_info(self, speaker_id):
        """
        特定の話者の情報を取得する
        
        Args:
            speaker_id (int): 話者ID
            
        Returns:
            dict: 話者情報、取得失敗時はNone
        """
        speakers = await self.get_speakers()
        for speaker in speakers:
            if speaker.get("speaker_id") == speaker_id:
                return speaker
        return None
    
    async def create_audio(self, text, speaker_id=1):
        """テキストから音声を生成（非同期版）"""
        try:
            # テキストの長さが長い場合は分割して処理
            if len(text) > 100:
                # 句読点で分割
                segments = re.split('([。、．，!！?？])', text)
                combined_segments = []
                
                # 句読点を保持しながら結合
                for i in range(0, len(segments) - 1, 2):
                    if i + 1 < len(segments):
                        combined_segments.append(segments[i] + segments[i + 1])
                    else:
                        combined_segments.append(segments[i])
                
                # 最後のセグメントが漏れている場合は追加
                if len(segments) % 2 == 1:
                    combined_segments.append(segments[-1])
                
                # 各セグメントを個別に音声化して結合
                audio_paths = []
                for segment in combined_segments:
                    if not segment.strip():
                        continue
                    path = await self._generate_audio_segment(segment, speaker_id)
                    if path:
                        audio_paths.append(path)
                
                if not audio_paths:
                    return None
                
                # 複数の音声ファイルを結合
                return await self._combine_audio_files(audio_paths)
            else:
                # 短いテキストはそのまま処理
                return await self._generate_audio_segment(text, speaker_id)
                
        except Exception as e:
            self.logger.error(f"音声合成エラー: {e}")
            return None
    
    async def _generate_audio_segment(self, text, speaker_id):
        """テキストセグメントから音声を生成する"""
        # 一時ファイルパスを生成
        temp_file = f"temp/{hashlib.sha256(text.encode()).hexdigest()[:8]}_{speaker_id}.{self.audio_format}"
        
        # ディレクトリの存在確認
        os.makedirs(os.path.dirname(temp_file), exist_ok=True)
        
        # 音声合成リクエスト
        async with aiohttp.ClientSession() as session:
            try:
                # 1. オーディオクエリの作成
                params = {"text": text, "speaker": speaker_id}
                async with session.post(f"{self.api_url}/audio_query", params=params) as response:
                    if response.status != 200:
                        self.logger.error(f"オーディオクエリ作成失敗: HTTP {response.status}")
                        return None
                    query_data = await response.json()
                
                # 2. 音声合成
                params = {"speaker": speaker_id}
                async with session.post(
                    f"{self.api_url}/synthesis", 
                    params=params,
                    json=query_data,
                    headers={"Accept": f"audio/{self.audio_format}"}
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"音声合成失敗: HTTP {response.status}")
                        return None
                    
                    # 音声ファイルの保存
                    with open(temp_file, "wb") as f:
                        f.write(await response.read())
                    
                    return temp_file
                    
            except aiohttp.ClientError as e:
                self.logger.error(f"VOICEVOXリクエストエラー: {e}")
                return None

    async def _combine_audio_files(self, audio_paths):
        """複数の音声ファイルを結合する"""
        if not audio_paths:
            return None
        
        # 1つしかない場合はそのまま返す
        if len(audio_paths) == 1:
            return audio_paths[0]
        
        # 複数ファイルの場合は結合
        import subprocess
        import uuid
        
        output_file = f"temp/combined_{uuid.uuid4().hex[:8]}.{self.audio_format}"
        
        # FFMPEGを使って結合
        try:
            # 入力ファイルリストを作成
            list_file = f"temp/filelist_{uuid.uuid4().hex[:8]}.txt"
            with open(list_file, "w") as f:
                for path in audio_paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            
            # FFMPEGで結合
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", 
                "-i", list_file, "-c", "copy", output_file
            ], check=True, stderr=subprocess.PIPE)
            
            # 一時リストファイルを削除
            os.remove(list_file)
            
            return output_file
            
        except (subprocess.SubprocessError, OSError) as e:
            self.logger.error(f"音声ファイル結合エラー: {e}")
            return audio_paths[0]  # エラーの場合は最初のファイルを返す
"""
Second version of the scrips for TTS transcriptions.
I've decided to use faster-whisper instead ow whisper large v3 due to faster-whisper being... well, faster while preserving the same quality.

faster-whisper also better handles background noise and silence
"""

import os
import json
import logging
from pathlib import Path
from datetime import timedelta
from typing import List, Dict, Any
from faster_whisper import WhisperModel

# --- CONFIGURATION ---
MODEL_SIZE = "large-v3"       # Best accuracy for Polish/English mix
DEVICE = "cuda"               # Uses RTX 3090
COMPUTE_TYPE = "float16"      # Optimal for RTX 3000 series (no precision loss vs float32)
LANGUAGE = "pl"               # Primary language (handles English code-switching naturally)
BEAM_SIZE = 5                 # Standard beam size for accuracy
VAD_FILTER = True             # Skips silence efficiently
MIN_SILENCE_DURATION_MS = 500 # Minimum silence to be considered a gap

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodcastTranscriber:
    def __init__(self):
        logger.info(f"Loading Whisper Model: {MODEL_SIZE} on {DEVICE}...")
        self.model = WhisperModel(
            MODEL_SIZE, 
            device=DEVICE, 
            compute_type=COMPUTE_TYPE
        )

    def format_timestamp(self, seconds: float) -> str:
        """Converts seconds to HH:MM:SS.mmm format."""
        td = timedelta(seconds=seconds)
        # Round to milliseconds
        total_seconds = int(td.total_seconds())
        milliseconds = int(td.microseconds / 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    def get_speaker_from_filename(self, filename: str) -> str:
        """Extracts speaker name from 'Episode_Speaker.wav'."""
        # Assumption: Filename is Episode_Speaker.wav
        base = Path(filename).stem
        parts = base.split('_')
        if len(parts) >= 2:
            return parts[-1] # Returns "John" from "S0E01_John"
        return "Unknown"

    def transcribe_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Transcribes a single audio file and returns segments with word timestamps."""
        logger.info(f"Processing: {file_path.name}")
        
        segments, info = self.model.transcribe(
            str(file_path),
            language=LANGUAGE,
            beam_size=BEAM_SIZE,
            vad_filter=VAD_FILTER,
            vad_parameters=dict(min_silence_duration_ms=MIN_SILENCE_DURATION_MS),
            word_timestamps=True # Critical for your requirement
        )

        results = []
        for segment in segments:
            words = []
            if segment.words:
                for w in segment.words:
                    words.append({
                        "start": w.start,
                        "end": w.end,
                        "word": w.word.strip(),
                        "probability": w.probability
                    })

            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": words
            })
        
        return results

    def save_detailed_json(self, data: List[Dict], output_path: Path):
        """Saves detailed per-word and per-sentence data to JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def process_directory(self, root_dir: str):
        """Scans directories recursively for episodes."""
        
        # 1. Map files to episodes based on directory structure or naming
        # We assume one directory = one episode, or strict naming S0E01_Speaker.wav
        
        for dirpath, _, filenames in os.walk(root_dir):
            wav_files = [f for f in filenames if f.lower().endswith('.wav')]
            if not wav_files:
                continue

            current_dir = Path(dirpath)
            episode_name = current_dir.name # e.g., "S0E01" or "Episode_5"
            
            combined_txt_path = current_dir / f"{episode_name}_TRANSCRIPT.txt"
            
            # Check if already processed
            if combined_txt_path.exists():
                logger.info(f"Skipping {episode_name} - Transcript already exists.")
                continue

            logger.info(f"--- Starting Episode: {episode_name} ---")
            
            all_segments = []
            
            # 2. Process each speaker file
            for wav in wav_files:
                wav_path = current_dir / wav
                speaker_name = self.get_speaker_from_filename(wav)
                
                # Check for individual JSON to avoid re-transcribing just one track
                json_path = wav_path.with_suffix('.json')
                
                speaker_data = []
                if json_path.exists():
                    logger.info(f"Loading existing data for {speaker_name}")
                    with open(json_path, 'r', encoding='utf-8') as f:
                        speaker_data = json.load(f)
                else:
                    speaker_data = self.transcribe_file(wav_path)
                    self.save_detailed_json(speaker_data, json_path)
                
                # Add speaker label to segments for the merger
                for seg in speaker_data:
                    seg['speaker'] = speaker_name
                    all_segments.append(seg)

            # 3. Merge and Sort
            # Sort by start time. Since digital silence is absolute, this works perfectly.
            all_segments.sort(key=lambda x: x['start'])

            # 4. Generate Combined Transcript
            logger.info(f"Generating merged transcript for {episode_name}...")
            with open(combined_txt_path, 'w', encoding='utf-8') as f:
                for seg in all_segments:
                    timestamp = self.format_timestamp(seg['start'])
                    # Format: [HH:MM:SS] Name: Text
                    line = f"[{timestamp}] {seg['speaker']}: {seg['text']}\n"
                    f.write(line)

            logger.info(f"Completed {episode_name}")

if __name__ == "__main__":
    # Define root directory to scan (current directory by default)
    ROOT_DIR = "." 
    
    app = PodcastTranscriber()
    app.process_directory(ROOT_DIR)
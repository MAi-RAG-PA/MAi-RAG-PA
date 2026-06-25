#!/usr/bin/env python3
"""
Speech Recognition using faster-whisper (primary) or Vosk (fallback)
"""
import os
import logging
from pathlib import Path
import wave
import json

logger = logging.getLogger(__name__)

# Try faster-whisper first
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    logger.info("✅ faster-whisper is available")
except ImportError as e:
    logger.warning(f"⚠️ faster-whisper not installed: {e}")

# Try Vosk as fallback
VOSK_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
    logger.info("✅ Vosk is available")
except ImportError as e:
    logger.warning(f"⚠️ Vosk not installed: {e}")

# Model paths
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")  # tiny, base, small, medium
VOSK_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "vosk-model-small-en-us-0.15"

class VoiceRecognizer:
    def __init__(self):
        self.whisper_model = None
        self.vosk_model = None
        self.preferred_engine = os.getenv("VOICE_ENGINE", "auto").lower()  # auto, whisper, vosk
        self._load_model()
    
    def _load_model(self):
        """Load the preferred speech recognition model."""
        
        # Try to load faster-whisper if preferred or auto
        if self.preferred_engine in ["auto", "whisper"] and WHISPER_AVAILABLE:
            try:
                logger.info(f"📥 Loading faster-whisper model: {WHISPER_MODEL_SIZE} (this may download ~500MB on first run)")
                self.whisper_model = WhisperModel(
                    WHISPER_MODEL_SIZE, 
                    device="cpu", 
                    compute_type="int8",
                    download_root=str(Path.home() / ".cache" / "huggingface" / "hub")
                )
                logger.info("✅ faster-whisper model loaded successfully")
                return
            except Exception as e:
                logger.error(f"❌ Failed to load faster-whisper: {e}")
                logger.info("🔄 Falling back to Vosk...")
        
        # Fall back to Vosk
        if VOSK_AVAILABLE and VOSK_MODEL_PATH.exists():
            try:
                logger.info(f"📥 Loading Vosk model from {VOSK_MODEL_PATH}")
                self.vosk_model = Model(str(VOSK_MODEL_PATH))
                logger.info("✅ Vosk model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load Vosk: {e}")
        else:
            if not VOSK_AVAILABLE:
                logger.error("❌ Vosk is not installed")
            if not VOSK_MODEL_PATH.exists():
                logger.error(f"❌ Vosk model not found at {VOSK_MODEL_PATH}")
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file to text."""
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return ""
        
        # Use whisper if available
        if self.whisper_model:
            result = self._transcribe_whisper(audio_file_path)
            if result:
                return result
            logger.warning("⚠️ Whisper transcription failed, trying Vosk...")
        
        # Fall back to Vosk
        if self.vosk_model:
            return self._transcribe_vosk(audio_file_path)
        
        logger.error("❌ No speech recognition engine available")
        return ""
    
    def _transcribe_whisper(self, audio_file_path: str) -> str:
        """Transcribe using faster-whisper."""
        try:
            logger.info(f"🎤 Transcribing with faster-whisper: {audio_file_path}")
            
            segments, info = self.whisper_model.transcribe(
                audio_file_path,
                beam_size=5,
                language="en",
                vad_filter=True,  # Filter out silence
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            result = " ".join(text_parts)
            logger.info(f"✅ Whisper transcription: '{result[:100]}...' " if len(result) > 100 else f"✅ Whisper transcription: '{result}'")
            return result
        except Exception as e:
            logger.error(f"❌ Whisper transcription failed: {e}", exc_info=True)
            return ""
    
    def _transcribe_vosk(self, audio_file_path: str) -> str:
        """Transcribe using Vosk."""
        try:
            logger.info(f"🎤 Transcribing with Vosk: {audio_file_path}")
            
            wf = wave.open(audio_file_path, "rb")
            
            # Check audio format
            if wf.getnchannels() != 1:
                logger.warning(f"⚠️ Audio has {wf.getnchannels()} channels, expected 1")
            if wf.getsampwidth() != 2:
                logger.warning(f"⚠️ Audio sample width is {wf.getsampwidth()}, expected 2")
            
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
            rec.SetWords(True)
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        results.append(result["text"])
            
            final_result = json.loads(rec.FinalResult())
            if final_result.get("text"):
                results.append(final_result["text"])
            
            wf.close()
            result = " ".join(results).strip()
            logger.info(f"✅ Vosk transcription: '{result[:100]}...' " if len(result) > 100 else f"✅ Vosk transcription: '{result}'")
            return result
        except Exception as e:
            logger.error(f"❌ Vosk transcription failed: {e}", exc_info=True)
            return ""

# Singleton instance
_recognizer = None

def get_recognizer() -> VoiceRecognizer:
    """Get or create the voice recognizer singleton."""
    global _recognizer
    if _recognizer is None:
        logger.info("🔧 Initializing VoiceRecognizer...")
        _recognizer = VoiceRecognizer()
    return _recognizer

def transcribe_audio_file(audio_file_path: str) -> str:
    """Transcribe an audio file to text."""
    recognizer = get_recognizer()
    return recognizer.transcribe_audio(audio_file_path)

#!/usr/bin/env python3
"""
Speech Recognition using faster-whisper (primary) or Vosk (fallback)
"""
import json
import logging
import os
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
    logger.info("faster-whisper is available")
except ImportError as e:
    logger.warning("faster-whisper not installed: %s", e)

VOSK_AVAILABLE = False
try:
    from vosk import KaldiRecognizer, Model

    VOSK_AVAILABLE = True
    logger.info("Vosk is available")
except ImportError as e:
    logger.warning("Vosk not installed: %s", e)

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
VOSK_MODEL_PATH = (
    Path(__file__).parent.parent.parent / "models" / "vosk-model-small-en-us-0.15"
)


class VoiceRecognizer:
    def __init__(self):
        self.whisper_model = None
        self.vosk_model = None
        self.preferred_engine = os.getenv("VOICE_ENGINE", "auto").lower()
        self._load_model()

    def _load_model(self):
        """Load the preferred speech recognition model."""
        if self.preferred_engine in ["auto", "whisper"] and WHISPER_AVAILABLE:
            try:
                logger.info(
                    "Loading faster-whisper model: %s (this may download model files on first run)",
                    WHISPER_MODEL_SIZE,
                )
                self.whisper_model = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(Path.home() / ".cache" / "huggingface" / "hub"),
                )
                logger.info("faster-whisper model loaded successfully")
                return
            except Exception as e:
                logger.error("Failed to load faster-whisper: %s", e, exc_info=True)
                logger.info("Falling back to Vosk...")

        if self.preferred_engine in ["auto", "vosk", "whisper"]:
            if VOSK_AVAILABLE and VOSK_MODEL_PATH.exists():
                try:
                    logger.info("Loading Vosk model from %s", VOSK_MODEL_PATH)
                    self.vosk_model = Model(str(VOSK_MODEL_PATH))
                    logger.info("Vosk model loaded successfully")
                except Exception as e:
                    logger.error("Failed to load Vosk: %s", e, exc_info=True)
            else:
                if not VOSK_AVAILABLE:
                    logger.error("Vosk is not installed")
                if not VOSK_MODEL_PATH.exists():
                    logger.error("Vosk model not found at %s", VOSK_MODEL_PATH)

    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file to text."""
        if not os.path.exists(audio_file_path):
            logger.error("Audio file not found: %s", audio_file_path)
            return ""

        if self.whisper_model:
            result = self._transcribe_whisper(audio_file_path)
            if result:
                return result
            logger.warning("Whisper transcription failed, trying Vosk...")

        if self.vosk_model:
            return self._transcribe_vosk(audio_file_path)

        logger.error("No speech recognition engine available")
        return ""

    def _transcribe_whisper(self, audio_file_path: str) -> str:
        """Transcribe using faster-whisper."""
        try:
            logger.info("Transcribing with faster-whisper: %s", audio_file_path)

            segments, info = self.whisper_model.transcribe(
                audio_file_path,
                beam_size=5,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            result = " ".join(text_parts).strip()
            if len(result) > 100:
                logger.info("Whisper transcription: '%s...'", result[:100])
            else:
                logger.info("Whisper transcription: '%s'", result)
            return result
        except Exception as e:
            logger.error("Whisper transcription failed: %s", e, exc_info=True)
            return ""

    def _transcribe_vosk(self, audio_file_path: str) -> str:
        """Transcribe using Vosk."""
        try:
            logger.info("Transcribing with Vosk: %s", audio_file_path)

            with wave.open(audio_file_path, "rb") as wf:
                if wf.getnchannels() != 1:
                    logger.warning(
                        "Audio has %s channels, expected 1", wf.getnchannels()
                    )
                if wf.getsampwidth() != 2:
                    logger.warning(
                        "Audio sample width is %s, expected 2", wf.getsampwidth()
                    )

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

            result = " ".join(results).strip()
            if len(result) > 100:
                logger.info("Vosk transcription: '%s...'", result[:100])
            else:
                logger.info("Vosk transcription: '%s'", result)
            return result
        except Exception as e:
            logger.error("Vosk transcription failed: %s", e, exc_info=True)
            return ""


_recognizer = None


def get_recognizer() -> VoiceRecognizer:
    """Get or create the voice recognizer singleton."""
    global _recognizer
    if _recognizer is None:
        logger.info("Initializing VoiceRecognizer...")
        _recognizer = VoiceRecognizer()
    return _recognizer


def transcribe_audio_file(audio_file_path: str) -> str:
    """Transcribe an audio file to text."""
    recognizer = get_recognizer()
    return recognizer.transcribe_audio(audio_file_path)

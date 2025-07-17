import threading
import io
import wave
import numpy as np
import sounddevice as sd
from silero_tts.silero_tts import SileroTTS


class SpeechSynthesizer:
    def __init__(self, update_status_callback):
        self.update_status = update_status_callback
        self.rate = 480   # It's not working yet
        self.volume = 0.5
        self.speech_thread = None
        self.is_playing = False

        self.tts_engine = SileroTTS(
            model_id='v4_ru',
            language='ru',
            speaker='baya',
            sample_rate=48000,
            device='auto'
        )

    def configure_voice(self, rate=None, volume=None):
        if rate is not None:
            self.rate = rate
        if volume is not None:
            self.volume = volume

    def speak(self, text):
        if self.speech_thread and self.speech_thread.is_alive():
            self.stop()

        self.speech_thread = threading.Thread(target=self._speak, args=(text,))
        self.speech_thread.start()

    def _speak(self, text):
        self.is_playing = True
        try:
            audio_buffer = io.BytesIO()
            self.tts_engine.tts(text, audio_buffer)
            audio_buffer.seek(0)

            with wave.open(audio_buffer, 'rb') as wav_file:
                n_channels = wav_file.getnchannels()
                framerate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                audio_bytes = wav_file.readframes(n_frames)

            audio_numpy = np.frombuffer(audio_bytes, dtype=np.int16)

            if self.volume != 1.0:
                audio_float = audio_numpy.astype(np.float32) * self.volume
                audio_numpy = np.clip(audio_float, -32768, 32767).astype(np.int16)

            sd.play(audio_numpy, samplerate=framerate)
            sd.wait()

        except Exception as e:
            self.update_status(f"Ошибка синтеза речи: {str(e)}")
        finally:
            self.is_playing = False

    def stop(self):
        sd.stop()
        self.is_playing = False

        if self.speech_thread and self.speech_thread.is_alive():
            try:
                self.speech_thread.join(timeout=0.5)
            except Exception as e:
                self.update_status(f"Ошибка остановки потока: {str(e)}")

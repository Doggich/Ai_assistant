import threading
import pyttsx3


class SpeechSynthesizer:
    def __init__(self, update_status_callback):
        self.speech_engine = None
        self.speech_thread = None
        self.update_status = update_status_callback
        self.rate = 250
        self.volume = 0.9

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
        try:
            self.speech_engine = pyttsx3.init()
            self.speech_engine.setProperty('rate', self.rate)
            self.speech_engine.setProperty('volume', self.volume)
            self.speech_engine.say(text)
            self.speech_engine.runAndWait()
        except Exception as e:
            self.update_status(f"Ошибка синтеза речи: {str(e)}")
        finally:
            self.speech_engine = None

    def stop(self):
        if self.speech_engine:
            try:
                self.speech_engine.stop()
            except Exception as e:
                self.update_status(f"Ошибка остановки: {str(e)}")
            self.speech_engine = None

        if self.speech_thread and self.speech_thread.is_alive():
            try:
                self.speech_thread.join(timeout=0.5)
            except Exception as e:
                self.update_status(f"Ошибка остановки потока: {str(e)}")
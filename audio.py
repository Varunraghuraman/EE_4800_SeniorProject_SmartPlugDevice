"""Audio input pipeline using sounddevice + Vosk.

Auto-detects mic's native sample rate, downsamples to 16 kHz for Vosk.
"""

import json
import queue
import threading
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

VOSK_SAMPLE_RATE = 16000   # Vosk was trained at 16 kHz, don't change this


class AudioPipeline:
    def __init__(self, model_path: str, mic_device_index: int):
        print(f"[audio] Loading Vosk model from {model_path}...")
        self.model = Model(model_path)
        print("[audio] Model loaded.")

        self.recognizer = KaldiRecognizer(self.model, VOSK_SAMPLE_RATE)
        self.mic_device_index = mic_device_index

        device_info = sd.query_devices(mic_device_index, 'input')
        self.mic_sample_rate = int(device_info['default_samplerate'])
        print(f"[audio] Mic native rate: {self.mic_sample_rate} Hz")
        print(f"[audio] Target rate for Vosk: {VOSK_SAMPLE_RATE} Hz")

        self.resample_ratio = self.mic_sample_rate / VOSK_SAMPLE_RATE
        print(f"[audio] Resample ratio: {self.resample_ratio:.4f}")

        self.block_size = int(self.mic_sample_rate * 0.5)

        self.audio_q = queue.Queue()
        self.text_q = queue.Queue()
        self._stop = threading.Event()

    def _resample(self, samples):
        if self.resample_ratio == 1.0:
            return samples
        target_len = int(len(samples) / self.resample_ratio)
        indices = np.linspace(0, len(samples) - 1, target_len)
        resampled = np.interp(indices, np.arange(len(samples)), samples)
        return resampled.astype(np.int16)

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[audio] status: {status}", flush=True)
        samples = np.frombuffer(indata, dtype=np.int16)
        resampled = self._resample(samples)
        self.audio_q.put(resampled.tobytes())

    def _recognition_loop(self):
        while not self._stop.is_set():
            try:
                data = self.audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    self.text_q.put(text)

    def start(self):
        self._stop.clear()
        self.stream = sd.RawInputStream(
            samplerate=self.mic_sample_rate,
            blocksize=self.block_size,
            device=self.mic_device_index,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.rec_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.rec_thread.start()
        print(f"[audio] Pipeline started (mic {self.mic_sample_rate}Hz -> Vosk {VOSK_SAMPLE_RATE}Hz).")

    def stop(self):
        self._stop.set()
        self.stream.stop()
        self.stream.close()
        print("[audio] Pipeline stopped.")

    def get_phrase(self, timeout=0.1):
        try:
            return self.text_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def flush(self):
        while not self.text_q.empty():
            try:
                self.text_q.get_nowait()
            except queue.Empty:
                break
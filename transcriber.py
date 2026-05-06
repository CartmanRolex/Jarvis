from groq import Groq


class Transcriber:
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        self._client = Groq(api_key=api_key)
        self._model = model

    def transcribe(self, audio_bytes: bytes) -> str:
        result = self._client.audio.transcriptions.create(
            file=("audio.ogg", audio_bytes),
            model=self._model,
        )
        return result.text

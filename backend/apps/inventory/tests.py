from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from farm_products.models import FarmProductCategory, FarmProductItem
from seeds.models import SeedCategory, SeedItem

from .views import _normalize_voice_transcript, _voice_compare_text


class FakeWhisperModel:
    def __init__(self, transcript):
        self.transcript = transcript
        self.last_call = {}

    def transcribe(
        self,
        audio_path,
        language=None,
        beam_size=None,
        best_of=None,
        temperature=None,
        condition_on_previous_text=None,
        vad_filter=None,
        initial_prompt=None,
        hotwords=None,
        repetition_penalty=None,
        no_repeat_ngram_size=None,
        compression_ratio_threshold=None,
        log_prob_threshold=None,
        no_speech_threshold=None,
        hallucination_silence_threshold=None,
    ):
        self.last_call = {
            "audio_path": audio_path,
            "language": language,
            "beam_size": beam_size,
            "best_of": best_of,
            "temperature": temperature,
            "condition_on_previous_text": condition_on_previous_text,
            "vad_filter": vad_filter,
            "initial_prompt": initial_prompt,
            "hotwords": hotwords,
            "repetition_penalty": repetition_penalty,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "compression_ratio_threshold": compression_ratio_threshold,
            "log_prob_threshold": log_prob_threshold,
            "no_speech_threshold": no_speech_threshold,
            "hallucination_silence_threshold": hallucination_silence_threshold,
        }
        return [SimpleNamespace(text=self.transcript)], SimpleNamespace(language=language)


class SequencedWhisperModel:
    def __init__(self, transcripts):
        self.transcripts = list(transcripts)
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append({"audio_path": audio_path, **kwargs})
        transcript = self.transcripts.pop(0) if self.transcripts else ""
        return [SimpleNamespace(text=transcript)], SimpleNamespace(language=kwargs.get("language"))


class InventoryVoiceInputTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="voice-user",
            password="secret123",
        )
        self.client.force_login(self.user)

        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=seed_category, name="Buğda")

        farm_category = FarmProductCategory.objects.create(name="Yumurta")
        FarmProductItem.objects.create(category=farm_category, name="Hinduşka yumurtası", unit="ədəd")

    def test_normalize_voice_transcript_uses_catalog_terms_for_azerbaijani(self):
        normalized = _normalize_voice_transcript("xerca elave et bugada miqdar on kilo", "az")

        self.assertEqual(
            _voice_compare_text(normalized),
            _voice_compare_text("xərc əlavə et Buğda miqdar on kilo"),
        )
        self.assertIn("Buğda", normalized)

    def test_normalize_voice_transcript_maps_animal_aliases_for_azerbaijani(self):
        normalized = _normalize_voice_transcript("heyvan elave et inerc ceki min dort yuz", "az")

        self.assertEqual(
            _voice_compare_text(normalized),
            _voice_compare_text("heyvan əlavə et inək çəki min dörd yüz"),
        )
        self.assertIn("inək", normalized.lower())

    def test_normalize_voice_transcript_maps_gender_aliases_for_azerbaijani(self):
        normalized = _normalize_voice_transcript("heyvan elave et qoyun tişi", "az")

        self.assertEqual(
            _voice_compare_text(normalized),
            _voice_compare_text("heyvan əlavə et qoyun dişi"),
        )
        self.assertIn("dişi", normalized.lower())

    def test_voice_transcribe_returns_normalized_transcript_and_uses_stronger_options(self):
        fake_model = FakeWhisperModel("xerca elave et bugada miqdar on kilo")

        with patch("inventory.views._get_whisper_model", return_value=fake_model):
            response = self.client.post(
                reverse("inventory:voice_transcribe"),
                {
                    "language": "az",
                    "audio": SimpleUploadedFile("voice-input.webm", b"fake-audio", content_type="audio/webm"),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["transcript"], "xerca elave et bugada miqdar on kilo")
        self.assertEqual(
            _voice_compare_text(payload["normalized_transcript"]),
            _voice_compare_text("xərc əlavə et Buğda miqdar on kilo"),
        )

        self.assertEqual(fake_model.last_call["language"], "az")
        self.assertEqual(fake_model.last_call["beam_size"], 7)
        self.assertEqual(fake_model.last_call["best_of"], 5)
        self.assertEqual(fake_model.last_call["temperature"], 0.0)
        self.assertIs(fake_model.last_call["condition_on_previous_text"], False)
        self.assertIs(fake_model.last_call["vad_filter"], True)
        self.assertTrue(fake_model.last_call["initial_prompt"])
        self.assertIn("Buğda", fake_model.last_call["hotwords"])
        self.assertEqual(fake_model.last_call["repetition_penalty"], 1.15)
        self.assertEqual(fake_model.last_call["no_repeat_ngram_size"], 2)

    def test_voice_transcribe_retries_when_transcript_is_repetitive(self):
        fake_model = SequencedWhisperModel([
            "heyvan elave et inek disi miqdar bir meblek meblek meblek meblek me",
            "heyvan elave et inek disi miqdar bir ceki dord yuz mebleg min bes yuz",
        ])

        with patch("inventory.views._get_whisper_model", return_value=fake_model):
            response = self.client.post(
                reverse("inventory:voice_transcribe"),
                {
                    "language": "az",
                    "audio": SimpleUploadedFile("voice-input.webm", b"fake-audio", content_type="audio/webm"),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(
            _voice_compare_text(payload["transcript"]),
            _voice_compare_text("heyvan elave et inek disi miqdar bir ceki dord yuz mebleg min bes yuz"),
        )
        self.assertGreaterEqual(len(fake_model.calls), 2)
        self.assertEqual(fake_model.calls[0]["temperature"], 0.0)
        self.assertEqual(fake_model.calls[1]["temperature"], 0.2)

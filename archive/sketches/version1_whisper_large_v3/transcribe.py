import whisper
import torch
import os
from datetime import timedelta

# --- KONFIGURACJA ---
FILE_SPEAKER_A = "sciezka_mowca_1.wav"  # Podaj ścieżkę do pliku mówcy 1
FILE_SPEAKER_B = "sciezka_mowca_2.wav"  # Podaj ścieżkę do pliku mówcy 2
OUTPUT_FILE = "transkrypcja_podcastu.txt"
MODEL_SIZE = "large-v3"  # Wykorzystujemy Twój VRAM (24GB). Dla szybkości można zmienić na "medium" lub "small"
# --------------------

def format_timestamp(seconds):
    """Konwertuje sekundy na format HH:MM:SS"""
    return str(timedelta(seconds=int(seconds)))

def transcribe_track(model, file_path, speaker_label):
    print(f"--- Rozpoczynam transkrypcję: {speaker_label} ({file_path}) ---")
    
    # Parametry dobrane pod kątem eliminacji halucynacji w ciszy
    result = model.transcribe(
        file_path, 
        language="pl", 
        verbose=False,
        
        # Kluczowe dla Twojego przypadku:
        condition_on_previous_text=False, # Zapobiega pętlom powtórzeń w ciszy
        temperature=(0.0, 0.2, 0.4),      # Zmniejszamy zakres "kreatywności" modelu
        logprob_threshold=-1.0,           # Bardziej rygorystyczny próg pewności (domyślnie jest luźniejszy)
        no_speech_threshold=0.1,          # Jeśli model uzna, że to cisza/szum, nie generuje tekstu (domyślnie 0.6)
        compression_ratio_threshold=2.0   # Odrzuca segmenty, jeśli tekst jest zbyt skompresowany (oznaka pętli)
    )
    
    segments = []
    for segment in result["segments"]:
        text = segment["text"].strip()
        
        # Hard-filter: Whisper czasem generuje te konkretne znaki w ciszy
        if text in [".", "...", "?", "!", "You"]: 
            continue
            
        # Dodatkowe zabezpieczenie: ignoruj segmenty krótsze niż 0.5s (zazwyczaj szum/oddech)
        if segment["end"] - segment["start"] < 0.5:
            continue

        if not text:
            continue
            
        segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "speaker": speaker_label,
            "text": text
        })
    
    print(f"--- Zakończono: {speaker_label} ---")
    return segments

def main():
    # Sprawdzenie dostępności GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Używane urządzenie: {device.upper()}")
    if device == "cuda":
        print(f"Karta graficzna: {torch.cuda.get_device_name(0)}")

    if not os.path.exists(FILE_SPEAKER_A) or not os.path.exists(FILE_SPEAKER_B):
        print("Błąd: Nie znaleziono plików audio. Sprawdź ścieżki w konfiguracji.")
        return

    # Ładowanie modelu
    print(f"Ładowanie modelu Whisper ({MODEL_SIZE})...")
    try:
        model = whisper.load_model(MODEL_SIZE, device=device)
    except torch.cuda.OutOfMemoryError:
        print("Błąd: Za mało pamięci VRAM. Spróbuj mniejszego modelu (np. 'medium').")
        return

    # Transkrypcja obu ścieżek
    segments_a = transcribe_track(model, FILE_SPEAKER_A, "Mówca 1")
    segments_b = transcribe_track(model, FILE_SPEAKER_B, "Mówca 2")

    # Scalanie i sortowanie chronologiczne
    all_segments = segments_a + segments_b
    # Sortujemy po czasie rozpoczęcia wypowiedzi
    all_segments.sort(key=lambda x: x["start"])

    # Zapis do pliku
    print(f"Zapisywanie wyników do {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for seg in all_segments:
            timestamp = format_timestamp(seg["start"])
            line = f"[{timestamp}] {seg['speaker']}: {seg['text']}\n"
            f.write(line)
            # Opcjonalnie wypisz na ekran
            # print(line.strip())

    print("Gotowe.")

if __name__ == "__main__":
    main()
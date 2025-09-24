import cv2
import mediapipe as mp
import time
import math
import numpy as np
from datetime import datetime
import csv
import os
import pygame

# Definicja instrumentów z pozycjami (powtórzone z main.py dla niezależności)
INSTRUMENTS = [
    {"name": "Pianino", "pos": (150, 100), "color": (255, 100, 100)},
    {"name": "Trabka", "pos": (400, 150), "color": (100, 255, 100)},
    {"name": "Harfa", "pos": (550, 120), "color": (100, 100, 255)},
    {"name": "Gitara", "pos": (200, 300), "color": (255, 255, 100)},
    {"name": "Perkusja", "pos": (500, 350), "color": (255, 100, 255)},
    {"name": "Flet", "pos": (350, 250), "color": (100, 255, 255)},
]

pygame.mixer.init()

# Załaduj dźwięki instrumentów
for instrument in INSTRUMENTS:
    instrument_name = instrument["name"].lower()
    instrument["sound"] = pygame.mixer.Sound(f"sound/{instrument_name}.mp3")

INSTRUMENT_RADIUS = 40
HIGHLIGHT_RADIUS = 60
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"
CSV_FILE = "played_instruments.csv"

class PlaygroundMode:
    def __init__(self, control_mode):
        self.control_mode = control_mode
        self.played_instruments = []  # Lista przechowująca zagrane instrumenty
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_duration_needed = 1.0  # Czas potrzebny do aktywacji (1 sekunda)
        self.hover_progress = 0.0
        self.last_touch_time = 0
        self.touch_cooldown = 0.5  # 0.5 sekundy między dotknięciami (dla myszy)
        # Inicjalizuj plik CSV z nagłówkami, jeśli nie istnieje
        self.init_csv()

    def init_csv(self):
        """Inicjalizuje plik CSV z nagłówkami, jeśli nie istnieje"""
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Instrument"])

    def save_to_csv(self, timestamp, instrument_name):
        """Zapisuje zagrany instrument do pliku CSV"""
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, instrument_name])

    def activate_instrument(self, instrument_index):
        """Aktywuje instrument i zapisuje go do pliku CSV"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        instrument_name = INSTRUMENTS[instrument_index]["name"]
        instrument_index = instrument_index  # już masz przekazany do funkcji
        INSTRUMENTS[instrument_index]["sound"].play()
        INSTRUMENTS[instrument_index]["sound"].set_volume(0.8)  # 0.0 - 1.0
        self.played_instruments.append({"timestamp": timestamp, "instrument": instrument_name})
        print(f"Zagrano: {instrument_name} o {timestamp}")
        self.save_to_csv(timestamp, instrument_name)
        # Ograniczamy listę w pamięci do ostatnich 10 wpisów
        if len(self.played_instruments) > 10:
            self.played_instruments.pop(0)

    def update_hover(self, x, y):
        """Aktualizuje stan hover dla trybu ręki"""
        if self.control_mode != CONTROL_HAND:
            return
        
        current_time = time.time()
        hovered_instrument = -1
        for i, instrument in enumerate(INSTRUMENTS):
            dist = math.sqrt((x - instrument["pos"][0])**2 + (y - instrument["pos"][1])**2)
            if dist <= INSTRUMENT_RADIUS:
                hovered_instrument = i
                break
        
        if hovered_instrument != self.hover_instrument:
            if hovered_instrument >= 0:
                self.hover_instrument = hovered_instrument
                self.hover_start_time = current_time
                self.hover_progress = 0.0
            else:
                self.reset_hover_state()
        
        if self.hover_instrument >= 0:
            hover_elapsed = current_time - self.hover_start_time
            self.hover_progress = min(hover_elapsed / self.hover_duration_needed, 1.0)
            if self.hover_progress >= 1.0:
                self.activate_instrument(self.hover_instrument)
                self.reset_hover_state()

    def reset_hover_state(self):
        """Resetuje stan hover"""
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_progress = 0.0

    def check_touch(self, x, y):
        """Sprawdza kliknięcie myszą"""
        if self.control_mode != CONTROL_MOUSE:
            return
        
        current_time = time.time()
        if current_time - self.last_touch_time < self.touch_cooldown:
            return
        
        for i, instrument in enumerate(INSTRUMENTS):
            dist = math.sqrt((x - instrument["pos"][0])**2 + (y - instrument["pos"][1])**2)
            if dist <= INSTRUMENT_RADIUS:
                self.activate_instrument(i)
                self.last_touch_time = current_time
                break

    def is_point_in_game_area(self, x, y, frame_width, frame_height):
        """Sprawdza czy punkt znajduje się w obszarze gry"""
        margin = 50
        return (margin <= x <= frame_width - margin and 
                margin <= y <= frame_height - margin)

def run_playground(control_mode):
    # Inicjalizacja MediaPipe (tylko dla trybu ręki)
    mp_hands = None
    hands = None
    if control_mode == CONTROL_HAND:
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            max_num_hands=1
        )

    # Inicjalizacja kamery i gry
    playground = PlaygroundMode(control_mode)
    cap = cv2.VideoCapture(0)
    cv2.namedWindow('Tryb Własna Melodia', cv2.WINDOW_NORMAL)

    # Zmienne dla myszy
    mouse_x, mouse_y = 0, 0
    mouse_clicked = False

    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_x, mouse_y, mouse_clicked
        mouse_x, mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_clicked = True

    if control_mode == CONTROL_MOUSE:
        cv2.setMouseCallback('Tryb Własna Melodia', mouse_callback)

    print("🎵 Tryb Własna Melodia 🎵")
    print(f"Graj dowolne melodie na instrumentach! Sekwencja zapisywana do {CSV_FILE}")
    if control_mode == CONTROL_HAND:
        print("Trzymaj palec wskazujący prawej ręki nad instrumentem przez 1 sekundę.")
    else:
        print("Użyj myszy do klikania na instrumenty.")
    print("Naciśnij ESC aby zakończyć.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Błąd: Nie można odczytać klatki z kamery")
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        cursor_x, cursor_y = None, None
        if control_mode == CONTROL_HAND:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    if handedness.classification[0].label == 'Right':
                        finger_tip = hand_landmarks.landmark[8]
                        cursor_x = int(finger_tip.x * w)
                        cursor_y = int(finger_tip.y * h)
                        break
        elif control_mode == CONTROL_MOUSE:
            cursor_x, cursor_y = mouse_x, mouse_y
            if not playground.is_point_in_game_area(cursor_x, cursor_y, w, h):
                cursor_x, cursor_y = None, None

        # Aktualizuj interakcje
        if control_mode == CONTROL_HAND and cursor_x is not None and cursor_y is not None:
            playground.update_hover(cursor_x, cursor_y)
        elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None and cursor_y is not None:
            playground.check_touch(cursor_x, cursor_y)
            mouse_clicked = False
        elif control_mode == CONTROL_HAND and cursor_x is None:
            playground.reset_hover_state()

        # Rysuj tło
        cv2.rectangle(frame, (0, 0), (w, h), (20, 20, 20), -1)

        # Rysuj instrumenty
        for i, instrument in enumerate(INSTRUMENTS):
            pos = instrument["pos"]
            color = instrument["color"]
            is_hover_highlight = (control_mode == CONTROL_HAND and playground.hover_instrument == i)
            
            if is_hover_highlight:
                cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
                cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
                if playground.hover_progress > 0:
                    angle_end = int(360 * playground.hover_progress)
                    overlay = frame.copy()
                    cv2.ellipse(overlay, pos, (HIGHLIGHT_RADIUS, HIGHLIGHT_RADIUS), 
                               -90, 0, angle_end, (0, 255, 0), 4)
                    frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
                    progress_text = f"{int(playground.hover_progress * 100)}%"
                    text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                    text_pos = (pos[0] - text_size[0] // 2, pos[1] + 5)
                    cv2.putText(frame, progress_text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            else:
                cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
                cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)

            # Rysuj nazwę instrumentu
            text_size = cv2.getTextSize(instrument["name"], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            text_x = pos[0] - text_size[0] // 2
            text_y = pos[1] + INSTRUMENT_RADIUS + 20
            cv2.rectangle(frame, (text_x - 5, text_y - 15), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
            cv2.putText(frame, instrument["name"], (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Rysuj kursor
        if cursor_x is not None and cursor_y is not None:
            if control_mode == CONTROL_HAND:
                cv2.circle(frame, (cursor_x, cursor_y), 8, (0, 255, 0), -1)
                cv2.circle(frame, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
            else:
                cv2.circle(frame, (cursor_x, cursor_y), 6, (255, 0, 0), -1)
                cv2.circle(frame, (cursor_x, cursor_y), 10, (255, 255, 255), 2)

        # Rysuj granice obszaru gry (dla myszy)
        if control_mode == CONTROL_MOUSE:
            cv2.rectangle(frame, (50, 50), (w-50, h-50), (100, 100, 100), 2)

        # Rysuj informacje o trybie
        info_text = "Tryb Własna Melodia - graj swobodnie!"
        text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.rectangle(frame, (10, 5), (text_size[0] + 20, 40), (0, 0, 0), -1)
        cv2.putText(frame, info_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)

        control_text = f"Tryb: {'Ręka (1s hover)' if control_mode == CONTROL_HAND else 'Mysz (klik)'}"
        cv2.rectangle(frame, (w - 170, 5), (w - 10, 40), (0, 0, 0), -1)
        cv2.putText(frame, control_text, (w - 165, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Wyświetl klatkę
        cv2.imshow('Tryb Własna Melodia', frame)

        # Sprawdź wyjście
        if cv2.waitKey(1) & 0xFF == 27:
            break
        if cv2.getWindowProperty('Tryb Własna Melodia', cv2.WND_PROP_VISIBLE) < 1:
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if hands:
        hands.close()
    print("Dziękuję za grę w trybie Własna Melodia! 🎵")
    print(f"Sekwencja zapisana w {CSV_FILE}")

if __name__ == "__main__":
    # Placeholder: Tryb powinien być wybrany w main.py
    run_playground(CONTROL_MOUSE)
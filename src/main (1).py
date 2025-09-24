import cv2
import mediapipe as mp
import threading
import time
import random
import math
import numpy as np
from playground import run_playground  # Import the playground mode

# Definicja instrumentów z pozycjami
INSTRUMENTS = [
    {"name": "Pianino", "pos": (150, 100), "color": (255, 100, 100)},
    {"name": "Harmonijka", "pos": (400, 150), "color": (100, 255, 100)},
    {"name": "Organy", "pos": (550, 120), "color": (100, 100, 255)},
    {"name": "Gitara", "pos": (200, 300), "color": (255, 255, 100)},
    {"name": "Skrzypce", "pos": (500, 350), "color": (255, 100, 255)},
    {"name": "Flet", "pos": (350, 250), "color": (100, 255, 255)},
]

INSTRUMENT_RADIUS = 40
HIGHLIGHT_RADIUS = 60

# Tryby sterowania
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"

# Stany gry
GAME_STATE_SHOWING = "showing_sequence"
GAME_STATE_WAITING = "waiting_for_input"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_SUCCESS = "sequence_success"

# Tryby gry
MODE_SINGLE = 1
MODE_DOUBLE = 2
MODE_PLAYGROUND = 3

class MusicalGame:
    def __init__(self, control_mode=CONTROL_HAND):
        self.sequence = []
        self.current_sequence_index = 0
        self.player_sequence = []
        self.game_state = GAME_STATE_SHOWING
        self.highlight_instrument = -1
        self.highlight_start_time = 0
        self.sequence_display_index = 0
        self.level = 1
        self.last_touch_time = 0
        self.touch_cooldown = 0.5
        self.control_mode = control_mode
        self.sequence_completed_time = 0
        self.waiting_for_next_level = False
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_duration_needed = 1.0
        self.hover_progress = 0.0
        self.generate_new_sequence()
        
    def generate_new_sequence(self):
        self.sequence = []
        sequence_length = min(self.level + 1, 6)
        for _ in range(sequence_length):
            self.sequence.append(random.randint(0, len(INSTRUMENTS) - 1))
        print(f"Nowa sekwencja (poziom {self.level}): {[INSTRUMENTS[i]['name'] for i in self.sequence]}")
        self.reset_for_new_sequence()
        
    def reset_for_new_sequence(self):
        self.current_sequence_index = 0
        self.player_sequence = []
        self.game_state = GAME_STATE_SHOWING
        self.sequence_display_index = 0
        self.highlight_instrument = -1
        self.highlight_start_time = time.time()
        self.reset_hover_state()
        
    def update(self):
        current_time = time.time()
        if self.game_state == GAME_STATE_SHOWING:
            if self.sequence_display_index < len(self.sequence):
                cycle_time = current_time - self.highlight_start_time
                if cycle_time < 0.8:
                    self.highlight_instrument = self.sequence[self.sequence_display_index]
                elif cycle_time < 1.1:
                    self.highlight_instrument = -1
                else:
                    self.sequence_display_index += 1
                    self.highlight_start_time = current_time
            else:
                self.game_state = GAME_STATE_WAITING
                self.highlight_instrument = -1
                print("Twoja kolej! Powtórz sekwencję.")
        elif self.game_state == GAME_STATE_SUCCESS:
            if self.waiting_for_next_level and current_time - self.sequence_completed_time > 1.5:
                self.level += 1
                self.waiting_for_next_level = False
                self.generate_new_sequence()
    
    def reset_hover_state(self):
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_progress = 0.0
    
    def update_hover(self, x, y):
        if self.control_mode != CONTROL_HAND or self.game_state != GAME_STATE_WAITING:
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
    
    def check_touch(self, x, y):
        if self.control_mode != CONTROL_MOUSE or self.game_state != GAME_STATE_WAITING:
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
    
    def activate_instrument(self, instrument_index):
        self.player_sequence.append(instrument_index)
        expected_instrument = self.sequence[self.current_sequence_index]
        print(f"Aktywowano: {INSTRUMENTS[instrument_index]['name']}")
        if instrument_index == expected_instrument:
            print("✓ Dobrze!")
            self.current_sequence_index += 1
            if self.current_sequence_index >= len(self.sequence):
                print(f"🎉 Poziom {self.level} ukończony!")
                self.game_state = GAME_STATE_SUCCESS
                self.sequence_completed_time = time.time()
                self.waiting_for_next_level = True
        else:
            print(f"✗ Błąd! Oczekiwano: {INSTRUMENTS[expected_instrument]['name']}")
            print("Gra zakończona. Rozpoczynam od nowa...")
            self.level = 1
            self.generate_new_sequence()
    
    def is_point_in_game_area(self, x, y, frame_width, frame_height):
        margin = 50
        return (margin <= x <= frame_width - margin and 
                margin <= y <= frame_height - margin)

# Funkcja obsługi myszy
mouse_x, mouse_y = 0, 0
mouse_clicked = False

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y, mouse_clicked
    mouse_x, mouse_y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True

selected_mode = None
def mouse_callback1(event, x, y, flags, param):
    global selected_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 < x < 250 and 80 < y < 140:
            selected_mode = CONTROL_HAND
        elif 50 < x < 250 and 180 < y < 240:
            selected_mode = CONTROL_MOUSE

game_mode = None
def mouse_callback_game_mode(event, x, y, flags, param):
    global game_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 < x < 250 and 80 < y < 140:
            game_mode = MODE_SINGLE
        elif 50 < x < 250 and 180 < y < 240:
            game_mode = MODE_DOUBLE
        elif 50 < x < 250 and 280 < y < 340:
            game_mode = MODE_PLAYGROUND

def choose_game_mode():
    global game_mode
    game_mode = None
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Wybierz tryb gry:", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 80), (250, 140), (200, 200, 200), -1)
    cv2.putText(img, "1. Jeden gracz", (60, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 180), (250, 240), (200, 200, 200), -1)
    cv2.putText(img, "2. Dwóch graczy", (60, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 280), (250, 340), (200, 200, 200), -1)
    cv2.putText(img, "3. Własna melodia", (60, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.namedWindow("Wybór trybu gry")
    cv2.setMouseCallback("Wybór trybu gry", mouse_callback_game_mode)
    while True:
        cv2.imshow("Wybór trybu gry", img)
        if cv2.getWindowProperty("Wybór trybu gry", cv2.WND_PROP_VISIBLE) < 1:
            game_mode = None
            break
        if game_mode is not None:
            break
        if cv2.waitKey(20) & 0xFF == 27:
            game_mode = None
            break
    cv2.destroyWindow("Wybór trybu gry")
    return game_mode

def choose_control_mode():
    global selected_mode
    img = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Wybierz tryb sterowania:", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 80), (250, 140), (200, 200, 200), -1)
    cv2.putText(img, "1. Reka (kamera)", (60, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 180), (250, 240), (200, 200, 200), -1)
    cv2.putText(img, "2. Myszka", (60, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.namedWindow("Wybór trybu")
    cv2.setMouseCallback("Wybór trybu", mouse_callback1)
    while True:
        cv2.imshow("Wybór trybu", img)
        if cv2.getWindowProperty("Wybór trybu", cv2.WND_PROP_VISIBLE) < 1:
            selected_mode = None
            break
        if selected_mode is not None:
            break
        if cv2.waitKey(20) & 0xFF == 27:
            selected_mode = None
            break
    cv2.destroyWindow("Wybór trybu")
    return selected_mode

def cleanup():
    cap.release()
    cv2.destroyAllWindows()
    print("Dziękuję za grę! 🎵")

# Wybór trybu sterowania i gry
control_mode = choose_control_mode()
if control_mode is None:
    cleanup()
    exit()

game_mode = choose_game_mode()
if game_mode is None:
    cleanup()
    exit()

# Uruchom odpowiedni tryb gry
if game_mode == MODE_PLAYGROUND:
    run_playground(control_mode)
    exit()
elif game_mode == MODE_DOUBLE:
    print("Tryb dla dwóch graczy nie jest jeszcze zaimplementowany.")
    cleanup()
    exit()

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

# Inicjalizacja gry i kamery
game = MusicalGame(control_mode)
cap = cv2.VideoCapture(0)
cv2.namedWindow('Edukacyjna Gra Muzyczna', cv2.WINDOW_NORMAL)

if control_mode == CONTROL_MOUSE:
    cv2.setMouseCallback('Edukacyjna Gra Muzyczna', mouse_callback)

print("🎵 Edukacyjna Gra Muzyczna 🎵")
print("Obserwuj sekwencję podświetlanych instrumentów, a następnie powtórz ją!")
if control_mode == CONTROL_HAND:
    print("Trzymaj palec wskazujący prawej ręki nad instrumentem przez 1 sekundę aby go wybrać.")
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
        if not game.is_point_in_game_area(cursor_x, cursor_y, w, h):
            cursor_x, cursor_y = None, None
    game.update()
    if control_mode == CONTROL_HAND and cursor_x is not None and cursor_y is not None:
        game.update_hover(cursor_x, cursor_y)
    elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None and cursor_y is not None:
        game.check_touch(cursor_x, cursor_y)
        mouse_clicked = False
    elif control_mode == CONTROL_HAND and cursor_x is None:
        game.reset_hover_state()
    cv2.rectangle(frame, (0, 0), (w, h), (20, 20, 20), -1)
    for i, instrument in enumerate(INSTRUMENTS):
        pos = instrument["pos"]
        color = instrument["color"]
        is_sequence_highlight = (game.highlight_instrument == i)
        is_hover_highlight = (control_mode == CONTROL_HAND and game.hover_instrument == i)
        if is_sequence_highlight:
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS, (255, 255, 255), 3)
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS - 5, color, -1)
        elif is_hover_highlight:
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
            if game.hover_progress > 0:
                angle_end = int(360 * game.hover_progress)
                overlay = frame.copy()
                cv2.ellipse(overlay, pos, (HIGHLIGHT_RADIUS, HIGHLIGHT_RADIUS), 
                           -90, 0, angle_end, (0, 255, 0), 4)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
                progress_text = f"{int(game.hover_progress * 100)}%"
                text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                text_pos = (pos[0] - text_size[0] // 2, pos[1] + 5)
                cv2.putText(frame, progress_text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        else:
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
        text_size = cv2.getTextSize(instrument["name"], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        text_x = pos[0] - text_size[0] // 2
        text_y = pos[1] + INSTRUMENT_RADIUS + 20
        cv2.rectangle(frame, (text_x - 5, text_y - 15), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
        cv2.putText(frame, instrument["name"], (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    if cursor_x is not None and cursor_y is not None:
        if control_mode == CONTROL_HAND:
            cv2.circle(frame, (cursor_x, cursor_y), 8, (0, 255, 0), -1)
            cv2.circle(frame, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
        else:
            cv2.circle(frame, (cursor_x, cursor_y), 6, (255, 0, 0), -1)
            cv2.circle(frame, (cursor_x, cursor_y), 10, (255, 255, 255), 2)
    if control_mode == CONTROL_MOUSE:
        cv2.rectangle(frame, (50, 50), (w-50, h-50), (100, 100, 100), 2)
    info_y = 30
    if game.game_state == GAME_STATE_SHOWING:
        info_text = f"Obserwuj sekwencję... ({game.sequence_display_index + 1}/{len(game.sequence)})"
        color = (100, 255, 255)
    elif game.game_state == GAME_STATE_WAITING:
        info_text = f"Twoja kolej! Postęp: {len(game.player_sequence)}/{len(game.sequence)}"
        if control_mode == CONTROL_HAND and game.hover_instrument >= 0:
            info_text += f" | Hover: {int(game.hover_progress * 100)}%"
        color = (100, 255, 100)
    elif game.game_state == GAME_STATE_SUCCESS:
        if game.waiting_for_next_level:
            info_text = "🎉 Świetnie! Przygotowuję następny poziom..."
        else:
            info_text = "🎉 Poziom ukończony!"
        color = (255, 255, 100)
    else:
        info_text = "Gra zakończona"
        color = (100, 100, 255)
    text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    cv2.rectangle(frame, (10, 5), (text_size[0] + 20, 40), (0, 0, 0), -1)
    cv2.putText(frame, info_text, (15, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    level_text = f"Poziom: {game.level}"
    control_text = f"Tryb: {'Ręka (1s hover)' if control_mode == CONTROL_HAND else 'Mysz (klik)'}"
    cv2.rectangle(frame, (w - 170, 5), (w - 10, 70), (0, 0, 0), -1)
    cv2.putText(frame, level_text, (w - 165, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, control_text, (w - 165, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.imshow('Edukacyjna Gra Muzyczna', frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break
    if cv2.getWindowProperty("Edukacyjna Gra Muzyczna", cv2.WND_PROP_VISIBLE) < 1:
        break

cleanup()
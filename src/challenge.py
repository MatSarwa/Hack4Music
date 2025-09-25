import cv2
import mediapipe as mp
import time
import random
import math
import numpy as np
import pygame
import os

# Definicja instrumentow identyczna jak w playground.py
INSTRUMENTS = [
    {"name": "Pianino", "pos": (950, 700), "size": 100, "color": (255, 100, 100), "image_file": "img/pianino.png"},
    {"name": "Trabka", "pos": (960, 270), "size": 40, "color": (100, 255, 100), "image_file": "img/trabka.png"},
    {"name": "Harfa", "pos": (600, 700), "size": 80, "color": (100, 100, 255), "image_file": "img/harfa.png"},
    {"name": "Gitara", "pos": (100, 720), "size": 60, "color": (255, 255, 100), "image_file": "img/gitara.png"},
    {"name": "Perkusja", "pos": (382, 666), "size": 83, "color": (255, 100, 255), "image_file": "img/perkusja.png"},
    {"name": "Flet", "pos": (690, 350), "size": 35, "color": (100, 255, 255), "image_file": "img/flet.png"},
    {"name": "Bass", "pos": (450, 300), "size": 75, "color": (200, 150, 50), "image_file": "img/bass.png"},
]

pygame.mixer.init()

# Zaladuj dzwieki instrumentow
for instrument in INSTRUMENTS:
    instrument_name = instrument["name"].lower()
    try:
        instrument["sound"] = pygame.mixer.Sound(f"sound/{instrument_name}.mp3")
    except:
        print(f"Nie mozna zaladowac dzwieku dla {instrument_name}")

# Stale
INSTRUMENT_RADIUS = 40
HIGHLIGHT_RADIUS = 60
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"
GAME_STATE_SHOWING = "showing_sequence"
GAME_STATE_WAITING = "waiting_for_input"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_SUCCESS = "sequence_success"

# Funkcje pomocnicze do wczytywania grafik
def load_images():
    for instrument in INSTRUMENTS:
        try:
            img = cv2.imread(instrument["image_file"], cv2.IMREAD_UNCHANGED)
            if img is not None:
                size = instrument["size"] * 2
                img = cv2.resize(img, (size, size))
                instrument["image"] = img
                instrument["original_image"] = cv2.imread(instrument["image_file"], cv2.IMREAD_UNCHANGED)
            else:
                instrument["image"] = None
        except:
            instrument["image"] = None


def load_background():
    try:
        bg = cv2.imread("img/background.png")
        if bg is None:
            print("Nie mozna zaladowac tla")
        return bg
    except:
        return None


class MusicalGame:
    def __init__(self, control_mode=CONTROL_HAND):
        self.sequence = []
        self.current_sequence_index = 0
        self.player_sequence = []
        self.game_state = GAME_STATE_SHOWING
        self.highlight_instrument = -1
        self.sequence_display_index = 0
        self.level = 1
        self.last_touch_time = 0
        self.touch_cooldown = 0.5
        self.control_mode = control_mode
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_duration_needed = 1.0
        self.hover_progress = 0.0
        self.sequence_completed_time = 0
        self.waiting_for_next_level = False

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
        self.hover_instrument = -1
        self.hover_progress = 0.0

    def update(self):
        current_time = time.time()
        if self.game_state == GAME_STATE_SHOWING:
            if self.sequence_display_index < len(self.sequence):
                instrument_index = self.sequence[self.sequence_display_index]
                instrument = INSTRUMENTS[instrument_index]
                if "sound" in instrument:
                    instrument["sound"].play()
                    time.sleep(instrument["sound"].get_length() + 0.5)
                self.sequence_display_index += 1
            else:
                self.game_state = GAME_STATE_WAITING
                print("Twoja kolej! Powtorz sekwencje.")

        elif self.game_state == GAME_STATE_SUCCESS:
            if self.waiting_for_next_level and current_time - self.sequence_completed_time > 1.5:
                self.level += 1
                self.waiting_for_next_level = False
                self.generate_new_sequence()

        if self.control_mode == CONTROL_HAND and self.game_state == GAME_STATE_WAITING:
            if self.hover_instrument >= 0:
                hover_elapsed = current_time - self.hover_start_time
                self.hover_progress = min(hover_elapsed / self.hover_duration_needed, 1.0)
                if self.hover_progress >= 1.0:
                    self.activate_instrument(self.hover_instrument)
                    self.reset_hover_state()

    def reset_hover_state(self):
        self.hover_instrument = -1
        self.hover_progress = 0.0

    def update_hover(self, x, y, frame_width, frame_height):
        if self.control_mode != CONTROL_HAND or self.game_state != GAME_STATE_WAITING:
            return
        original_bg_size = 1024
        scale_x = frame_width / original_bg_size
        scale_y = frame_height / original_bg_size
        hovered_instrument = -1
        for i, instrument in enumerate(INSTRUMENTS):
            pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
            dist = math.sqrt((x - pos[0]) * 2 + (y - pos[1]) * 2)
            if dist <= instrument["size"]:
                hovered_instrument = i
                break
        if hovered_instrument != self.hover_instrument:
            if hovered_instrument >= 0:
                self.hover_instrument = hovered_instrument
                self.hover_start_time = time.time()
                self.hover_progress = 0.0
            else:
                self.reset_hover_state()

    def check_touch(self, x, y, frame_width, frame_height):
        if self.control_mode != CONTROL_MOUSE or self.game_state != GAME_STATE_WAITING:
            return
        current_time = time.time()
        if current_time - self.last_touch_time < self.touch_cooldown:
            return
        original_bg_size = 1024
        scale_x = frame_width / original_bg_size
        scale_y = frame_height / original_bg_size
        for i, instrument in enumerate(INSTRUMENTS):
            pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
            dist = math.sqrt((x - pos[0]) * 2 + (y - pos[1]) * 2)
            if dist <= instrument["size"]:
                self.activate_instrument(i)
                self.last_touch_time = current_time
                break

    def activate_instrument(self, instrument_index):
        expected = self.sequence[self.current_sequence_index]
        INSTRUMENTS[instrument_index]["sound"].play()
        if instrument_index == expected:
            self.current_sequence_index += 1
            if self.current_sequence_index >= len(self.sequence):
                print(f"🎉 Poziom {self.level} ukonczony!")
                self.game_state = GAME_STATE_SUCCESS
                self.sequence_completed_time = time.time()
                self.waiting_for_next_level = True
        else:
            print("✗ Blad!")
            self.game_state = GAME_STATE_GAME_OVER


def draw_instrument(frame, instrument, index, game, frame_w, frame_h):
    original_bg_size = 1024
    scale_x = frame_w / original_bg_size
    scale_y = frame_h / original_bg_size
    pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))

    if "image" in instrument and instrument["image"] is not None:
        img = instrument["image"]
        h, w = img.shape[:2]
        x1, y1 = pos[0] - w // 2, pos[1] - h // 2
        x2, y2 = x1 + w, y1 + h
        if 0 <= x1 and 0 <= y1 and x2 <= frame_w and y2 <= frame_h:
            if img.shape[2] == 4:
                bgr = img[:, :, :3]
                alpha = img[:, :, 3] / 255.0
                for c in range(3):
                    frame[y1:y2, x1:x2, c] = alpha * bgr[:, :, c] + (1 - alpha) * frame[y1:y2, x1:x2, c]
            else:
                frame[y1:y2, x1:x2] = img
    cv2.putText(frame, instrument["name"], (pos[0], pos[1] + instrument["size"] + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def run_challenge(control_mode):
    mp_hands = None
    hands = None
    if control_mode == CONTROL_HAND:
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=1)

    load_images()
    background = load_background()
    game = MusicalGame(control_mode)
    cap = cv2.VideoCapture(0)
    cv2.namedWindow('Edukacyjna Gra Muzyczna - Wyzwanie', cv2.WINDOW_NORMAL)

    mouse_x, mouse_y, mouse_clicked = 0, 0, False

    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_x, mouse_y, mouse_clicked
        mouse_x, mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_clicked = True

    if control_mode == CONTROL_MOUSE:
        cv2.setMouseCallback('Edukacyjna Gra Muzyczna - Wyzwanie', mouse_callback)

    while True:
        if background is not None:
            bg_h, bg_w = background.shape[:2]
            scale = min(800 / bg_w, 600 / bg_h)
            frame_w, frame_h = int(bg_w * scale), int(bg_h * scale)
            frame = cv2.resize(background, (frame_w, frame_h))
        else:
            frame_h, frame_w = 600, 800
            frame = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)

        cursor_x, cursor_y = None, None
        if control_mode == CONTROL_HAND:
            ret_cam, cam_frame = cap.read()
            if ret_cam:
                cam_frame = cv2.flip(cam_frame, 1)
                cam_frame = cv2.resize(cam_frame, (frame_w, frame_h))
                rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                if results.multi_hand_landmarks and results.multi_handedness:
                    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        if handedness.classification[0].label == 'Right':
                            finger_tip = hand_landmarks.landmark[8]
                            cursor_x = int(finger_tip.x * frame_w)
                            cursor_y = int(finger_tip.y * frame_h)
                            break
        elif control_mode == CONTROL_MOUSE:
            cursor_x, cursor_y = mouse_x, mouse_y

        game.update()

        if control_mode == CONTROL_HAND and cursor_x is not None:
            game.update_hover(cursor_x, cursor_y, frame_w, frame_h)
        elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None:
            game.check_touch(cursor_x, cursor_y, frame_w, frame_h)
            mouse_clicked = False
        elif control_mode == CONTROL_HAND and cursor_x is None:
            game.reset_hover_state()

        for i, instrument in enumerate(INSTRUMENTS):
            draw_instrument(frame, instrument, i, game, frame_w, frame_h)

        if cursor_x is not None and cursor_y is not None:
            cv2.circle(frame, (cursor_x, cursor_y), 8, (0, 255, 0) if control_mode == CONTROL_HAND else (255, 0, 0), -1)

        cv2.imshow('Edukacyjna Gra Muzyczna - Wyzwanie', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    if hands:
        hands.close()


if __name__ == "_main_":
    run_challenge(CONTROL_MOUSE)
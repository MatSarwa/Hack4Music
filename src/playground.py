import cv2
import mediapipe as mp
import time
import math
import numpy as np
from datetime import datetime
import csv
import os
import pygame
import json


# Definicja instrumentow z pozycjami dopasowanymi do tla i nazwami plikow obrazow
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

INSTRUMENT_RADIUS = 40
HIGHLIGHT_RADIUS = 60
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"
CSV_FILE = "played_instruments.csv"

class PlaygroundMode:
    def __init__(self, control_mode):
        self.control_mode = control_mode
        self.played_instruments = []
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_duration_needed = 1.0
        self.hover_progress = 0.0
        self.last_touch_time = 0
        self.touch_cooldown = 0.5
        self.selected_instrument = -1  # Aktualnie wybrany instrument do edycji rozmiaru
        self.init_csv()
        self.load_instrument_settings()  # Wczytaj ustawienia przed ladowaniem obrazow
        self.load_images()
        self.load_background()

    def load_images(self):
        """Zaladuj obrazy instrumentow"""
        for instrument in INSTRUMENTS:
            try:
                # Wczytaj obraz z kanalem alfa (UNCHANGED zachowuje przezroczystośc)
                img = cv2.imread(instrument["image_file"], cv2.IMREAD_UNCHANGED)
                if img is not None:
                    # Skaluj obraz do odpowiedniego rozmiaru uzywajac indywidualnego rozmiaru
                    size = instrument["size"] * 2
                    img = cv2.resize(img, (size, size))
                    instrument["image"] = img
                    instrument["original_image"] = cv2.imread(instrument["image_file"], cv2.IMREAD_UNCHANGED)  # Zachowaj oryginalny obraz
                else:
                    instrument["image"] = None
                    instrument["original_image"] = None
                    print(f"Nie mozna zaladowac obrazu: {instrument['image_file']}")
            except Exception as e:
                instrument["image"] = None
                instrument["original_image"] = None
                print(f"Blad podczas ladowania obrazu {instrument['image_file']}: {e}")

    def load_background(self):
        """Zaladuj obraz tla"""
        try:
            self.background = cv2.imread("img/background.png")
            if self.background is None:
                print("Nie mozna zaladowac tla, uzywam domyślnego")
                self.background = None
        except:
            self.background = None

    def init_csv(self):
        """Inicjalizuje plik CSV z naglowkami, jeśli nie istnieje"""
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
        
        if "sound" in INSTRUMENTS[instrument_index]:
            INSTRUMENTS[instrument_index]["sound"].play()
            INSTRUMENTS[instrument_index]["sound"].set_volume(0.8)
        
        self.played_instruments.append({"timestamp": timestamp, "instrument": instrument_name})
        print(f"Zagrano: {instrument_name} o {timestamp}")
        self.save_to_csv(timestamp, instrument_name)
        
        if len(self.played_instruments) > 10:
            self.played_instruments.pop(0)

    def update_hover(self, x, y, frame_width, frame_height):
        """Aktualizuje stan hover dla trybu reki"""
        if self.control_mode != CONTROL_HAND:
            return
        
        current_time = time.time()
        hovered_instrument = -1
        # Skaluj pozycje instrumentow do aktualnych wymiarow
        original_bg_size = 1024
        scale_x = frame_width / original_bg_size
        scale_y = frame_height / original_bg_size
        
        for i, instrument in enumerate(INSTRUMENTS):
            scaled_pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
            dist = math.sqrt((x - scaled_pos[0])**2 + (y - scaled_pos[1])**2)
            if dist <= instrument["size"]:  # Uzyj indywidualnego rozmiaru
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
    
    def update_instrument_size(self, instrument_index, size_change):
        """Aktualizuje rozmiar instrumentu"""
        if 0 <= instrument_index < len(INSTRUMENTS):
            current_size = INSTRUMENTS[instrument_index]["size"]
            new_size = max(10, min(100, current_size + size_change))  # Ograniczenie 10-100 pikseli
            INSTRUMENTS[instrument_index]["size"] = new_size
            
            # Ponownie skaluj obraz jeśli istnieje
            if INSTRUMENTS[instrument_index]["original_image"] is not None:
                size = new_size * 2
                img = cv2.resize(INSTRUMENTS[instrument_index]["original_image"], (size, size))
                INSTRUMENTS[instrument_index]["image"] = img
            
            print(f"Rozmiar {INSTRUMENTS[instrument_index]['name']}: {new_size}")
    
    def save_instrument_settings(self):
        """Zapisuje aktualne ustawienia instrumentow do pliku JSON"""
        settings = {}
        for i, instrument in enumerate(INSTRUMENTS):
            settings[instrument["name"]] = {
                "size": instrument["size"],
                "pos": instrument["pos"]
            }
        
        try:
            with open("instrument_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            print("Ustawienia instrumentow zostaly zapisane do instrument_settings.json")
        except Exception as e:
            print(f"Blad podczas zapisywania ustawien: {e}")
    
    def load_instrument_settings(self):
        """Wczytuje ustawienia instrumentow z pliku JSON"""
        try:
            if os.path.exists("instrument_settings.json"):
                with open("instrument_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                
                for i, instrument in enumerate(INSTRUMENTS):
                    if instrument["name"] in settings:
                        saved_settings = settings[instrument["name"]]
                        if "size" in saved_settings:
                            instrument["size"] = saved_settings["size"]
                        if "pos" in saved_settings:
                            instrument["pos"] = tuple(saved_settings["pos"])
                
                # Ponownie zaladuj obrazy z nowymi rozmiarami
                self.load_images()
                print("Wczytano ustawienia instrumentow z instrument_settings.json")
        except Exception as e:
            print(f"Blad podczas wczytywania ustawien: {e}")

    def check_touch(self, x, y, frame_width, frame_height):
        """Sprawdza klikniecie mysza"""
        if self.control_mode != CONTROL_MOUSE:
            return
        
        current_time = time.time()
        if current_time - self.last_touch_time < self.touch_cooldown:
            return
        
        # Skaluj pozycje instrumentow do aktualnych wymiarow
        original_bg_size = 1024
        scale_x = frame_width / original_bg_size
        scale_y = frame_height / original_bg_size
        
        for i, instrument in enumerate(INSTRUMENTS):
            scaled_pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
            dist = math.sqrt((x - scaled_pos[0])**2 + (y - scaled_pos[1])**2)
            if dist <= instrument["size"]:  # Uzyj indywidualnego rozmiaru
                self.activate_instrument(i)
                self.last_touch_time = current_time
                break

    def is_point_in_game_area(self, x, y, frame_width, frame_height):
        """Sprawdza czy punkt znajduje sie w obszarze gry"""
        margin = 50
        return (margin <= x <= frame_width - margin and 
                margin <= y <= frame_height - margin)

    def draw_instrument(self, frame, instrument, index, is_hovered=False):
        """Rysuje instrument na ramce"""
        # Skaluj pozycje instrumentu do aktualnych wymiarow ramki
        frame_h, frame_w = frame.shape[:2]
        original_bg_size = 1024  # Oryginalny rozmiar tla
        scale_x = frame_w / original_bg_size
        scale_y = frame_h / original_bg_size
        
        pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
        instrument_radius = instrument["size"]  # Uzyj indywidualnego rozmiaru
        
        # Jeśli obraz jest dostepny, uzyj go
        if "image" in instrument and instrument["image"] is not None:
            img = instrument["image"]
            h, w = img.shape[:2]
            
            # Oblicz pozycje do wyrysowania (środek obrazu w pozycji instrumentu)
            x1 = pos[0] - w // 2
            y1 = pos[1] - h // 2
            x2 = x1 + w
            y2 = y1 + h
            
            # Upewnij sie, ze wspolrzedne mieszcza sie w ramce
            frame_h, frame_w = frame.shape[:2]
            if x1 >= 0 and y1 >= 0 and x2 <= frame_w and y2 <= frame_h:
                # Jeśli obraz ma kanal alfa, uzyj go do mieszania
                if img.shape[2] == 4:
                    # Rozdziel kanaly
                    bgr = img[:, :, :3]
                    alpha = img[:, :, 3] / 255.0
                    
                    # Jeśli instrument jest podświetlony, zwieksz jasnośc
                    if is_hovered or self.hover_instrument == index:
                        bgr = cv2.addWeighted(bgr, 1.2, bgr, 0, 30)
                    
                    # Mieszaj obraz z tlem uzywajac kanalu alfa
                    for c in range(3):
                        frame[y1:y2, x1:x2, c] = (
                            alpha * bgr[:, :, c] + 
                            (1 - alpha) * frame[y1:y2, x1:x2, c]
                        )
                else:
                    # Jeśli nie ma kanalu alfa, po prostu skopiuj obraz
                    if is_hovered or self.hover_instrument == index:
                        img_bright = cv2.addWeighted(img, 1.2, img, 0, 30)
                        frame[y1:y2, x1:x2] = img_bright
                    else:
                        frame[y1:y2, x1:x2] = img
            
            # Dodaj efekt podświetlenia dla hover
            if is_hovered or self.hover_instrument == index:
                # Rysuj świecaca obwodke
                cv2.circle(frame, pos, instrument_radius + 5, (255, 255, 100), 2)
                
                # Jeśli jest w trakcie hover, pokaz progress
                if self.control_mode == CONTROL_HAND and self.hover_instrument == index and self.hover_progress > 0:
                    angle_end = int(360 * self.hover_progress)
                    highlight_radius = instrument_radius + 20
                    cv2.ellipse(frame, pos, (highlight_radius, highlight_radius), 
                               -90, 0, angle_end, (0, 255, 0), 3)
                    
                    progress_text = f"{int(self.hover_progress * 100)}%"
                    text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                    text_pos = (pos[0] - text_size[0] // 2, pos[1] + instrument_radius + 35)
                    cv2.putText(frame, progress_text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 2)
            
            # Dodaj ramke dla wybranego instrumentu
            if self.selected_instrument == index:
                cv2.circle(frame, pos, instrument_radius + 8, (0, 255, 255), 3)
        else:
            # Fallback - rysuj kolorowe kolko jeśli obraz nie jest dostepny
            color = instrument["color"]
            if is_hovered or self.hover_instrument == index:
                cv2.circle(frame, pos, instrument_radius + 5, (255, 255, 100), 2)
                cv2.circle(frame, pos, instrument_radius, color, -1)
            else:
                cv2.circle(frame, pos, instrument_radius, color, -1)
                cv2.circle(frame, pos, instrument_radius, (255, 255, 255), 2)
            
            # Dodaj ramke dla wybranego instrumentu
            if self.selected_instrument == index:
                cv2.circle(frame, pos, instrument_radius + 8, (0, 255, 255), 3)
        
        # Rysuj nazwe instrumentu
        text = instrument["name"]
        if self.selected_instrument == index:
            text += f" (rozmiar: {instrument['size']})"
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        text_x = pos[0] - text_size[0] // 2
        text_y = pos[1] + instrument_radius + 20
        
        # Tlo dla tekstu z przezroczystościa
        overlay = frame.copy()
        cv2.rectangle(overlay, (text_x - 5, text_y - 15), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # Tekst
        text_color = (255, 255, 100) if (is_hovered or self.hover_instrument == index) else (255, 255, 255)
        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

def run_playground(control_mode):
    # Inicjalizacja MediaPipe (tylko dla trybu reki)
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
    cv2.namedWindow('Tryb Wlasna Melodia', cv2.WINDOW_NORMAL)

    # Zmienne dla myszy
    mouse_x, mouse_y = 0, 0
    mouse_clicked = False
    mouse_hover = -1

    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_x, mouse_y, mouse_clicked, mouse_hover
        mouse_x, mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_clicked = True
        
        # Sprawdz ktory instrument jest pod myszka
        mouse_hover = -1
        # Uzyj stalych wymiarow dla skalowania pozycji
        frame_w, frame_h = 800, 600  # Domyślne wymiary
        if playground.background is not None:
            bg_h, bg_w = playground.background.shape[:2]
            scale = min(800/bg_w, 600/bg_h)
            frame_w = int(bg_w * scale)
            frame_h = int(bg_h * scale)
        
        original_bg_size = 1024
        scale_x = frame_w / original_bg_size
        scale_y = frame_h / original_bg_size
        
        for i, instrument in enumerate(INSTRUMENTS):
            scaled_pos = (int(instrument["pos"][0] * scale_x), int(instrument["pos"][1] * scale_y))
            dist = math.sqrt((x - scaled_pos[0])**2 + (y - scaled_pos[1])**2)
            if dist <= instrument["size"]:  # Uzyj indywidualnego rozmiaru
                mouse_hover = i
                break

    if control_mode == CONTROL_MOUSE:
        cv2.setMouseCallback('Tryb Wlasna Melodia', mouse_callback)

    print("🎵 Tryb Wlasna Melodia 🎵")
    print(f"Graj dowolne melodie na instrumentach! Sekwencja zapisywana do {CSV_FILE}")
    if control_mode == CONTROL_HAND:
        print("Trzymaj palec wskazujacy prawej reki nad instrumentem przez 1 sekunde.")
    else:
        print("Uzyj myszy do klikania na instrumenty.")
    print("\nSterowanie rozmiarem instrumentow:")
    print("- Klawisze 1-7: wybierz instrument do edycji")
    print("- Klawisz +/=: zwieksz rozmiar wybranego instrumentu")
    print("- Klawisz -: zmniejsz rozmiar wybranego instrumentu")
    print("- Klawisz 0: odznacz wybor instrumentu")
    print("- Klawisz S: zapisz aktualne ustawienia do pliku")
    print("Naciśnij ESC aby zakonczyc.")

    while True:
        # Uzyj tylko tla - ukryj kamere calkowicie
        if playground.background is not None:
            # Uzyj oryginalnego rozmiaru tla lub skaluj do odpowiednich proporcji
            bg_h, bg_w = playground.background.shape[:2]
            # Skaluj tlo do rozmiaru okna zachowujac proporcje
            scale = min(800/bg_w, 600/bg_h)  # Maksymalne wymiary okna
            new_w = int(bg_w * scale)
            new_h = int(bg_h * scale)
            frame = cv2.resize(playground.background, (new_w, new_h))
            h, w, _ = frame.shape
        else:
            # Domyślne ciemne tlo z gradientem
            h, w = 600, 800
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            gradient = np.linspace(40, 80, h).astype(np.uint8)
            for i in range(h):
                frame[i, :] = [gradient[i], gradient[i] * 0.8, gradient[i] * 0.6]

        cursor_x, cursor_y = None, None
        if control_mode == CONTROL_HAND:
            # Pobierz obraz z kamery do analizy rak
            ret_cam, camera_frame = cap.read()
            if ret_cam:
                camera_frame = cv2.flip(camera_frame, 1)
                camera_frame = cv2.resize(camera_frame, (w, h))
                rgb = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
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
            playground.update_hover(cursor_x, cursor_y, w, h)
        elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None and cursor_y is not None:
            playground.check_touch(cursor_x, cursor_y, w, h)
            mouse_clicked = False
        elif control_mode == CONTROL_HAND and cursor_x is None:
            playground.reset_hover_state()

        # Rysuj instrumenty
        for i, instrument in enumerate(INSTRUMENTS):
            is_hovered = (control_mode == CONTROL_MOUSE and mouse_hover == i)
            playground.draw_instrument(frame, instrument, i, is_hovered)

        # Rysuj kursor
        if cursor_x is not None and cursor_y is not None:
            if control_mode == CONTROL_HAND:
                cv2.circle(frame, (cursor_x, cursor_y), 8, (0, 255, 0), -1)
                cv2.circle(frame, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
            else:
                cv2.circle(frame, (cursor_x, cursor_y), 6, (255, 0, 0), -1)
                cv2.circle(frame, (cursor_x, cursor_y), 10, (255, 255, 255), 2)

        # Rysuj informacje o trybie
        info_text = "Tryb Wlasna Melodia - graj swobodnie!"
        text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 5), (text_size[0] + 20, 40), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        cv2.putText(frame, info_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)

        control_text = f"Tryb: {'Reka (1s hover)' if control_mode == CONTROL_HAND else 'Mysz (klik)'}"
        cv2.rectangle(overlay, (w - 170, 5), (w - 10, 40), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        cv2.putText(frame, control_text, (w - 165, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Dodaj instrukcje sterowania
        instructions = [
        ]
        
        start_y = 50
        for i, instruction in enumerate(instructions):
            text_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            overlay = frame.copy()
            cv2.rectangle(overlay, (5, start_y + i * 20), (text_size[0] + 15, start_y + i * 20 + 18), (0, 0, 0), -1)
            frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
            cv2.putText(frame, instruction, (10, start_y + i * 20 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Wyświetl klatke
        cv2.imshow('Tryb Wlasna Melodia', frame)

        # Sprawdz wyjście i obsluz klawiature
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord('1'):  # Wybierz instrument 1
            playground.selected_instrument = 0
        elif key == ord('2'):  # Wybierz instrument 2
            playground.selected_instrument = 1
        elif key == ord('3'):  # Wybierz instrument 3
            playground.selected_instrument = 2
        elif key == ord('4'):  # Wybierz instrument 4
            playground.selected_instrument = 3
        elif key == ord('5'):  # Wybierz instrument 5
            playground.selected_instrument = 4
        elif key == ord('6'):  # Wybierz instrument 6
            playground.selected_instrument = 5
        elif key == ord('7'):  # Wybierz instrument 7
            playground.selected_instrument = 6
        elif key == ord('0'):  # Odznacz wybor
            playground.selected_instrument = -1
        elif key == ord('+') or key == ord('='):  # Zwieksz rozmiar
            if playground.selected_instrument >= 0:
                playground.update_instrument_size(playground.selected_instrument, 5)
        elif key == ord('-'):  # Zmniejsz rozmiar
            if playground.selected_instrument >= 0:
                playground.update_instrument_size(playground.selected_instrument, -5)
        elif key == ord('s') or key == ord('S'):  # Zapisz ustawienia
            playground.save_instrument_settings()
        
        if cv2.getWindowProperty('Tryb Wlasna Melodia', cv2.WND_PROP_VISIBLE) < 1:
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if hands:
        hands.close()
    print("Dziekuje za gre w trybie Wlasna Melodia! 🎵")
    print(f"Sekwencja zapisana w {CSV_FILE}")

if __name__ == "__main__":
    run_playground(CONTROL_MOUSE)

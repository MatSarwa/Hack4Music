import cv2
import mediapipe as mp
import threading
import time
import random
import math
import numpy as np
import pygame
from playground import run_playground  # Import the playground mode

# Definicja instrumentów z pozycjami
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

# Tryby sterowania
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"

# Stany gry
GAME_STATE_SHOWING = "showing_sequence"
GAME_STATE_WAITING = "waiting_for_input"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_SUCCESS = "sequence_success"

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
        self.touch_cooldown = 0.5  # 0.5 sekundy między dotknięciami
        self.control_mode = control_mode
        self.game_mode = game_mode
        self.sequence_completed_time = 0
        self.waiting_for_next_level = False
        
        # Nowe zmienne dla systemu hover w trybie ręki
        self.hover_instrument = -1  # Który instrument jest aktualnie "hovered"
        self.hover_start_time = 0   # Kiedy rozpoczął się hover
        self.hover_duration_needed = 1.0  # Czas potrzebny do aktywacji (1 sekunda)
        self.hover_progress = 0.0   # Postęp hover (0.0 - 1.0)
        
        # Rozpocznij pierwszą sekwencję
        #time.sleep(2)
        self.generate_new_sequence()

        
    def generate_new_sequence(self):
        """Generuje nową sekwencję na podstawie aktualnego poziomu"""
        self.sequence = []
        sequence_length = min(self.level + 1, 6)  # Maksymalnie 6 instrumentów w sekwencji
        
        for _ in range(sequence_length):
            self.sequence.append(random.randint(0, len(INSTRUMENTS) - 1))
        
        print(f"Nowa sekwencja (poziom {self.level}): {[INSTRUMENTS[i]['name'] for i in self.sequence]}")
        self.reset_for_new_sequence()
        
    def reset_for_new_sequence(self):
        """Resetuje stan dla nowej sekwencji"""
        self.current_sequence_index = 0
        self.player_sequence = []
        self.game_state = GAME_STATE_SHOWING
        self.sequence_display_index = 0
        self.highlight_instrument = -1
        self.highlight_start_time = time.time()
        # Reset hover state
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_progress = 0.0
        
    def update(self):
        """Aktualizuje stan gry"""
        current_time = time.time()
        
        if self.game_state == GAME_STATE_SHOWING:
            if self.sequence_display_index < len(self.sequence):
                instrument_index = self.sequence[self.sequence_display_index]
                instrument = INSTRUMENTS[instrument_index]
                
                # Zagraj dźwięk instrumentu
                instrument["sound"].play()
                duration = instrument["sound"].get_length()
                
                # Poczekaj na zakończenie odtwarzania
                time.sleep(duration+0.5)
                
                # Przejdź do następnego instrumentu
                self.sequence_display_index += 1
            else:
                # Koniec pokazywania sekwencji
                self.game_state = GAME_STATE_WAITING
                self.highlight_instrument = -1
                print("Twoja kolej! Powtórz sekwencję.")

                
        elif self.game_state == GAME_STATE_SUCCESS:
            # Czekamy aż gracz ukończy całą sekwencję przed przejściem do następnego poziomu
            if self.waiting_for_next_level and current_time - self.sequence_completed_time > 1.5:
                self.level += 1
                self.waiting_for_next_level = False
                self.generate_new_sequence()
        
        # Aktualizuj stan hover (tylko dla trybu ręki)
        if self.control_mode == CONTROL_HAND and self.game_state == GAME_STATE_WAITING:
            if self.hover_instrument >= 0:
                # Sprawdź postęp hover
                hover_elapsed = current_time - self.hover_start_time
                self.hover_progress = min(hover_elapsed / self.hover_duration_needed, 1.0)
                
                # Jeśli hover jest zakończony, aktywuj instrument
                if self.hover_progress >= 1.0:
                    self.activate_instrument(self.hover_instrument)
                    self.reset_hover_state()
            else:
                self.hover_progress = 0.0
    
    def reset_hover_state(self):
        """Resetuje stan hover"""
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_progress = 0.0
    
    def update_hover(self, x, y):
        """Aktualizuje stan hover na podstawie pozycji kursora (tylko dla trybu ręki)"""
        if self.control_mode != CONTROL_HAND or self.game_state != GAME_STATE_WAITING:
            return
        
        current_time = time.time()
        
        # Sprawdź czy kursor jest nad którymś instrumentem
        hovered_instrument = -1
        for i, instrument in enumerate(INSTRUMENTS):
            dist = math.sqrt((x - instrument["pos"][0])**2 + (y - instrument["pos"][1])**2)
            if dist <= INSTRUMENT_RADIUS:
                hovered_instrument = i
                break
        
        # Aktualizuj stan hover
        if hovered_instrument != self.hover_instrument:
            # Zmienił się instrument lub palec opuścił obszar
            if hovered_instrument >= 0:
                # Rozpocznij nowy hover
                self.hover_instrument = hovered_instrument
                self.hover_start_time = current_time
                self.hover_progress = 0.0
            else:
                # Palec opuścił wszystkie instrumenty
                self.reset_hover_state()
    
    def check_touch(self, x, y):
        """Sprawdza czy pozycja dotyka któregoś z instrumentów (tylko dla trybu myszy)"""
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
        """Aktywuje wybrany instrument"""
        self.player_sequence.append(instrument_index)
        expected_instrument = self.sequence[self.current_sequence_index]
        
        print(f"Aktywowano: {INSTRUMENTS[instrument_index]['name']}")
        instrument_index = instrument_index  # już masz przekazany do funkcji
        INSTRUMENTS[instrument_index]["sound"].play()
        INSTRUMENTS[instrument_index]["sound"].set_volume(0.8)  # 0.0 - 1.0


        
        if instrument_index == expected_instrument:
            print("✓ Dobrze!")
            self.current_sequence_index += 1
            
            # Sprawdź czy cała sekwencja została ukończona
            if self.current_sequence_index >= len(self.sequence):
                print(f"🎉 Poziom {self.level} ukończony!")
                self.game_state = GAME_STATE_SUCCESS
                self.sequence_completed_time = time.time()
                self.waiting_for_next_level = True

                time.sleep(2)
                
        else:
            print(f"✗ Błąd! Oczekiwano: {INSTRUMENTS[expected_instrument]['name']}")

            choice = show_game_over_screen()
            if choice == "retry":
                print("Gra rozpoczyna się od nowa...")
                self.level = 1
                self.generate_new_sequence()
            elif choice == "menu":
                print("Powrót do menu głównego...")
                cv2.destroyAllWindows()
                cap.release()
                # restart aplikacji od wyboru
                control_mode = choose_control_mode()
                game_mode = choose_game_mode()
                if game_mode == MODE_PLAYGROUND:
                    run_playground(control_mode)
                    exit()
                elif game_mode == MODE_DOUBLE:
                    print("Tryb dla dwóch graczy nie jest jeszcze zaimplementowany.")
                    exit()
                else:
                    # nowa gra
                    new_game = MusicalGame(control_mode)
                    return new_game  # zwróć nową grę, żeby zastąpić starą
            else:
                print("Gra zakończona.")
                cv2.destroyAllWindows()
                exit(0)


    
    def is_point_in_game_area(self, x, y, frame_width, frame_height):
        """Sprawdza czy punkt znajduje się w obszarze gry"""
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
        # sprawdzamy czy kliknięto w prostokąt przycisku
        if 50 < x < 250 and 80 < y < 140:
            selected_mode = CONTROL_HAND
        elif 50 < x < 250 and 180 < y < 240:
            selected_mode = CONTROL_MOUSE
# --- NOWY KOD ---

def mouse_callback_game_mode(event, x, y, flags, param):
    global game_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 < x < 250 and 80 < y < 140:
            game_mode = MODE_SINGLE
        elif 50 < x < 250 and 180 < y < 240:
            game_mode = MODE_DOUBLE
        elif 50 < x < 250 and 280 < y < 340:
            game_mode = MODE_PLAYGROUND

game_over_choice = None  # globalna zmienna: "retry" albo "quit"

def mouse_callback_game_over(event, x, y, flags, param):
    global game_over_choice
    if event == cv2.EVENT_LBUTTONDOWN:
        # Graj ponownie
        if 50 < x < 250 and 150 < y < 210:
            game_over_choice = "retry"
        # Menu główne
        elif 50 < x < 250 and 230 < y < 290:
            game_over_choice = "menu"

MODE_SINGLE = 1
MODE_DOUBLE = 2
MODE_PLAYGROUND = 3

def choose_game_mode():
    global game_mode
    game_mode = None

    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Wybierz tryb gry:", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # przycisk 1
    cv2.rectangle(img, (50, 80), (250, 140), (200, 200, 200), -1)
    cv2.putText(img, "1. Jeden gracz", (60, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # przycisk 2
    cv2.rectangle(img, (50, 180), (250, 240), (200, 200, 200), -1)
    cv2.putText(img, "2. Dwóch graczy", (60, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # przycisk 3
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

        if cv2.waitKey(20) & 0xFF == 27:  # ESC
            game_mode = None
            break

        if cv2.getWindowProperty("Wybór trybu gry", cv2.WND_PROP_VISIBLE) < 1:
            game_mode = None
            break

    cv2.destroyWindow("Wybór trybu gry")
    return game_mode

# Funkcja wyboru trybu sterowania
def choose_control_mode():
    global selected_mode
    # tworzymy tło
    img = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Wybierz tryb sterowania:", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # rysujemy dwa przyciski
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

        # sprawdzamy czy okno istnieje
        if cv2.getWindowProperty("Wybór trybu", cv2.WND_PROP_VISIBLE) < 1:
            selected_mode = None
            break

        if selected_mode is not None:
            break

        if cv2.waitKey(20) & 0xFF == 27:  # ESC
            selected_mode = None
            break
        if cv2.getWindowProperty("Wybór trybu", cv2.WND_PROP_VISIBLE) < 1:
            selected_mode = None
            break

    cv2.destroyWindow("Wybór trybu")
    return selected_mode

 

def show_game_over_screen():
    global game_over_choice
    game_over_choice = None

    img = np.ones((450, 400, 3), dtype=np.uint8) * 255

    # Nagłówek
    cv2.putText(img, "✗ Przegrales!", (60, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Przycisk Graj ponownie
    cv2.rectangle(img, (50, 150), (250, 210), (200, 200, 200), -1)
    cv2.putText(img, "Graj ponownie", (60, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Przycisk Menu główne
    cv2.rectangle(img, (50, 230), (250, 290), (200, 200, 200), -1)
    cv2.putText(img, "Menu glowne", (60, 270),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    cv2.namedWindow("Koniec gry")
    cv2.setMouseCallback("Koniec gry", mouse_callback_game_over)

    while True:
        cv2.imshow("Koniec gry", img)

        if game_over_choice is not None:
            break

        if cv2.waitKey(20) & 0xFF == 27:  # ESC
            game_over_choice = "quit"
            break

        if cv2.getWindowProperty("Koniec gry", cv2.WND_PROP_VISIBLE) < 1:
            game_over_choice = "quit"
            break

    cv2.destroyWindow("Koniec gry")
    return game_over_choice


# Wybór trybu sterowania
control_mode = choose_control_mode()
game_mode = choose_game_mode()

# Uruchom odpowiedni tryb gry
if game_mode == MODE_PLAYGROUND:
    run_playground(control_mode)
    exit()
elif game_mode == MODE_DOUBLE:
    print("Tryb dla dwóch graczy nie jest jeszcze zaimplementowany.")
    exit()

# Inicjalizacja MediaPipe (tylko gdy używamy trybu ręki)
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

# Ustawienie callback dla myszy
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

    # Odbij kamerę poziomo dla bardziej naturalnego doświadczenia
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    # Znajdź pozycję kursora (palec lub mysz)
    cursor_x, cursor_y = None, None
    
    if control_mode == CONTROL_HAND:
        # Konwertuj na RGB dla MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        # Znajdź pozycję palca wskazującego prawej ręki
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                if handedness.classification[0].label == 'Right':
                    # Punkt 8 to czubek palca wskazującego
                    finger_tip = hand_landmarks.landmark[8]
                    cursor_x = int(finger_tip.x * w)
                    cursor_y = int(finger_tip.y * h)
                    break
    
    elif control_mode == CONTROL_MOUSE:
        cursor_x, cursor_y = mouse_x, mouse_y
        
        # Sprawdź czy mysz jest w obszarze gry
        if not game.is_point_in_game_area(cursor_x, cursor_y, w, h):
            cursor_x, cursor_y = None, None
    
    # Aktualizuj stan gry
    game.update()
    if isinstance(game, MusicalGame) and hasattr(game, "new_game_pending"):
        game = game.new_game_pending
        del game.new_game_pending

    
    # Aktualizuj hover (dla trybu ręki) lub sprawdź kliknięcie (dla trybu myszy)
    if control_mode == CONTROL_HAND and cursor_x is not None and cursor_y is not None:
        game.update_hover(cursor_x, cursor_y)
    elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None and cursor_y is not None:
        game.check_touch(cursor_x, cursor_y)
        mouse_clicked = False  # Reset flagi kliknięcia
    elif control_mode == CONTROL_HAND and cursor_x is None:
        # Jeśli palec nie jest wykryty, resetuj hover
        game.reset_hover_state()
    
    # Rysuj tło
    cv2.rectangle(frame, (0, 0), (w, h), (20, 20, 20), -1)
    
    # Rysuj instrumenty
    for i, instrument in enumerate(INSTRUMENTS):
        pos = instrument["pos"]
        color = instrument["color"]
        
        # Sprawdź czy instrument powinien być podświetlony (sekwencja) lub ma hover
        is_sequence_highlight = (game.highlight_instrument == i)
        is_hover_highlight = (control_mode == CONTROL_HAND and game.hover_instrument == i)
        
        if is_sequence_highlight:
            # Rysuj podświetlenie sekwencji (białe)
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS, (255, 255, 255), 3)
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS - 5, color, -1)
        elif is_hover_highlight:
            # Rysuj postęp hover (zielony pierścień)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
            
            # Rysuj pierścień postępu
            if game.hover_progress > 0:
                angle_end = int(360 * game.hover_progress)
                # Używamy elipsy do rysowania łuku postępu
                overlay = frame.copy()
                cv2.ellipse(overlay, pos, (HIGHLIGHT_RADIUS, HIGHLIGHT_RADIUS), 
                           -90, 0, angle_end, (0, 255, 0), 4)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
                
                # Rysuj tekst z postępem
                progress_text = f"{int(game.hover_progress * 100)}%"
                text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                text_pos = (pos[0] - text_size[0] // 2, pos[1] + 5)
                cv2.putText(frame, progress_text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        else:
            # Rysuj normalny instrument
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
        
        # Rysuj nazwę instrumentu
        text_size = cv2.getTextSize(instrument["name"], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        text_x = pos[0] - text_size[0] // 2
        text_y = pos[1] + INSTRUMENT_RADIUS + 20
        
        # Tło dla tekstu
        cv2.rectangle(frame, (text_x - 5, text_y - 15), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
        cv2.putText(frame, instrument["name"], (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Rysuj pozycję kursora (palec lub mysz)
    if cursor_x is not None and cursor_y is not None:
        if control_mode == CONTROL_HAND:
            cv2.circle(frame, (cursor_x, cursor_y), 8, (0, 255, 0), -1)
            cv2.circle(frame, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
        else:  # CONTROL_MOUSE
            cv2.circle(frame, (cursor_x, cursor_y), 6, (255, 0, 0), -1)
            cv2.circle(frame, (cursor_x, cursor_y), 10, (255, 255, 255), 2)
    
    # Rysuj granice obszaru gry (dla trybu myszy)
    if control_mode == CONTROL_MOUSE:
        cv2.rectangle(frame, (50, 50), (w-50, h-50), (100, 100, 100), 2)
    
    # Rysuj informacje o stanie gry
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
    
    # Tło dla informacji
    text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    cv2.rectangle(frame, (10, 5), (text_size[0] + 20, 40), (0, 0, 0), -1)
    cv2.putText(frame, info_text, (15, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Rysuj poziom i tryb sterowania
    level_text = f"Poziom: {game.level}"
    control_text = f"Tryb: {'Ręka (1s hover)' if control_mode == CONTROL_HAND else 'Mysz (klik)'}"
    
    cv2.rectangle(frame, (w - 170, 5), (w - 10, 70), (0, 0, 0), -1)
    cv2.putText(frame, level_text, (w - 165, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, control_text, (w - 165, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Wyświetl klatkę
    cv2.imshow('Edukacyjna Gra Muzyczna', frame)
    
    # Sprawdź wyjście (ESC)
    if cv2.waitKey(1) & 0xFF == 27:
        break
    if cv2.getWindowProperty("Edukacyjna Gra Muzyczna", cv2.WND_PROP_VISIBLE) < 1:
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("Dziękuję za grę! 🎵")
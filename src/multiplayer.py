import cv2
import mediapipe as mp
import time
import math
import numpy as np
import pygame

# Definicja instrumentów z pozycjami (powtórzone z main.py dla niezależności)
INSTRUMENTS = [
    {"name": "Pianino", "pos": (150, 100), "color": (255, 100, 100)},
    {"name": "Harmonijka", "pos": (400, 150), "color": (100, 255, 100)},
    {"name": "Organy", "pos": (550, 120), "color": (100, 100, 255)},
    {"name": "Gitara", "pos": (200, 300), "color": (255, 255, 100)},
    {"name": "Skrzypce", "pos": (500, 350), "color": (255, 100, 255)},
    {"name": "Flet", "pos": (350, 250), "color": (100, 255, 255)},
]

pygame.mixer.init()

# Załaduj dźwięki instrumentów
for instrument in INSTRUMENTS:
    instrument_name = instrument["name"].lower()
    try:
        instrument["sound"] = pygame.mixer.Sound(f"sound/{instrument_name}.mp3")
    except:
        print(f"Nie można załadować dźwięku dla {instrument_name}")

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

# Nowe stany dla gry wieloosobowej
GAME_STATE_WAITING_FOR_CREATOR = "waiting_for_creator"
GAME_STATE_SHOWING_SCORES = "showing_scores"
GAME_STATE_NEXT_CREATOR = "next_creator"

class MultiplayerGame:
    def __init__(self, players, control_mode=CONTROL_HAND, starting_level=2):
        self.players = players  # Lista imion graczy
        self.scores = {player: 0 for player in players}  # Punkty graczy
        self.current_creator_idx = 0  # Indeks gracza tworzącego sekwencję
        self.current_level = starting_level  # Poziom trudności
        self.created_sequence = []  # Sekwencja stworzona przez gracza
        self.current_guesser_idx = 0  # Indeks gracza odgadującego
        self.round_scores = {}  # Punkty za obecną rundę
        self.control_mode = control_mode
        
        # Stany gry
        self.game_state = GAME_STATE_WAITING_FOR_CREATOR
        self.sequence = []
        self.current_sequence_index = 0
        self.player_sequence = []
        self.highlight_instrument = -1
        self.highlight_start_time = 0
        self.sequence_display_index = 0
        self.last_touch_time = 0
        self.touch_cooldown = 0.5
        
        # System hover dla trybu ręki
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_duration_needed = 1.0
        self.hover_progress = 0.0
        
        # Liczniki rund
        self.completed_rounds_in_level = 0  # Ile graczy już stworzyło sekwencję na tym poziomie
        self.total_rounds_per_level = len(players)  # Każdy gracz tworzy sekwencję raz na poziom
        
        self.show_message_until = 0  # Do wyświetlania komunikatów czasowych
        self.current_message = ""
        
        print(f"🎵 Gra wieloosobowa rozpoczęta!")
        print(f"Gracze: {', '.join(self.players)}")
        print(f"Poziom trudności: {self.current_level} instrumentów")
        self.show_timed_message(f"Sekwencję wymyśla: {self.get_current_creator()}", 2.0)
        
    def get_current_creator(self):
        return self.players[self.current_creator_idx]
    
    def get_current_guesser(self):
        if self.current_guesser_idx < len(self.players):
            return self.players[self.current_guesser_idx]
        return None
    
    def show_timed_message(self, message, duration):
        self.current_message = message
        self.show_message_until = time.time() + duration
    
    def update(self):
        current_time = time.time()
        
        # Ukryj wiadomość po czasie
        if current_time > self.show_message_until:
            self.current_message = ""
        
        if self.game_state == GAME_STATE_WAITING_FOR_CREATOR:
            # Czekamy aż twórca sekwencji utworzy melodię
            pass
            
        elif self.game_state == GAME_STATE_SHOWING:
            # Pokazywanie sekwencji graczom odgadującym
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
                current_guesser = self.get_current_guesser()
                if current_guesser:
                    self.show_timed_message(f"Kolej {current_guesser}!", 1.5)
                    
        elif self.game_state == GAME_STATE_SUCCESS:
            # Gracz odgadł sekwencję - przejdź do następnego gracza po krótkiej przerwie
            if not hasattr(self, 'success_start_time'):
                self.success_start_time = current_time
            elif current_time - self.success_start_time > 1.0:  # 1 sekunda przerwy
                delattr(self, 'success_start_time')
                self.next_guesser()
            
        elif self.game_state == GAME_STATE_GAME_OVER:
            # Gracz się pomylił - przejdź do następnego gracza po krótkiej przerwie
            if not hasattr(self, 'game_over_start_time'):
                self.game_over_start_time = current_time
            elif current_time - self.game_over_start_time > 1.5:  # 1.5 sekundy przerwy
                delattr(self, 'game_over_start_time')
                self.next_guesser()
            
        elif self.game_state == GAME_STATE_SHOWING_SCORES:
            # Wyświetlanie wyników po rundzie
            pass
        
        # Aktualizuj hover dla trybu ręki
        if self.control_mode == CONTROL_HAND and self.game_state in [GAME_STATE_WAITING, GAME_STATE_WAITING_FOR_CREATOR]:
            if self.hover_instrument >= 0:
                hover_elapsed = current_time - self.hover_start_time
                self.hover_progress = min(hover_elapsed / self.hover_duration_needed, 1.0)
                
                if self.hover_progress >= 1.0:
                    self.activate_instrument(self.hover_instrument)
                    self.reset_hover_state()
            else:
                self.hover_progress = 0.0
    
    def reset_hover_state(self):
        self.hover_instrument = -1
        self.hover_start_time = 0
        self.hover_progress = 0.0
    
    def update_hover(self, x, y):
        if self.control_mode != CONTROL_HAND:
            return
        if self.game_state not in [GAME_STATE_WAITING, GAME_STATE_WAITING_FOR_CREATOR]:
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
    
    def check_touch(self, x, y):
        if self.control_mode != CONTROL_MOUSE:
            return
        if self.game_state not in [GAME_STATE_WAITING, GAME_STATE_WAITING_FOR_CREATOR]:
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
        current_time = time.time()
        
        # Odtwórz dźwięk instrumentu
        if "sound" in INSTRUMENTS[instrument_index]:
            INSTRUMENTS[instrument_index]["sound"].play()
            INSTRUMENTS[instrument_index]["sound"].set_volume(0.8)
        
        if self.game_state == GAME_STATE_WAITING_FOR_CREATOR:
            # Twórca dodaje instrument do sekwencji
            self.created_sequence.append(instrument_index)
            print(f"{self.get_current_creator()} dodał: {INSTRUMENTS[instrument_index]['name']}")
            
            # Sprawdź czy sekwencja jest kompletna
            if len(self.created_sequence) >= self.current_level:
                self.sequence = self.created_sequence.copy()
                self.created_sequence = []
                self.start_guessing_phase()
                
        elif self.game_state == GAME_STATE_WAITING:
            # Gracz odgadujący dodaje instrument
            self.player_sequence.append(instrument_index)
            expected_instrument = self.sequence[self.current_sequence_index]
            
            current_guesser = self.get_current_guesser()
            print(f"{current_guesser} wybrał: {INSTRUMENTS[instrument_index]['name']}")
            
            if instrument_index == expected_instrument:
                print("✓ Dobrze!")
                self.current_sequence_index += 1
                
                # Sprawdź czy gracz ukończył CAŁĄ sekwencję
                if self.current_sequence_index >= len(self.sequence):
                    # Gracz odgadł całą sekwencję - przyznaj punkt
                    self.scores[current_guesser] += 1
                    self.show_timed_message(f"🎉 {current_guesser} odgadł całą sekwencję!", 2.0)
                    print(f"🎉 {current_guesser} odgadł całą sekwencję!")
                    self.game_state = GAME_STATE_SUCCESS
                else:
                    # Gracz odgadł kolejny instrument, ale sekwencja jeszcze nie skończona
                    remaining = len(self.sequence) - self.current_sequence_index
                    self.show_timed_message(f"✓ Dobrze! Pozostało: {remaining}", 1.0)
            else:
                # Błędna odpowiedź - twórca dostaje punkt za błąd gracza
                creator = self.get_current_creator()
                if creator not in self.round_scores:
                    self.round_scores[creator] = 0
                self.round_scores[creator] += 1
                
                expected_name = INSTRUMENTS[expected_instrument]['name']
                print(f"✗ {current_guesser} się pomylił! Oczekiwano: {expected_name}")
                self.show_timed_message(f"✗ {current_guesser} się pomylił na {self.current_sequence_index + 1}. instrumencie!", 2.0)
                self.game_state = GAME_STATE_GAME_OVER
    
    def start_guessing_phase(self):
        """Rozpocznij fazę odgadywania - pokaż sekwencję"""
        self.current_guesser_idx = 0
        # Pomiń twórcę sekwencji
        if self.current_guesser_idx == self.current_creator_idx:
            self.current_guesser_idx += 1
            
        self.game_state = GAME_STATE_SHOWING
        self.sequence_display_index = 0
        self.highlight_start_time = time.time()
        self.show_timed_message("Obserwuj sekwencję...", 1.0)
        
        creator = self.get_current_creator()
        sequence_names = [INSTRUMENTS[i]['name'] for i in self.sequence]
        print(f"Sekwencja {creator}: {' -> '.join(sequence_names)}")
    
    def next_guesser(self):
        """Przejdź do następnego gracza odgadującego"""
        self.current_guesser_idx += 1
        
        # Pomiń twórcę sekwencji
        if self.current_guesser_idx == self.current_creator_idx:
            self.current_guesser_idx += 1
            
        if self.current_guesser_idx >= len(self.players):
            # Wszyscy gracze już próbowali - koniec rundy
            self.end_round()
        else:
            # Następny gracz - zresetuj stan gry
            self.reset_for_next_guesser()
    
    def reset_for_next_guesser(self):
        """Resetuj stan dla następnego gracza odgadującego"""
        self.player_sequence = []
        self.current_sequence_index = 0
        self.game_state = GAME_STATE_SHOWING
        self.sequence_display_index = 0
        self.highlight_start_time = time.time()
        self.reset_hover_state()
        
        current_guesser = self.get_current_guesser()
        self.show_timed_message(f"Następny: {current_guesser}", 1.0)
    
    def end_round(self):
        """Zakończ rundę i przejdź do następnego twórcy lub poziomu"""
        # Dodaj punkty twórcy za błędy innych graczy
        creator = self.get_current_creator()
        if creator in self.round_scores:
            self.scores[creator] += self.round_scores[creator]
            print(f"{creator} zdobył {self.round_scores[creator]} punkt(ów) za błędy przeciwników")
        
        self.round_scores = {}
        self.completed_rounds_in_level += 1
        
        if self.completed_rounds_in_level >= self.total_rounds_per_level:
            # Wszyscy gracze stworzyli sekwencję na tym poziomie
            self.next_level()
        else:
            # Następny gracz tworzy sekwencję
            self.next_creator()
    
    def next_creator(self):
        """Przejdź do następnego twórcy sekwencji"""
        self.current_creator_idx = (self.current_creator_idx + 1) % len(self.players)
        self.game_state = GAME_STATE_WAITING_FOR_CREATOR
        self.created_sequence = []
        self.reset_hover_state()
        
        creator = self.get_current_creator()
        self.show_timed_message(f"Sekwencję wymyśla: {creator}", 2.0)
        print(f"Kolej {creator} na wymyślenie sekwencji ({self.current_level} instrumentów)")
    
    def next_level(self):
        """Przejdź do następnego poziomu"""
        self.current_level += 1
        self.completed_rounds_in_level = 0
        self.current_creator_idx = 0  # Zacznij od pierwszego gracza
        
        self.show_timed_message(f"🎉 Poziom {self.current_level}!", 3.0)
        print(f"🎉 Nowy poziom! Teraz {self.current_level} instrumentów")
        self.print_scores()
        
        # Krótka przerwa przed następnym poziomem
        time.sleep(1.0)
        self.next_creator()
    
    def print_scores(self):
        """Wyświetl aktualny stan punktów"""
        print("\n📊 Aktualny stan punktów:")
        sorted_players = sorted(self.players, key=lambda p: self.scores[p], reverse=True)
        for i, player in enumerate(sorted_players, 1):
            print(f"{i}. {player}: {self.scores[player]} punktów")
        print()
    
    def is_point_in_game_area(self, x, y, frame_width, frame_height):
        margin = 50
        return (margin <= x <= frame_width - margin and 
                margin <= y <= frame_height - margin)

def get_player_input(prompt, window_name):
    """Funkcja do wprowadzania tekstu przez użytkownika"""
    text = ""
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    
    while True:
        # Wyczyść obraz
        img.fill(255)
        
        # Rysuj prompt
        cv2.putText(img, prompt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Rysuj aktualny tekst
        cv2.putText(img, f"Tekst: {text}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Instrukcje
        cv2.putText(img, "Wpisz tekst i nacisnij ENTER", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "ESC - anuluj", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        cv2.imshow(window_name, img)
        
        key = cv2.waitKey(0) & 0xFF
        
        if key == 27:  # ESC
            cv2.destroyWindow(window_name)
            return None
        elif key == 13 or key == 10:  # ENTER
            cv2.destroyWindow(window_name)
            return text if text else None
        elif key == 8:  # BACKSPACE
            if text:
                text = text[:-1]
        elif 32 <= key <= 126:  # Znaki drukowalne
            if len(text) < 20:  # Limit długości
                text += chr(key)

def setup_multiplayer_game():
    """Konfiguracja gry wieloosobowej"""
    # Pobierz liczbę graczy
    num_players_str = get_player_input("Ile graczy? (2-6):", "Liczba graczy")
    if not num_players_str:
        return None, None
    
    try:
        num_players = int(num_players_str)
        if num_players < 2 or num_players > 6:
            print("Liczba graczy musi być między 2 a 6!")
            return None, None
    except ValueError:
        print("Nieprawidłowa liczba!")
        return None, None
    
    # Pobierz imiona graczy
    players = []
    for i in range(num_players):
        name = get_player_input(f"Imie gracza {i+1}:", f"Gracz {i+1}")
        if not name:
            return None, None
        players.append(name)
    
    # Pobierz poziom trudności
    level_str = get_player_input("Poziom trudnosci (2-6 instrumentow):", "Poziom trudnosci")
    if not level_str:
        return None, None
    
    try:
        starting_level = int(level_str)
        if starting_level < 2 or starting_level > 6:
            starting_level = 2
    except ValueError:
        starting_level = 2
    
    return players, starting_level

def draw_multiplayer_info(frame, game, control_mode):
    """Rysuj informacje dla trybu wieloosobowego"""
    h, w, _ = frame.shape
    
    # Główna informacja
    info_y = 30
    color = (100, 255, 255)
    
    if game.game_state == GAME_STATE_WAITING_FOR_CREATOR:
        creator = game.get_current_creator()
        remaining = game.current_level - len(game.created_sequence)
        info_text = f"{creator} tworzy sekwencje ({remaining} instrumentow pozostalo)"
        
        if control_mode == CONTROL_HAND and game.hover_instrument >= 0:
            info_text += f" | Hover: {int(game.hover_progress * 100)}%"
        color = (255, 255, 100)
        
    elif game.game_state == GAME_STATE_SHOWING:
        info_text = f"Obserwuj sekwencje... ({game.sequence_display_index + 1}/{len(game.sequence)})"
        color = (100, 255, 255)
        
    elif game.game_state == GAME_STATE_WAITING:
        guesser = game.get_current_guesser()
        progress = len(game.player_sequence)
        total = len(game.sequence)
        info_text = f"Kolej {guesser}! Postep: {progress}/{total}"
        
        if control_mode == CONTROL_HAND and game.hover_instrument >= 0:
            info_text += f" | Hover: {int(game.hover_progress * 100)}%"
        color = (100, 255, 100)
        
    else:
        info_text = "Gra wieloosobowa"
        color = (255, 255, 255)
    
    # Wiadomości czasowe
    if game.current_message:
        info_text = game.current_message
        color = (255, 255, 100)
    
    text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cv2.rectangle(frame, (10, 5), (text_size[0] + 20, 40), (0, 0, 0), -1)
    cv2.putText(frame, info_text, (15, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Informacje o rundzie i poziomie
    round_info = f"Poziom: {game.current_level} | Runda: {game.completed_rounds_in_level + 1}/{game.total_rounds_per_level}"
    control_text = f"Tryb: {'Reka' if control_mode == CONTROL_HAND else 'Mysz'}"
    
    cv2.rectangle(frame, (w - 200, 5), (w - 10, 70), (0, 0, 0), -1)
    cv2.putText(frame, round_info, (w - 195, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(frame, control_text, (w - 195, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Wyniki graczy
    scores_y = h - 100
    cv2.rectangle(frame, (10, scores_y - 25), (w - 10, h - 10), (0, 0, 0), -1)
    cv2.putText(frame, "Wyniki:", (15, scores_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    sorted_players = sorted(game.players, key=lambda p: game.scores[p], reverse=True)
    x_offset = 100
    for i, player in enumerate(sorted_players):
        score_text = f"{player}: {game.scores[player]}"
        
        # Podświetl aktualnego twórcę lub gracza
        if player == game.get_current_creator():
            color = (100, 255, 255)  # Twórca - cyan
        elif player == game.get_current_guesser():
            color = (100, 255, 100)  # Aktualny gracz - zielony
        else:
            color = (200, 200, 200)  # Pozostali - szary
            
        cv2.putText(frame, score_text, (x_offset, scores_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
        x_offset += len(score_text) * 10 + 20

def draw_game_interface(frame, game, cursor_x, cursor_y, control_mode):
    """Rysuj interfejs gry"""
    h, w, _ = frame.shape
    
    # Rysuj tło
    cv2.rectangle(frame, (0, 0), (w, h), (20, 20, 20), -1)
    
    # Rysuj instrumenty
    for i, instrument in enumerate(INSTRUMENTS):
        pos = instrument["pos"]
        color = instrument["color"]
        
        # Sprawdź podświetlenia
        is_sequence_highlight = (game.highlight_instrument == i)
        is_hover_highlight = (control_mode == CONTROL_HAND and hasattr(game, 'hover_instrument') and game.hover_instrument == i)
        
        if is_sequence_highlight:
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS, (255, 255, 255), 3)
            cv2.circle(frame, pos, HIGHLIGHT_RADIUS - 5, color, -1)
        elif is_hover_highlight:
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, color, -1)
            cv2.circle(frame, pos, INSTRUMENT_RADIUS, (255, 255, 255), 2)
            
            if hasattr(game, 'hover_progress') and game.hover_progress > 0:
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
        
        # Nazwa instrumentu
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
    
    # Granice dla myszy
    if control_mode == CONTROL_MOUSE:
        cv2.rectangle(frame, (50, 50), (w-50, h-50), (100, 100, 100), 2)
    
    return frame

def run_multiplayer(control_mode):
    """Główna funkcja uruchamiająca tryb multiplayer"""
    # Konfiguracja gry
    players, starting_level = setup_multiplayer_game()
    if players is None:
        print("Anulowano konfigurację gry.")
        return "menu"
    
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
    game = MultiplayerGame(players, control_mode, starting_level)
    cap = cv2.VideoCapture(0)
    cv2.namedWindow('Edukacyjna Gra Muzyczna - Multiplayer', cv2.WINDOW_NORMAL)
    
    # Zmienne dla myszy
    mouse_x, mouse_y = 0, 0
    mouse_clicked = False
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_x, mouse_y, mouse_clicked
        mouse_x, mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_clicked = True
    
    if control_mode == CONTROL_MOUSE:
        cv2.setMouseCallback('Edukacyjna Gra Muzyczna - Multiplayer', mouse_callback)
    
    print("🎵 Edukacyjna Gra Muzyczna - Tryb Multiplayer 🎵")
    print("Tryb wieloosobowy aktywny!")
    print("Obserwuj sekwencję i powtarzaj CAŁĄ SEKWENCJĘ aby zdobyć punkty!")
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
        
        # Znajdź pozycję kursora
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
        
        # Aktualizuj grę
        game.update()
        
        # Obsłuż interakcje
        if control_mode == CONTROL_HAND and cursor_x is not None and cursor_y is not None:
            game.update_hover(cursor_x, cursor_y)
        elif control_mode == CONTROL_MOUSE and mouse_clicked and cursor_x is not None and cursor_y is not None:
            game.check_touch(cursor_x, cursor_y)
            mouse_clicked = False
        elif control_mode == CONTROL_HAND and cursor_x is None:
            game.reset_hover_state()
        
        # Rysuj interfejs
        frame = draw_game_interface(frame, game, cursor_x, cursor_y, control_mode)
        
        # Rysuj informacje multiplayer
        draw_multiplayer_info(frame, game, control_mode)
        
        # Wyświetl
        cv2.imshow('Edukacyjna Gra Muzyczna - Multiplayer', frame)
        
        # Sprawdź wyjście
        if cv2.waitKey(1) & 0xFF == 27:
            break
        if cv2.getWindowProperty("Edukacyjna Gra Muzyczna - Multiplayer", cv2.WND_PROP_VISIBLE) < 1:
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if hands:
        hands.close()
    
    # Wyświetl finalne wyniki
    print("\n🏆 FINALNE WYNIKI:")
    game.print_scores()
    print("Dziękuję za grę w trybie multiplayer! 🎵")
    return "menu"

if __name__ == "__main__":
    # Placeholder: Tryb powinien być wybrany w main.py
    run_multiplayer(CONTROL_MOUSE)
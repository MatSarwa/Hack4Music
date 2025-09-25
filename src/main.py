import cv2
import numpy as np
from playground import run_playground
from challenge import run_challenge
from multiplayer import run_multiplayer

# Tryby sterowania
CONTROL_HAND = "hand"
CONTROL_MOUSE = "mouse"

# Tryby gry
MODE_SINGLE = 1
MODE_DOUBLE = 2
MODE_PLAYGROUND = 3

selected_mode = None
game_mode = None

def mouse_callback_control(event, x, y, flags, param):
    global selected_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        # sprawdzamy czy kliknięto w prostokąt przycisku
        if 50 < x < 250 and 80 < y < 140:
            selected_mode = CONTROL_HAND
        elif 50 < x < 250 and 180 < y < 240:
            selected_mode = CONTROL_MOUSE

def mouse_callback_game_mode(event, x, y, flags, param):
    global game_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 < x < 250 and 80 < y < 140:
            game_mode = MODE_SINGLE
        elif 50 < x < 250 and 180 < y < 240:
            game_mode = MODE_DOUBLE
        elif 50 < x < 250 and 280 < y < 340:
            game_mode = MODE_PLAYGROUND

def choose_control_mode():
    """Funkcja wyboru trybu sterowania"""
    global selected_mode
    selected_mode = None
    
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
    cv2.setMouseCallback("Wybór trybu", mouse_callback_control)

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

    cv2.destroyWindow("Wybór trybu")
    return selected_mode

def choose_game_mode():
    """Funkcja wyboru trybu gry"""
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
    cv2.putText(img, "2. Dwoch graczy", (60, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # przycisk 3
    cv2.rectangle(img, (50, 280), (250, 340), (200, 200, 200), -1)
    cv2.putText(img, "3. Wlasna melodia", (60, 320),
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

    cv2.destroyWindow("Wybór trybu gry")
    return game_mode

def main():
    """Główna funkcja aplikacji"""
    while True:
        # Wybór trybu sterowania
        control_mode = choose_control_mode()
        if control_mode is None:
            print("Anulowano wybór trybu sterowania.")
            break
        
        # Wybór trybu gry
        game_mode = choose_game_mode()
        if game_mode is None:
            print("Anulowano wybór trybu gry.")
            break
        
        # Uruchom odpowiedni tryb gry
        if game_mode == MODE_PLAYGROUND:
            print("Uruchamianie trybu własnej melodii...")
            run_playground(control_mode)
            break
        elif game_mode == MODE_DOUBLE:
            print("Uruchamianie trybu multiplayer...")
            result = run_multiplayer(control_mode)
            if result == "menu":
                continue  # Powróć do menu
            else:
                break  # Wyjdź z aplikacji
        elif game_mode == MODE_SINGLE:
            print("Uruchamianie trybu wyzwania dla jednego gracza...")
            result = run_challenge(control_mode)
            if result == "menu":
                continue  # Powróć do menu
            else:
                break  # Wyjdź z aplikacji
        else:
            print("Nieznany tryb gry.")
            break

if __name__ == "__main__":
    print("🎵 Edukacyjna Gra Muzyczna 🎵")
    print("Witaj w grze muzycznej!")
    main()
    print("Dziękuję za grę! 🎵")
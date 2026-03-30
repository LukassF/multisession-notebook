import streamlit as st
import requests
import json
import os
import time
from typing import Optional, Dict, Any

try:
    from streamlit_autorefresh import rerun_if_updated
except ImportError:
    rerun_if_updated = None

# Konfiguracja
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
HISTORY_DIR = os.path.dirname(os.path.abspath(__file__))


def get_history_filename(email: str) -> str:
    """Wygeneruj bezpieczną nazwę pliku historii dla użytkownika"""
    if not email:
        return None
    safe_email = email.lower().replace("@", "_").replace(".", "_")
    return f"history_{safe_email}.json"


def get_history_filepath(email: str) -> str:
    """Pobierz ścieżkę do pliku historii"""
    filename = get_history_filename(email)
    if not filename:
        return None
    return os.path.join(HISTORY_DIR, filename)


def load_notebook_history(email: str) -> Dict[str, str]:
    """Załaduj historię notatników z pliku"""
    if not email:
        return {}

    filepath = get_history_filepath(email)
    if not filepath:
        return {}

    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:  # Plik pusty
                    return {}
                data = json.loads(content)
                return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        # Plik uszkodzony - zwróć puste
        return {}
    except Exception as e:
        # Inne błędy - zwróć puste
        print(f"Błąd ładowania historii: {e}")
        return {}

    return {}


def save_notebook_history(email: str, history: Dict[str, str]):
    """Zapisz historię notatników do pliku"""
    if not email or not isinstance(history, dict):
        return

    filepath = get_history_filepath(email)
    if not filepath:
        return

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Nie wyrzucaj błędu - aplikacja powinna dalej działać
        print(f"Błąd zapisywania historii: {e}")


# Inicjalizacja session state
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "notebook_history" not in st.session_state:
    st.session_state.notebook_history = {}  # {notebook_id: notebook_name}
if "current_view" not in st.session_state:
    st.session_state.current_view = "dashboard"  # "dashboard" lub "editor"
if "selected_notebook_id" not in st.session_state:
    st.session_state.selected_notebook_id = None
if "notebook_content" not in st.session_state:
    st.session_state.notebook_content = ""
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "last_loaded_notebook_id" not in st.session_state:
    st.session_state.last_loaded_notebook_id = None


def make_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, require_auth: bool = True) -> tuple[Optional[Dict], Optional[str]]:
    """
    Wykonaj zapytanie HTTP do backendu.
    Zwraca tuple: (response_data, error_message)
    """
    url = f"{BACKEND_URL}{endpoint}"
    headers = {}

    if require_auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return None, f"Nieznana metoda HTTP: {method}"

        if response.status_code == 401:
            st.session_state.access_token = None
            return None, "Sesja wygasła. Zaloguj się ponownie."

        if response.status_code == 404:
            return None, "Zasób nie znaleziony (404)"

        if response.status_code >= 400:
            try:
                error_detail = response.json().get("detail", response.text)
            except:
                error_detail = response.text
            return None, f"Błąd {response.status_code}: {error_detail}"

        return response.json(), None

    except requests.exceptions.ConnectionError:
        return None, "Nie można połączyć się z backendem. Sprawdź czy serwer działa na http://localhost:8000"
    except Exception as e:
        return None, f"Błąd: {str(e)}"


def sidebar_auth():
    """Obsługa logowania i rejestracji w sidebar"""
    st.sidebar.title("🔐 Autoryzacja")

    if st.session_state.access_token:
        st.sidebar.success(f"✅ Zalogowany: {st.session_state.user_email}")
        if st.sidebar.button("Wyloguj"):
            st.session_state.access_token = None
            st.session_state.user_email = None
            st.session_state.selected_notebook_id = None
            st.session_state.current_view = "dashboard"
            st.session_state.notebook_history = {}
            st.rerun()
        return

    auth_tab = st.sidebar.radio("Wybierz opcję", ["Logowanie", "Rejestracja"])

    if auth_tab == "Logowanie":
        st.sidebar.subheader("Logowanie")
        login_email = st.sidebar.text_input("Email", key="login_email")
        login_password = st.sidebar.text_input("Hasło", type="password", key="login_password")

        if st.sidebar.button("Zaloguj się"):
            if not login_email or not login_password:
                st.sidebar.error("Uzupełnij wszystkie pola")
            else:
                data = {"email": login_email, "password": login_password}
                response, error = make_request("POST", "/auth/login", data, require_auth=False)

                if error:
                    st.sidebar.error(error)
                else:
                    st.session_state.access_token = response.get("data", {}).get("access_token")
                    st.session_state.user_email = login_email
                    # Załaduj historię
                    st.session_state.notebook_history = load_notebook_history(login_email)
                    st.sidebar.success("Zalogowano pomyślnie!")
                    st.rerun()

    else:  # Rejestracja
        st.sidebar.subheader("Rejestracja")
        reg_firstname = st.sidebar.text_input("Imię", key="reg_firstname")
        reg_lastname = st.sidebar.text_input("Nazwisko", key="reg_lastname")
        reg_email = st.sidebar.text_input("Email", key="reg_email")
        reg_password = st.sidebar.text_input("Hasło", type="password", key="reg_password")

        if st.sidebar.button("Zarejestruj się"):
            if not all([reg_firstname, reg_lastname, reg_email, reg_password]):
                st.sidebar.error("Uzupełnij wszystkie pola")
            else:
                data = {
                    "firstname": reg_firstname,
                    "lastname": reg_lastname,
                    "email": reg_email,
                    "password": reg_password
                }
                response, error = make_request("POST", "/auth/signup", data, require_auth=False)

                if error:
                    st.sidebar.error(error)
                else:
                    st.session_state.access_token = response.get("access_token")
                    st.session_state.user_email = reg_email
                    # Załaduj historię (powinna być pusta dla nowego użytkownika)
                    st.session_state.notebook_history = load_notebook_history(reg_email)
                    st.sidebar.success("Zarejestrowano pomyślnie!")
                    st.rerun()


def add_notebook_to_history(notebook_id: str, notebook_name: str):
    """Dodaj notatnik do historii i zapisz do pliku"""
    st.session_state.notebook_history[notebook_id] = notebook_name
    save_notebook_history(st.session_state.user_email, st.session_state.notebook_history)


def load_notebook_content(notebook_id: str) -> bool:
    """
    Ładuj zawartość notatnika z serwera.
    Zwraca True jeśli udało się załadować, False w przeciwnym wypadku.
    """
    if not notebook_id:
        return False

    try:
        with st.spinner("⏳ Ładuję zawartość notatnika..."):
            content_response, error = make_request("GET", f"/api/notebooks/{notebook_id}/poll")

        if error:
            if "403" in error:
                st.error("🔒 Błąd uprawnień - upewnij się, że Twój e-mail został zaproszony do tego notatnika")
            else:
                st.error(f"❌ {error}")
            st.session_state.notebook_content = ""  # Wyczyść zawartość w razie błędu
            return False

        # Defensywna logika pobierania zawartości z różnych lokalizacji JSONa
        current_content = ""

        if content_response and isinstance(content_response, dict):
            # Wariant 1: Zawartość w response['data']['content'] (struktura wrappowana)
            data_part = content_response.get("data", {})
            if isinstance(data_part, dict):
                # Może być stringiem lub None
                content_candidate = data_part.get("content")
                if content_candidate is not None:
                    current_content = str(content_candidate).strip()

                # Zaktualizuj nazwę jeśli jest w odpowiedzi
                if "title" in data_part:
                    st.session_state.notebook_history[notebook_id] = data_part.get("title")

            # Wariant 2: Zawartość bezpośrednio w response['content']
            if not current_content:
                content_candidate = content_response.get("content")
                if content_candidate is not None:
                    current_content = str(content_candidate).strip()

        # Konwertuj na string i wyczyść żeby nie miał żadnych dziwnych typów
        current_content = str(current_content) if current_content else ""

        # Zaktualizuj session state PRZED renderowaniem
        st.session_state.notebook_content = current_content
        st.session_state.last_loaded_notebook_id = notebook_id

        return True

    except Exception as e:
        st.error(f"⚠️ Nieoczekiwany błąd: {str(e)}")
        st.session_state.notebook_content = ""
        return False


def dashboard_view():
    """Widok Dashboard - lista i tworzenie notatników"""
    st.subheader("📚 Pulpit nawigacyjny")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write("Wybierz notatnik z historii lub utwórz nowy")

    with col2:
        if st.button("➕ Nowy notatnik", key="new_notebook_btn"):
            st.session_state.show_create_form = True

    # Formularz tworzenia nowego notatnika
    if st.session_state.get("show_create_form", False):
        with st.form("create_notebook_form"):
            st.subheader("Utwórz nowy notatnik")
            new_title = st.text_input("Tytuł notatnika")
            submit = st.form_submit_button("Utwórz")

            if submit:
                if not new_title:
                    st.error("Tytuł nie może być pusty")
                else:
                    data = {"title": new_title}
                    response, error = make_request("POST", "/api/notebooks/", data)

                    if error:
                        st.error(error)
                    else:
                        # Pobierz ID z klucza 'data'
                        new_notebook_id = response.get("data", {}).get("id")
                        if new_notebook_id:
                            add_notebook_to_history(new_notebook_id, new_title)
                            st.session_state.selected_notebook_id = new_notebook_id
                            st.session_state.current_view = "editor"
                        st.success("Notatnik utworzony pomyślnie!")
                        st.session_state.show_create_form = False
                        st.rerun()

    # Historia notatników
    st.divider()
    st.subheader("📋 Twoja historia")

    if not st.session_state.notebook_history:
        st.info("Brak notatników w historii. Utwórz lub załaduj notatnik!")

        # Opcja ręcznego załadowania notatnika
        with st.expander("📥 Załaduj istniejący notatnik"):
            manual_id = st.text_input("Wpisz ID notatnika do załadowania")
            manual_name = st.text_input("Nazwa notatnika (opcjonalnie)")

            if st.button("Załaduj"):
                if manual_id:
                    display_name = manual_name if manual_name else f"Notatnik {manual_id}"
                    add_notebook_to_history(manual_id, display_name)
                    st.session_state.selected_notebook_id = manual_id
                    # Spróbuj załadować zawartość
                    if load_notebook_content(manual_id):
                        st.session_state.current_view = "editor"
                        st.success("Notatnik załadowany!")
                        st.rerun()
                    # Jeśli nie udało się załadować, zostać w dashboard ale wyświetlacz błąd (już jest)
                else:
                    st.error("Podaj ID notatnika")
        return

    # Selectbox do wyboru z historii
    notebook_names = list(st.session_state.notebook_history.values())
    notebook_ids = list(st.session_state.notebook_history.keys())

    selected_name = st.selectbox(
        "Wybierz notatnik",
        notebook_names,
        key="notebook_history_select"
    )

    if selected_name:
        selected_id = notebook_ids[notebook_names.index(selected_name)]

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✏️ Otwórz", key="open_notebook_btn"):
                st.session_state.selected_notebook_id = selected_id
                # Spróbuj załadować zawartość przed przejściem
                if load_notebook_content(selected_id):
                    st.session_state.current_view = "editor"
                    st.rerun()
                # Jeśli nie udało się załadować, zostać w dashboard ale wyświetlacher błąd (już jest)

        with col2:
            if st.button("🗑️ Usuń z historii", key="delete_history_btn"):
                del st.session_state.notebook_history[selected_id]
                save_notebook_history(st.session_state.user_email, st.session_state.notebook_history)
                st.rerun()

        with col3:
            st.caption(f"`{selected_id}`")

    # Opcja ręcznego załadowania kolejnego notatnika
    st.divider()
    with st.expander("📥 Załaduj inny notatnik"):
        manual_id = st.text_input("Wpisz ID notatnika", key="manual_load_id")
        manual_name = st.text_input("Nazwa notatnika (opcjonalnie)", key="manual_load_name")

        if st.button("Załaduj", key="manual_load_btn"):
            if manual_id:
                if manual_id not in st.session_state.notebook_history:
                    display_name = manual_name if manual_name else f"Notatnik {manual_id}"
                    add_notebook_to_history(manual_id, display_name)
                # Spróbuj załadować zawartość
                if load_notebook_content(manual_id):
                    st.session_state.selected_notebook_id = manual_id
                    st.session_state.current_view = "editor"
                    st.success("Notatnik załadowany!")
                    st.rerun()
                # Jeśli nie udało się załadować, zostać w dashboard ale wyświetlacz błąd (już jest)
            else:
                st.error("Podaj ID notatnika")


def editor_view():
    """Widok Edytora - edycja notatnika"""
    # Przycisk powrotu
    if st.button("⬅️ Wróć do listy"):
        st.session_state.current_view = "dashboard"
        st.rerun()

    notebook_id = st.session_state.selected_notebook_id
    notebook_name = st.session_state.notebook_history.get(notebook_id, f"Notatnik {notebook_id}")

    st.subheader(f"✏️ {notebook_name}")

    # Sprawdź czy trzeba załadować zawartość (jeśli notebook się zmienił)
    if st.session_state.last_loaded_notebook_id != notebook_id:
        load_notebook_content(notebook_id)

    # Auto-refresh checkbox
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh_enabled = st.checkbox(
            "🔄 Auto-odświeżanie",
            value=st.session_state.auto_refresh,
            key="auto_refresh_checkbox"
        )
        st.session_state.auto_refresh = auto_refresh_enabled

    if auto_refresh_enabled and rerun_if_updated:
        rerun_if_updated(seconds=5)

    # Pobierz zawartość z session state (już załadowaną wcześniej)
    current_content = st.session_state.notebook_content

    # Text area do edycji
    edited_content = st.text_area(
        "Zawartość notatnika",
        value=current_content,
        height=300,
        key="notebook_editor"
    )

    # DEBUG: Pokaż co siedzi w session state
    with st.expander("🔧 DEBUG - Stan notatnika"):
        st.write("**ID notatnika:**", notebook_id)
        st.write("**Ostatnio załadowany ID:**", st.session_state.last_loaded_notebook_id)
        st.write("**Typ current_content:**", type(current_content).__name__)
        st.write("**Długość current_content:**", len(current_content) if isinstance(current_content, str) else "N/A")
        st.write("**Zawartość (pierwsze 100 chars):**", current_content[:100] if current_content else "(pusty)")

    # Przyciski
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🚀 Wyślij przez Kafkę"):
            if edited_content == current_content:
                st.warning("Nie wprowadzono zmian")
            else:
                data = {"content": edited_content}
                response, error = make_request("PUT", f"/api/notebooks/{notebook_id}", data)

                if error:
                    st.error(error)
                else:
                    st.success("✅ Zmiana wysłana do systemu rozproszonego!")
                    st.info("⏳ Przetwarzam wiadomość przez workera... poczekaj sekundę...")

                    # Czekaj na workera aby przetworzy wiadomość
                    time.sleep(1)

                    # Automatycznie odśwież zawartość z serwera
                    st.write("🔄 Ładuję zaktualizowaną zawartość...")
                    if load_notebook_content(notebook_id):
                        st.success("✅ Zawartość zaktualizowana!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Nie udało się załadować zaktualizowanej zawartości. Kliknij 'Odśwież teraz'.")

    with col2:
        if st.button("🔄 Odśwież teraz"):
            load_notebook_content(notebook_id)
            st.rerun()

    with col3:
        if st.button("📝 Zmień nazwę"):
            st.session_state.show_rename_form = True

    with col4:
        if st.button("🗑️ Usuń notatnik"):
            st.session_state.show_delete_confirm = True

    # Formularz zmiany nazwy
    if st.session_state.get("show_rename_form", False):
        with st.form("rename_notebook_form"):
            new_name = st.text_input(
                "Nowa nazwa notatnika",
                value=notebook_name
            )
            submit = st.form_submit_button("Zmień nazwę")

            if submit:
                if new_name:
                    st.session_state.notebook_history[notebook_id] = new_name
                    save_notebook_history(st.session_state.user_email, st.session_state.notebook_history)
                    st.success("Nazwa zmieniona!")
                    st.session_state.show_rename_form = False
                    st.rerun()

    # Potwierdzenie usunięcia
    if st.session_state.get("show_delete_confirm", False):
        st.warning(f"Na pewno chcesz usunąć notatnik '{notebook_name}'?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✓ Tak, usuń"):
                response, error = make_request("DELETE", f"/api/notebooks/{notebook_id}")
                if error:
                    st.error(error)
                else:
                    st.success("Notatnik usunięty!")
                    del st.session_state.notebook_history[notebook_id]
                    save_notebook_history(st.session_state.user_email, st.session_state.notebook_history)
                    st.session_state.show_delete_confirm = False
                    st.session_state.selected_notebook_id = None
                    st.session_state.current_view = "dashboard"
                    st.rerun()
        with col2:
            if st.button("✗ Anuluj"):
                st.session_state.show_delete_confirm = False
                st.rerun()


def main():
    st.set_page_config(page_title="📓 Notatniki", layout="wide")
    st.title("📓 Aplikacja do Notatników")

    # Sidebar autoryzacji
    sidebar_auth()

    # Jeśli nie zalogowany
    if not st.session_state.access_token:
        st.info("👈 Zaloguj się lub zarejestruj w panelu bocznym")
        return

    # Wyświetl odpowiedni widok
    if st.session_state.current_view == "dashboard":
        dashboard_view()
    elif st.session_state.current_view == "editor":
        editor_view()


if __name__ == "__main__":
    main()

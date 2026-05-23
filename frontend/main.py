import streamlit as st
import requests
import time
from typing import Optional, Dict, Any
import os

try:
    from streamlit_autorefresh import rerun_if_updated
except ImportError:
    rerun_if_updated = None

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# Inicjalizacja session state
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
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


def _refresh_access_token() -> bool:
    """Spróbuj odświeżyć access_token za pomocą refresh_token. Zwraca True jeśli się uda."""
    if not st.session_state.refresh_token:
        return False

    url = f"{BACKEND_URL}/auth/refresh"
    data = {"refresh_token": st.session_state.refresh_token}
    headers = {}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)

        if response.status_code == 200:
            response_data = response.json()
            new_access_token = response_data.get("data", {}).get("access_token")
            if new_access_token:
                st.session_state.access_token = new_access_token
                return True

        return False
    except requests.exceptions.RequestException:
        return False


def make_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, require_auth: bool = True) -> tuple[Optional[Dict], Optional[str]]:
    """
    Wykonaj zapytanie HTTP do backendu.
    Zwraca tuple: (response_data, error_message)

    Obsługuje automatyczne odświeżenie tokenu przy 401.
    """
    url = f"{BACKEND_URL}{endpoint}"
    headers = {}

    if require_auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return None, f"Nieznana metoda HTTP: {method}"

        # Obsługa 401 - spróbuj odświeżyć token
        if response.status_code == 401:
            if _refresh_access_token():
                # Ponów zapytanie z nowym tokenem
                headers["Authorization"] = f"Bearer {st.session_state.access_token}"
                try:
                    if method == "GET":
                        response = requests.get(url, headers=headers, timeout=10)
                    elif method == "POST":
                        response = requests.post(url, json=data, headers=headers, timeout=10)
                    elif method == "PUT":
                        response = requests.put(url, json=data, headers=headers, timeout=10)
                    elif method == "DELETE":
                        response = requests.delete(url, headers=headers, timeout=10)
                except requests.exceptions.RequestException as e:
                    return None, f"Błąd sieci: {str(e)}"
            else:
                # Refresh nie powiódł się - wyczyść sesję
                st.session_state.access_token = None
                st.session_state.refresh_token = None
                st.session_state.user_email = None
                return None, "Sesja wygasła. Zaloguj się ponownie."

        # Obsługa 403
        if response.status_code == 403:
            return None, "Brak uprawnień do tego zasobu"

        # Obsługa 404
        if response.status_code == 404:
            return None, "Zasób nie znaleziony (404)"

        # Obsługa innych błędów 4xx i 5xx
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", {})
                if isinstance(error_detail, dict):
                    error_msg = error_detail.get("error", error_detail.get("message", response.text))
                else:
                    error_msg = str(error_detail)
            except:
                error_msg = response.text
            return None, f"Błąd {response.status_code}: {error_msg}"

        return response.json(), None

    except requests.exceptions.ConnectionError:
        return None, "Nie można połączyć się z backendem. Sprawdź czy serwer działa na http://localhost:8000"
    except requests.exceptions.Timeout:
        return None, "Timeout - serwer nie odpowiada"
    except requests.exceptions.RequestException as e:
        return None, f"Błąd sieci: {str(e)}"
    except Exception as e:
        return None, f"Błąd: {str(e)}"


def sidebar_auth():
    """Obsługa logowania i rejestracji w sidebar"""
    st.sidebar.title("🔐 Autoryzacja")

    if st.session_state.access_token:
        st.sidebar.success(f"✅ Zalogowany: {st.session_state.user_email}")
        if st.sidebar.button("Wyloguj"):
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.session_state.user_email = None
            st.session_state.selected_notebook_id = None
            st.session_state.current_view = "dashboard"
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
                    response_data = response.get("data", {})
                    st.session_state.access_token = response_data.get("access_token")
                    st.session_state.refresh_token = response_data.get("refresh_token")
                    st.session_state.user_email = login_email
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
                    # Po signup trzeba zalogować się, aby otrzymać tokeny
                    login_data = {"email": reg_email, "password": reg_password}
                    login_response, login_error = make_request("POST", "/auth/login", login_data, require_auth=False)

                    if login_error:
                        st.sidebar.error(f"Rejestracja ok, ale logowanie nie powiodło się: {login_error}")
                    else:
                        response_data = login_response.get("data", {})
                        st.session_state.access_token = response_data.get("access_token")
                        st.session_state.refresh_token = response_data.get("refresh_token")
                        st.session_state.user_email = reg_email
                        st.sidebar.success("Zarejestrowano i zalogowano pomyślnie!")
                        st.rerun()


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
            st.session_state.notebook_content = ""
            return False

        current_content = ""
        if content_response and isinstance(content_response, dict):
            data_part = content_response.get("data", {})
            if isinstance(data_part, dict):
                content_candidate = data_part.get("content")
                if content_candidate is not None:
                    current_content = str(content_candidate).strip()

        current_content = str(current_content) if current_content else ""
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
        st.write("Zarządzaj swoimi notatnikami")

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
                        new_notebook_id = response.get("data", {}).get("id")
                        if new_notebook_id:
                            st.session_state.selected_notebook_id = new_notebook_id
                            st.session_state.current_view = "editor"
                        st.success("Notatnik utworzony pomyślnie!")
                        st.session_state.show_create_form = False
                        st.rerun()

    # Lista notatników z API
    st.divider()
    st.subheader("📋 Twoje notatniki")

    notebooks_response, error = make_request("GET", "/api/notebooks/")

    if error:
        st.error(f"❌ {error}")
        return

    notebooks = notebooks_response.get("data", []) if notebooks_response else []

    if not notebooks:
        st.info("Nie masz jeszcze żadnych notatników. Utwórz nowy!")
        return

    for notebook in notebooks:
        if not isinstance(notebook, dict):
            continue

        notebook_id = notebook.get("id")
        notebook_title = notebook.get("title", f"Notatnik {notebook_id}")

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button(f"✏️ {notebook_title}", key=f"open_{notebook_id}"):
                st.session_state.selected_notebook_id = notebook_id
                if load_notebook_content(notebook_id):
                    st.session_state.current_view = "editor"
                    st.rerun()

        with col2:
            if st.button("🗑️", key=f"delete_{notebook_id}", help="Usuń notatnik"):
                st.session_state.show_delete_confirm = notebook_id
                st.rerun()

        with col3:
            st.caption(f"`{notebook_id}`")

        # Potwierdzenie usunięcia
        if st.session_state.get("show_delete_confirm") == notebook_id:
            st.warning(f"Na pewno chcesz usunąć '{notebook_title}'?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ Tak", key=f"confirm_delete_{notebook_id}"):
                    response, error = make_request("DELETE", f"/api/notebooks/{notebook_id}")
                    if error:
                        st.error(error)
                    else:
                        st.success("Notatnik usunięty!")
                        st.session_state.show_delete_confirm = None
                        st.rerun()
            with col2:
                if st.button("✗ Nie", key=f"cancel_delete_{notebook_id}"):
                    st.session_state.show_delete_confirm = None
                    st.rerun()

        st.divider()


def editor_view():
    """Widok Edytora - edycja notatnika"""
    if st.button("⬅️ Wróć do listy"):
        st.session_state.current_view = "dashboard"
        st.rerun()

    notebook_id = st.session_state.selected_notebook_id
    st.subheader(f"✏️ Edytor - {notebook_id}")

    if st.session_state.last_loaded_notebook_id != notebook_id:
        load_notebook_content(notebook_id)

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

    current_content = st.session_state.notebook_content

    edited_content = st.text_area(
        "Zawartość notatnika",
        value=current_content,
        height=300,
        key="notebook_editor"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Wyślij"):
            if edited_content == current_content:
                st.warning("Nie wprowadzono zmian")
            else:
                data = {"content": edited_content}
                response, error = make_request("PUT", f"/api/notebooks/{notebook_id}", data)

                if error:
                    st.error(error)
                else:
                    st.success("✅ Zmiana wysłana!")
                    st.info("⏳ Przetwarzam wiadomość... poczekaj sekundę...")
                    time.sleep(1)
                    st.write("🔄 Ładuję zaktualizowaną zawartość...")
                    if load_notebook_content(notebook_id):
                        st.success("✅ Zawartość zaktualizowana!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Nie udało się załadować zawartości. Kliknij 'Odśwież'.")

    with col2:
        if st.button("🔄 Odśwież"):
            load_notebook_content(notebook_id)
            st.rerun()

    with col3:
        if st.button("🗑️ Usuń"):
            st.session_state.show_delete_confirm = True

    if st.session_state.get("show_delete_confirm", False):
        st.divider()
        st.warning(f"Na pewno chcesz usunąć ten notatnik?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✓ Tak, usuń"):
                response, error = make_request("DELETE", f"/api/notebooks/{notebook_id}")
                if error:
                    st.error(error)
                else:
                    st.success("Notatnik usunięty!")
                    st.session_state.show_delete_confirm = False
                    st.session_state.selected_notebook_id = None
                    st.session_state.current_view = "dashboard"
                    st.rerun()
        with col2:
            if st.button("✗ Nie"):
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

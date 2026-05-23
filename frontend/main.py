import streamlit as st
import requests
import time
import difflib
from typing import Optional, Dict, Any
import os

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AUTO_REFRESH_INTERVAL_MS = 5000


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
if "last_confirmed_content" not in st.session_state:
    st.session_state.last_confirmed_content = ""
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "last_loaded_notebook_id" not in st.session_state:
    st.session_state.last_loaded_notebook_id = None


def _clear_editor_widget() -> None:
    st.session_state.pop("notebook_editor", None)


def _trigger_autorefresh(key: str) -> None:
    if st.session_state.auto_refresh and st_autorefresh is not None:
        st_autorefresh(interval=AUTO_REFRESH_INTERVAL_MS, key=key)


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


def assemble_text_from_events(data: Optional[Dict[str, Any]]) -> str:
    if not data or not isinstance(data, dict):
        return ""

    root = data.get("data", data)
    if not isinstance(root, dict):
        return ""

    chain = root.get("content_event_chain", [])
    if isinstance(chain, list) and chain:
        pass
    elif root.get("content") is not None:
        return str(root.get("content"))
    else:
        chain = []
    if not isinstance(chain, list) or not chain:
        return ""

    # Ensure events are applied in server order
    chain = sorted(chain, key=lambda x: x.get("server_version", 0))

    buffer: list[str] = []
    for event in chain:
        if not isinstance(event, dict):
            continue

        op = event.get("op")
        # Prefer char_start (backend format), fall back to index
        index = event.get("char_start") if event.get("char_start") is not None else event.get("index", 0)
        try:
            index = int(index)
        except Exception:
            index = 0

        text = event.get("text", "") or ""
        length = int(event.get("length", 0) or 0)

        if op == "insert":
            for i, ch in enumerate(text):
                insert_pos = max(0, min(len(buffer), index + i))
                buffer.insert(insert_pos, ch)
        elif op == "delete":
            if index < 0:
                continue
            if index < len(buffer):
                del buffer[index : index + length]
        elif op == "replace":
            new_text = text if text else event.get("content", "")
            buffer = list(new_text)

    return "".join(buffer)


def _line_col_from_index(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    col = index - last_newline - 1 if last_newline != -1 else index
    return line, col


def compute_edit_operation(old_text: str, new_text: str) -> Optional[Dict[str, Any]]:
    if old_text == new_text:
        return None

    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    ops = [op for op in matcher.get_opcodes() if op[0] != "equal"]

    if len(ops) == 1:
        tag, i1, i2, j1, j2 = ops[0]
        line, col = _line_col_from_index(old_text, i1)

        if tag == "delete":
            return {
                "op": "delete",
                "line_start": line,
                "char_start": col,
                "text": "",
                "length": i2 - i1,
            }
        if tag == "insert":
            return {
                "op": "insert",
                "line_start": line,
                "char_start": col,
                "text": new_text[j1:j2],
            }
        if tag == "replace":
            return {
                "op": "replace",
                "line_start": line,
                "char_start": col,
                "text": new_text[j1:j2],
                "length": i2 - i1,
            }

    # Fallback: wyślij pełne nadpisanie, jeżeli zmiana jest złożona.
    return {"op": "replace", "text": new_text, "line_start": 1, "char_start": 0}


def build_update_payload(op_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mapuj operację edycji na format oczekiwany przez API i workera."""
    payload = dict(op_data)
    op = payload.get("op", "insert")

    if op == "delete":
        payload.setdefault("content", "")
        payload.setdefault("text", "")
    elif op in ("insert", "replace"):
        text = payload.get("text", "")
        payload["content"] = text

    payload.setdefault("content", payload.get("text", ""))
    return payload


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


def load_notebook_content(notebook_id: str, *, silent: bool = False) -> tuple[bool, bool]:
    """
    Ładuj pełną zawartość notatnika z serwera.
    Zwraca (sukces, czy_treść_się_zmieniła).
    """
    if not notebook_id:
        return False, False

    try:
        if silent:
            content_response, error = make_request(
                "GET", f"/api/notebooks/{notebook_id}"
            )
        else:
            with st.spinner("⏳ Ładuję zawartość notatnika..."):
                content_response, error = make_request(
                    "GET", f"/api/notebooks/{notebook_id}"
                )

        if error:
            if "403" in error:
                st.error("🔒 Błąd uprawnień - upewnij się, że Twój e-mail został zaproszony do tego notatnika")
            else:
                st.error(f"❌ {error}")
            st.session_state.notebook_content = ""
            return False, False

        server_content = assemble_text_from_events(content_response)
        server_content = server_content if server_content is not None else ""

        previous_content = st.session_state.notebook_content
        content_changed = server_content != previous_content

        st.session_state.notebook_content = server_content
        st.session_state.last_confirmed_content = server_content
        st.session_state.last_loaded_notebook_id = notebook_id
        return True, content_changed

    except Exception as e:
        st.error(f"⚠️ Nieoczekiwany błąd: {str(e)}")
        st.session_state.notebook_content = ""
        return False, False


def dashboard_view():
    """Widok Dashboard - lista i tworzenie notatników"""
    st.subheader("📚 Pulpit nawigacyjny")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.write("Zarządzaj swoimi notatnikami")

    with col2:
        auto_refresh_enabled = st.checkbox(
            "🔄 Auto-odświeżanie",
            value=st.session_state.auto_refresh,
            key="dashboard_auto_refresh",
        )
        st.session_state.auto_refresh = auto_refresh_enabled
        if auto_refresh_enabled and st_autorefresh is None:
            st.caption("Brak pakietu streamlit-autorefresh — przebuduj frontend.")

    with col3:
        if st.button("🔄 Odśwież listę", key="dashboard_manual_refresh"):
            st.rerun()

    with col4:
        if st.button("➕ Nowy notatnik", key="new_notebook_btn"):
            st.session_state.show_create_form = True

    _trigger_autorefresh("dashboard_autorefresh")

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
                st.session_state.notebook_content = ""
                ok, _ = load_notebook_content(notebook_id)
                if ok:
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
    notebook_id = st.session_state.selected_notebook_id

    if st.button("⬅️ Wróć do listy"):
        st.session_state.current_view = "dashboard"
        st.rerun()

    st.subheader(f"✏️ Edytor - {notebook_id}")
    st.code(notebook_id, language="")

    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh_enabled = st.checkbox(
            "🔄 Auto-odświeżanie",
            value=st.session_state.auto_refresh,
            key="editor_auto_refresh",
        )
        st.session_state.auto_refresh = auto_refresh_enabled
        if auto_refresh_enabled and st_autorefresh is None:
            st.caption("Brak pakietu streamlit-autorefresh — przebuduj frontend.")

    _trigger_autorefresh("editor_autorefresh")

    if st.session_state.last_loaded_notebook_id != notebook_id:
        load_notebook_content(notebook_id)

    edited_content = st.text_area(
        "Zawartość notatnika",
        value=st.session_state.notebook_content,
        height=300,
        key="notebook_editor",
    )

    if edited_content != st.session_state.notebook_content:
        st.session_state.notebook_content = edited_content

    has_local_edits = (
        st.session_state.notebook_content != st.session_state.last_confirmed_content
    )

    if auto_refresh_enabled and not has_local_edits:
        ok, content_changed = load_notebook_content(notebook_id, silent=True)
        if ok and content_changed:
            _clear_editor_widget()
            st.rerun()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Wyślij"):
            op_data = compute_edit_operation(
                st.session_state.last_confirmed_content,
                st.session_state.notebook_content,
            )

            if not op_data:
                st.warning("Nie wprowadzono zmian")
            else:
                payload = build_update_payload(op_data)
                response, error = make_request(
                    "PUT", f"/api/notebooks/{notebook_id}", payload
                )

                if error:
                    st.error(error)
                else:
                    st.session_state.last_confirmed_content = (
                        st.session_state.notebook_content
                    )
                    st.success("✅ Zmiana wysłana!")
                    time.sleep(0.5)
                    ok, content_changed = load_notebook_content(
                        notebook_id, silent=True
                    )
                    if ok and content_changed:
                        _clear_editor_widget()
                        st.rerun()

    with col2:
        if st.button("🔄 Odśwież"):
            ok, content_changed = load_notebook_content(notebook_id)
            if ok:
                if content_changed:
                    _clear_editor_widget()
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

    # Sidebar - Zapraszanie
    with st.sidebar:
        st.sidebar.divider()
        st.sidebar.subheader("👥 Udostępnianie")
        invite_email = st.sidebar.text_input("E-mail współpracownika", key="invite_email")
        if st.sidebar.button("Zaproś"):
            if not invite_email or "@" not in invite_email:
                st.sidebar.error("Wpisz poprawny e-mail")
            else:
                response, error = make_request(
                    "PUT",
                    f"/api/notebooks/{notebook_id}/invite",
                    {"emails": [invite_email]}
                )
                if error:
                    st.sidebar.error(f"❌ {error}")
                else:
                    st.sidebar.success(f"✅ Zaproszenie wysłane do {invite_email}")
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

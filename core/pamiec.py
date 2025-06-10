# core/pamiec.py
import json
import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
import uuid

# === Ścieżki względne do projektu ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data", "db")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

DB_HISTORIA = os.path.join(DB_DIR, "historia.db")
DB_WIADOMOSCI = os.path.join(DB_DIR, "wiadomosci.db")
DB_ANALYTICS = os.path.join(DB_DIR, "analytics.db")

# Upewnij się, że foldery istnieją
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

@contextmanager
def get_db_connection(db_path):
    """Context manager dla bezpiecznego zarządzania połączeniami DB"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Umożliwia dostęp do kolumn po nazwach
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_databases():
    """Inicjalizuje wszystkie bazy danych z tabelami"""
    
    # Historia rozmów
    with get_db_connection(DB_HISTORIA) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historia_rozmow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                tekst_wejsciowy TEXT NOT NULL,
                tekst_wyjsciowy TEXT NOT NULL,
                intencja TEXT,
                model_llm TEXT,
                czas_odpowiedzi_ms INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT  -- JSON z dodatkowymi danymi
            )
        """)
        
        # Index dla szybszego wyszukiwania
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON historia_rozmow(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON historia_rozmow(session_id)")
        conn.commit()
    
    # System wiadomości/notatek
    with get_db_connection(DB_WIADOMOSCI) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wiadomosci (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                tytul TEXT NOT NULL,
                tresc TEXT NOT NULL,
                nadawca TEXT DEFAULT 'Użytkownik',
                priorytet INTEGER DEFAULT 1,  -- 1=niski, 2=średni, 3=wysoki
                status TEXT DEFAULT 'aktywne',  -- aktywne, archiwalne, usunięte
                kategoria TEXT DEFAULT 'notatka',
                data_przypomnienia DATETIME,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON wiadomosci(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_przypomnienie ON wiadomosci(data_przypomnienia)")
        conn.commit()
    
    # Analytics i metryki
    with get_db_connection(DB_ANALYTICS) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metryki_systemu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                typ_metryki TEXT NOT NULL,  -- 'tts_usage', 'stt_usage', 'llm_usage', 'intencja'
                wartosc TEXT NOT NULL,
                licznik INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_typ_metryki ON metryki_systemu(typ_metryki)")
        conn.commit()

# === HISTORIA ROZMÓW ===
def zapisz_rozmowe(tekst_wej, tekst_wyj, intencja=None, model_llm=None, czas_ms=None, session_id=None, metadata=None):
    """
    Zapisuje rozmowę do historii
    Args:
        tekst_wej: tekst wejściowy użytkownika
        tekst_wyj: odpowiedź systemu
        intencja: rozpoznana intencja (jeśli była)
        model_llm: użyty model LLM
        czas_ms: czas odpowiedzi w milisekundach
        session_id: ID sesji rozmowy
        metadata: dodatkowe dane jako słownik
    """
    try:
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]  # Krótkie ID sesji
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        with get_db_connection(DB_HISTORIA) as conn:
            conn.execute("""
                INSERT INTO historia_rozmow 
                (session_id, tekst_wejsciowy, tekst_wyjsciowy, intencja, model_llm, czas_odpowiedzi_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, tekst_wej, tekst_wyj, intencja, model_llm, czas_ms, metadata_json))
            conn.commit()
        
        print(f"📝 Zapisano rozmowę: {tekst_wej[:30]}... → {tekst_wyj[:30]}...")
        return session_id
        
    except Exception as e:
        print(f"❌ Błąd zapisu rozmowy: {e}")
        return None

def pobierz_historie_rozmow(limit=10, session_id=None, dni_wstecz=None):
    """Pobiera historię rozmów z opcjonalnymi filtrami"""
    try:
        with get_db_connection(DB_HISTORIA) as conn:
            query = "SELECT * FROM historia_rozmow WHERE 1=1"
            params = []
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            if dni_wstecz:
                cutoff_date = datetime.now() - timedelta(days=dni_wstecz)
                query += " AND timestamp >= ?"
                params.append(cutoff_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception as e:
        print(f"❌ Błąd pobierania historii: {e}")
        return []

# === SYSTEM WIADOMOŚCI ===
def zapisz_wiadomosc(tytul, tresc, nadawca="Użytkownik", priorytet=1, kategoria="notatka", data_przypomnienia=None):
    """Zapisuje wiadomość/notatkę"""
    try:
        message_uuid = str(uuid.uuid4())
        
        with get_db_connection(DB_WIADOMOSCI) as conn:
            conn.execute("""
                INSERT INTO wiadomosci 
                (uuid, tytul, tresc, nadawca, priorytet, kategoria, data_przypomnienia)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_uuid, tytul, tresc, nadawca, priorytet, kategoria, data_przypomnienia))
            conn.commit()
        
        print(f"💾 Zapisano wiadomość: {tytul}")
        return message_uuid
        
    except Exception as e:
        print(f"❌ Błąd zapisu wiadomości: {e}")
        return None

def pobierz_wiadomosci(limit=10, status="aktywne", kategoria=None, priorytet_min=1):
    """Pobiera wiadomości z filtrami"""
    try:
        with get_db_connection(DB_WIADOMOSCI) as conn:
            query = "SELECT * FROM wiadomosci WHERE status = ? AND priorytet >= ?"
            params = [status, priorytet_min]
            
            if kategoria:
                query += " AND kategoria = ?"
                params.append(kategoria)
            
            query += " ORDER BY priorytet DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception as e:
        print(f"❌ Błąd pobierania wiadomości: {e}")
        return []

def pobierz_przypomnienia():
    """Pobiera wiadomości z datą przypomnienia w przeszłości lub dzisiaj"""
    try:
        with get_db_connection(DB_WIADOMOSCI) as conn:
            cursor = conn.execute("""
                SELECT * FROM wiadomosci 
                WHERE data_przypomnienia <= datetime('now') 
                AND status = 'aktywne'
                ORDER BY data_przypomnienia ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception as e:
        print(f"❌ Błąd pobierania przypomnień: {e}")
        return []

def usun_wiadomosc(uuid_lub_tytul):
    """Usuwa wiadomość (soft delete - zmienia status)"""
    try:
        with get_db_connection(DB_WIADOMOSCI) as conn:
            # Próbuj UUID pierwszy, potem tytuł
            cursor = conn.execute("UPDATE wiadomosci SET status = 'usunięte' WHERE uuid = ? OR tytul = ?", 
                                (uuid_lub_tytul, uuid_lub_tytul))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"🗑️ Usunięto wiadomość: {uuid_lub_tytul}")
                return True
            else:
                print(f"❌ Nie znaleziono wiadomości: {uuid_lub_tytul}")
                return False
                
    except Exception as e:
        print(f"❌ Błąd usuwania wiadomości: {e}")
        return False

# === ANALYTICS ===
def zapisz_metrykę(typ, wartosc):
    """Zapisuje metrykę do analizy użycia"""
    try:
        with get_db_connection(DB_ANALYTICS) as conn:
            # Sprawdź czy metryka już istnieje
            cursor = conn.execute("SELECT licznik FROM metryki_systemu WHERE typ_metryki = ? AND wartosc = ?", 
                                (typ, wartosc))
            row = cursor.fetchone()
            
            if row:
                # Zwiększ licznik
                conn.execute("UPDATE metryki_systemu SET licznik = licznik + 1 WHERE typ_metryki = ? AND wartosc = ?",
                           (typ, wartosc))
            else:
                # Dodaj nową metrykę
                conn.execute("INSERT INTO metryki_systemu (typ_metryki, wartosc) VALUES (?, ?)", 
                           (typ, wartosc))
            
            conn.commit()
            
    except Exception as e:
        print(f"❌ Błąd zapisu metryki: {e}")

def pobierz_statystyki(dni_wstecz=7):
    """Pobiera statystyki użycia systemu"""
    try:
        stats = {}
        cutoff_date = datetime.now() - timedelta(days=dni_wstecz)
        
        # Statystyki rozmów
        with get_db_connection(DB_HISTORIA) as conn:
            cursor = conn.execute("SELECT COUNT(*) as rozmowy FROM historia_rozmow WHERE timestamp >= ?", 
                                (cutoff_date,))
            stats['rozmowy'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT intencja, COUNT(*) as liczba FROM historia_rozmow WHERE timestamp >= ? GROUP BY intencja", 
                                (cutoff_date,))
            stats['intencje'] = {row[0] or 'llm': row[1] for row in cursor.fetchall()}
        
        # Statystyki wiadomości
        with get_db_connection(DB_WIADOMOSCI) as conn:
            cursor = conn.execute("SELECT COUNT(*) as wiadomosci FROM wiadomosci WHERE timestamp >= ?", 
                                (cutoff_date,))
            stats['wiadomosci'] = cursor.fetchone()[0]
        
        return stats
        
    except Exception as e:
        print(f"❌ Błąd pobierania statystyk: {e}")
        return {}

# === KOMPATYBILNOŚĆ WSTECZNA ===
def zapisz_do_historii_logu(wej, wyj):
    """Funkcja kompatybilna z oryginalnym loggerem"""
    return zapisz_rozmowe(wej, wyj)

def odczytaj_zapisane_wiadomosci(limit=1):
    """Kompatybilność z oryginalnym API"""
    wiadomosci = pobierz_wiadomosci(limit=limit)
    return [(w['tytul'], w['tresc'], w['timestamp']) for w in wiadomosci]

def odczytaj_nowe_wiadomosci(limit=5):
    """Kompatybilność z oryginalnym API"""
    return odczytaj_zapisane_wiadomosci(limit)

# === INICJALIZACJA ===
def inicjalizuj_pamiec():
    """Inicjalizuje system pamięci"""
    try:
        init_databases()
        print("✅ System pamięci zainicjalizowany")
        return True
    except Exception as e:
        print(f"❌ Błąd inicjalizacji pamięci: {e}")
        return False

# === TEST LOKALNY ===
if __name__ == "__main__":
    print("🧪 Test systemu pamięci")
    
    if inicjalizuj_pamiec():
        # Test zapisu rozmowy
        session = zapisz_rozmowe("Cześć", "Witaj! Jak mogę pomóc?", "powitanie", "gpt-3.5", 150)
        
        # Test wiadomości
        zapisz_wiadomosc("Test", "To jest testowa wiadomość", priorytet=2)
        
        # Test statystyk
        stats = pobierz_statystyki()
        print(f"Statystyki: {stats}")
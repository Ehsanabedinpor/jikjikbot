"""
Database module for Jik Jik Bot using SQLite
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from config import DATABASE_PATH, JIK_JIK_COOLDOWN

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        conn = self.get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                points INTEGER DEFAULT 0,
                eggs INTEGER DEFAULT 0,
                chickens INTEGER DEFAULT 0,
                roosters INTEGER DEFAULT 0,
                last_jik_jik TEXT,
                auto_jik_enabled INTEGER DEFAULT 0,
                auto_jik_last_claimed TEXT,
                betting_balance INTEGER DEFAULT 0,
                total_jik_jiks INTEGER DEFAULT 0,
                bot_blocked INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        for col, definition in [('bot_blocked', 'INTEGER DEFAULT 0')]:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass

        c.execute("""
            CREATE TABLE IF NOT EXISTS animals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                animal_type TEXT CHECK(animal_type IN ('chicken', 'rooster')),
                name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                package_type TEXT,
                item_type TEXT,
                item_count INTEGER,
                price_toman INTEGER,
                charge_id TEXT,
                status TEXT DEFAULT 'completed',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        for col, definition in [
            ('item_type', 'TEXT'),
            ('item_count', 'INTEGER'),
            ('charge_id', 'TEXT'),
        ]:
            try:
                c.execute(f"ALTER TABLE payments ADD COLUMN {col} {definition}")
            except Exception:
                pass

        c.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                chat_type TEXT,
                chat_id INTEGER,
                points_before INTEGER,
                points_after INTEGER,
                eggs_before INTEGER,
                eggs_after INTEGER,
                extra_data TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS auto_jik_pending (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                pending_points INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS tictactoe_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                board TEXT,
                current_turn INTEGER,
                bet_amount INTEGER,
                status TEXT DEFAULT 'pending',
                winner INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (player1_id) REFERENCES users(user_id),
                FOREIGN KEY (player2_id) REFERENCES users(user_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    # ==================== USER OPERATIONS ====================

    def get_user(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row is None:
            return None
        return dict(row)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE LOWER(username)=?", (username.lower(),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return None
        return dict(row)

    def get_or_create_user(self, user_id: int, username: str = None,
                           first_name: str = None, last_name: str = None) -> Dict:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            if username:
                c.execute(
                    "UPDATE users SET username=?, first_name=?, updated_at=datetime('now') WHERE user_id=?",
                    (username, first_name or dict(row).get('first_name'), user_id)
                )
            conn.commit()
            conn.close()
            return dict(row)
        c.execute(
            "INSERT INTO users (user_id, username, first_name, last_name) VALUES (?,?,?,?)",
            (user_id, username, first_name, last_name)
        )
        conn.commit()
        conn.close()
        return self.get_user(user_id) or {}

    def add_points(self, user_id: int, points: int) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE users SET points=points+?, updated_at=datetime('now') WHERE user_id=?",
            (points, user_id)
        )
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        new_points = row[0] if row else 0
        conn.commit()
        conn.close()
        return new_points

    def deduct_points(self, user_id: int, points: int) -> Tuple[bool, int]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if not row or row[0] < points:
            conn.close()
            return False, row[0] if row else 0
        c.execute(
            "UPDATE users SET points=points-?, updated_at=datetime('now') WHERE user_id=?",
            (points, user_id)
        )
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        remaining = c.fetchone()[0]
        conn.commit()
        conn.close()
        return True, remaining

    # ==================== JIK JIK ====================

    def can_jik_jik(self, user_id: int) -> Tuple[bool, int]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT last_jik_jik FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        if not row or not row[0]:
            return True, 0
        try:
            last_time = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
        except Exception:
            return True, 0
        now_utc = datetime.now(timezone.utc)
        elapsed = (now_utc - last_time).total_seconds()
        if elapsed >= JIK_JIK_COOLDOWN:
            return True, 0
        return False, int(JIK_JIK_COOLDOWN - elapsed)

    def use_jik_jik(self, user_id: int) -> bool:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET
                last_jik_jik=datetime('now'),
                total_jik_jiks=total_jik_jiks+1,
                updated_at=datetime('now')
            WHERE user_id=?
        """, (user_id,))
        conn.commit()
        conn.close()
        return True

    # ==================== EGGS ====================

    def add_egg(self, user_id: int, count: int = 1) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE users SET eggs=eggs+?, updated_at=datetime('now') WHERE user_id=?",
            (count, user_id)
        )
        c.execute("SELECT eggs FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        new_count = row[0] if row else 0
        conn.commit()
        conn.close()
        return new_count

    def deduct_eggs(self, user_id: int, count: int = 1) -> Tuple[bool, int]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT eggs FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if not row or row[0] < count:
            conn.close()
            return False, row[0] if row else 0
        c.execute(
            "UPDATE users SET eggs=eggs-?, updated_at=datetime('now') WHERE user_id=?",
            (count, user_id)
        )
        c.execute("SELECT eggs FROM users WHERE user_id=?", (user_id,))
        remaining = c.fetchone()[0]
        conn.commit()
        conn.close()
        return True, remaining

    # ==================== ANIMALS ====================

    def add_animal(self, user_id: int, animal_type: str) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO animals (user_id, animal_type) VALUES (?,?)", (user_id, animal_type))
        animal_id = c.lastrowid
        col = 'chickens' if animal_type == 'chicken' else 'roosters'
        c.execute(f"UPDATE users SET {col}={col}+1, updated_at=datetime('now') WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        return animal_id

    def get_user_animals(self, user_id: int) -> List[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM animals WHERE user_id=?", (user_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def name_animal(self, animal_id: int, name: str) -> bool:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("UPDATE animals SET name=? WHERE id=?", (name, animal_id))
        success = c.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_animal(self, animal_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM animals WHERE id=?", (animal_id,))
        row = c.fetchone()
        conn.close()
        if row is None:
            return None
        return dict(row)

    def remove_animal(self, animal_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM animals WHERE id=?", (animal_id,))
        animal = c.fetchone()
        if not animal:
            conn.close()
            return None
        animal_dict = dict(animal)
        col = 'chickens' if animal_dict['animal_type'] == 'chicken' else 'roosters'
        c.execute("DELETE FROM animals WHERE id=?", (animal_id,))
        c.execute(f"UPDATE users SET {col}={col}-1, updated_at=datetime('now') WHERE user_id=?",
                  (animal_dict['user_id'],))
        conn.commit()
        conn.close()
        return animal_dict

    # ==================== PAYMENTS ====================

    def record_payment(self, user_id: int, package_type: str, item_type: str,
                       item_count: int, price_toman: int = 0,
                       charge_id: str = None, status: str = 'completed') -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO payments (user_id, package_type, item_type, item_count,
                                  price_toman, charge_id, status)
            VALUES (?,?,?,?,?,?,?)
        """, (user_id, package_type, item_type, item_count, price_toman, charge_id, status))
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        logger.info(
            f"[PAYMENT] user={user_id} pkg={package_type} item={item_type} "
            f"count={item_count} price={price_toman}T charge={charge_id} status={status}"
        )
        return row_id

    # ==================== EVENT LOGS ====================

    def log_event(self, user_id: int, event_type: str,
                  chat_type: str = 'private', chat_id: int = None,
                  points_before: int = None, points_after: int = None,
                  eggs_before: int = None, eggs_after: int = None,
                  extra: dict = None):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO event_logs
              (user_id, event_type, chat_type, chat_id,
               points_before, points_after, eggs_before, eggs_after, extra_data)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            user_id, event_type, chat_type, chat_id,
            points_before, points_after,
            eggs_before, eggs_after,
            json.dumps(extra, ensure_ascii=False) if extra else None
        ))
        conn.commit()
        conn.close()
        logger.debug(
            f"[EVENT] user={user_id} type={event_type} "
            f"pts={points_before}->{points_after} extra={extra}"
        )

    # ==================== AUTO JIK JIK ====================

    def is_auto_jik_enabled(self, user_id: int) -> bool:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT auto_jik_enabled FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row and row[0])

    def enable_auto_jik(self, user_id: int) -> bool:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET auto_jik_enabled=1,
            auto_jik_last_claimed=datetime('now'), updated_at=datetime('now')
            WHERE user_id=?
        """, (user_id,))
        success = c.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_auto_jik_users(self) -> List[Dict]:
        """Return all users with auto_jik enabled and not blocked."""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT user_id, points, bot_blocked
            FROM users
            WHERE auto_jik_enabled=1 AND bot_blocked=0
        """)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def give_auto_jik_points(self, user_id: int, points: int) -> int:
        """Add auto jik points and update last_claimed. Returns new total."""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET points=points+?,
            auto_jik_last_claimed=datetime('now'),
            updated_at=datetime('now')
            WHERE user_id=?
        """, (points, user_id))
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        new_total = row[0] if row else 0
        conn.commit()
        conn.close()
        return new_total

    def set_bot_blocked(self, user_id: int, blocked: bool):
        """Mark user as having blocked/unblocked the bot."""
        if user_id is None:
            logger.warning("[BOT_BLOCK] Called with None user_id, skipping")
            return
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE users SET bot_blocked=?, updated_at=datetime('now') WHERE user_id=?",
            (1 if blocked else 0, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"[BOT_BLOCK] user={user_id} blocked={blocked}")

    def get_pending_auto_jik(self, user_id: int) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT pending_points FROM auto_jik_pending WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0

    def claim_pending_auto_jik(self, user_id: int) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT pending_points FROM auto_jik_pending WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if not row or row[0] == 0:
            conn.close()
            return 0
        points = row[0]
        c.execute(
            "UPDATE users SET points=points+?, updated_at=datetime('now') WHERE user_id=?",
            (points, user_id)
        )
        c.execute("UPDATE auto_jik_pending SET pending_points=0 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        return points

    def add_pending_auto_jik(self, user_id: int, points: int):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO auto_jik_pending (user_id, pending_points)
            VALUES (?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                pending_points=pending_points+?, last_updated=datetime('now')
        """, (user_id, points, points))
        conn.commit()
        conn.close()

    def update_auto_jik_last_claimed(self, user_id: int):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET auto_jik_last_claimed=datetime('now'),
            updated_at=datetime('now') WHERE user_id=?
        """, (user_id,))
        conn.commit()
        conn.close()

    # ==================== LEGACY ====================

    def log_activity(self, user_id: int, action: str, details: str = None):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO activity_logs (user_id, action, details) VALUES (?,?,?)",
            (user_id, action, details)
        )
        conn.commit()
        conn.close()

    # ==================== TIC TAC TOE ====================

    def create_tictactoe_game(self, player1_id: int, player2_id: int, bet_amount: int) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO tictactoe_games (player1_id, player2_id, board, current_turn, bet_amount, status)
            VALUES (?,?,'---------',?,?,'active')
        """, (player1_id, player2_id, player1_id, bet_amount))
        game_id = c.lastrowid
        conn.commit()
        conn.close()
        return game_id

    def get_tictactoe_game(self, game_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM tictactoe_games WHERE id=?", (game_id,))
        row = c.fetchone()
        conn.close()
        if row is None:
            return None
        return dict(row)

    def delete_tictactoe_game(self, game_id: int):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM tictactoe_games WHERE id=?", (game_id,))
        conn.commit()
        conn.close()

    # ==================== STATISTICS ====================

    def get_total_users(self) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_top_users(self, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT user_id, username, points, total_jik_jiks
            FROM users ORDER BY points DESC LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_betting_balance(self, user_id: int) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT betting_balance FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0


db = Database()

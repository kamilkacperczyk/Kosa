"""
Zakladka Subskrypcja — wyswietla aktualny plan, zuzycie rund, porownanie planow i historie platnosci.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QProgressBar,
)
from PySide6.QtCore import Qt

from gui.db import get_subscription, get_payments, get_plans, get_daily_usage


class SubscriptionTab(QWidget):
    """Zakladka z informacjami o subskrypcji uzytkownika."""

    def __init__(self, user_id: int, subscription: dict):
        super().__init__()
        self._user_id = user_id
        self._subscription = subscription or {}
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(16, 16, 16, 16)

        # === HEADER + REFRESH ===
        header_row = QHBoxLayout()
        page_title = QLabel("Twoja subskrypcja")
        page_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #53a8b6;"
        )
        header_row.addWidget(page_title)
        header_row.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        refresh_btn = QPushButton("Odswiez")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #53a8b6; border: 1px solid #53a8b6; "
            "border-radius: 6px; padding: 6px 16px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: #16213e; color: #17b890; border-color: #17b890; }"
        )
        refresh_btn.clicked.connect(self._refresh_data)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        # === AKTUALNY PLAN — karta ===
        self._plan_card = QFrame()
        self._plan_card.setObjectName("subscriptionCard")
        card_layout = QVBoxLayout(self._plan_card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(20, 16, 20, 16)

        plan_header_row = QHBoxLayout()
        plan_label = QLabel("Aktualny plan")
        plan_label.setStyleSheet("color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        plan_header_row.addWidget(plan_label)
        plan_header_row.addStretch()

        self._plan_badge = QLabel()
        self._plan_badge.setStyleSheet(
            "background-color: #1b998b; color: white; font-size: 10px; font-weight: bold; "
            "padding: 2px 10px; border-radius: 10px;"
        )
        plan_header_row.addWidget(self._plan_badge)
        card_layout.addLayout(plan_header_row)

        self._plan_name_label = QLabel()
        card_layout.addWidget(self._plan_name_label)

        self._plan_status_label = QLabel()
        self._plan_status_label.setStyleSheet("color: #888; font-size: 12px;")
        card_layout.addWidget(self._plan_status_label)

        # Separator w karcie
        card_sep = QFrame()
        card_sep.setFrameShape(QFrame.HLine)
        card_sep.setStyleSheet("background-color: #0f3460; max-height: 1px;")
        card_layout.addWidget(card_sep)

        self._plan_features_label = QLabel()
        self._plan_features_label.setStyleSheet("color: #aaa; font-size: 12px; line-height: 1.6;")
        self._plan_features_label.setWordWrap(True)
        card_layout.addWidget(self._plan_features_label)

        layout.addWidget(self._plan_card)

        # === ZUZYCIE RUND — karta z progress barem ===
        self._usage_card = QFrame()
        self._usage_card.setObjectName("subscriptionCard")
        usage_layout = QVBoxLayout(self._usage_card)
        usage_layout.setSpacing(10)
        usage_layout.setContentsMargins(20, 16, 20, 16)

        usage_header = QLabel("Dzienne zuzycie rund")
        usage_header.setStyleSheet("color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        usage_layout.addWidget(usage_header)

        self._usage_text = QLabel()
        self._usage_text.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0e0e0;")
        usage_layout.addWidget(self._usage_text)

        self._usage_bar = QProgressBar()
        self._usage_bar.setMinimum(0)
        self._usage_bar.setMaximum(100)
        self._usage_bar.setTextVisible(False)
        self._usage_bar.setFixedHeight(12)
        self._usage_bar.setStyleSheet(
            "QProgressBar { background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; }"
            "QProgressBar::chunk { background-color: #1b998b; border-radius: 5px; }"
        )
        usage_layout.addWidget(self._usage_bar)

        self._usage_hint = QLabel()
        self._usage_hint.setStyleSheet("color: #666; font-size: 11px;")
        usage_layout.addWidget(self._usage_hint)

        layout.addWidget(self._usage_card)

        # === POROWNANIE PLANOW ===
        plans_header = QLabel("Dostepne plany")
        plans_header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #53a8b6; margin-top: 4px;"
        )
        layout.addWidget(plans_header)

        self._plans_row = QHBoxLayout()
        self._plans_row.setSpacing(12)
        layout.addLayout(self._plans_row)

        # === HISTORIA PLATNOSCI ===
        payments_header = QLabel("Historia platnosci")
        payments_header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #53a8b6; margin-top: 4px;"
        )
        layout.addWidget(payments_header)

        self._payments_table = QTableWidget()
        self._payments_table.setColumnCount(4)
        self._payments_table.setHorizontalHeaderLabels(["Data", "Kwota", "Plan", "Status"])
        self._payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._payments_table.setMinimumHeight(120)
        self._payments_table.setMaximumHeight(200)
        self._payments_table.verticalHeader().setVisible(False)
        layout.addWidget(self._payments_table)

        self._no_payments_label = QLabel("Brak historii platnosci")
        self._no_payments_label.setStyleSheet("color: #555; font-style: italic; padding: 16px;")
        self._no_payments_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._no_payments_label)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Zaladuj dane
        self._update_plan_display()
        self._load_usage()
        self._load_plans()
        self._load_payments()

    def _update_plan_display(self):
        """Aktualizuje wyswietlanie aktualnego planu."""
        sub = self._subscription
        if not sub or not sub.get("has_active"):
            self._plan_name_label.setText("Brak aktywnej subskrypcji")
            self._plan_name_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e63946;")
            self._plan_badge.setText("NIEAKTYWNY")
            self._plan_badge.setStyleSheet(
                "background-color: #e63946; color: white; font-size: 10px; font-weight: bold; "
                "padding: 2px 10px; border-radius: 10px;"
            )
            self._plan_status_label.setText("Skontaktuj sie z administratorem")
            self._plan_features_label.setText("")
            return

        plan_name = sub.get("plan_name", "Nieznany")
        expires = sub.get("expires_at")

        self._plan_name_label.setText(plan_name)
        self._plan_name_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1b998b;")

        self._plan_badge.setText("AKTYWNY")
        self._plan_badge.setStyleSheet(
            "background-color: #1b998b; color: white; font-size: 10px; font-weight: bold; "
            "padding: 2px 10px; border-radius: 10px;"
        )

        if expires:
            self._plan_status_label.setText(f"Aktywna do: {expires[:10]}")
        else:
            self._plan_status_label.setText("Aktywna — bez daty wygasniecia")

        features = sub.get("features") or {}
        features_lines = []
        if "max_rounds_per_day" in features:
            val = features["max_rounds_per_day"]
            features_lines.append(f"Rundy dziennie: {'bez limitu' if val == -1 else val}")
        if "max_sessions" in features:
            val = features["max_sessions"]
            features_lines.append(f"Sesje: {'bez limitu' if val == -1 else val}")
        if features.get("priority_support"):
            features_lines.append("Priorytetowe wsparcie")
        if features.get("full_access"):
            features_lines.append("Pelny dostep (Admin)")

        self._plan_features_label.setText("\n".join(features_lines) if features_lines else "")

    def _load_usage(self):
        """Pobiera i wyswietla dzienne zuzycie rund."""
        result = get_daily_usage(self._user_id)
        rounds_used = result.get("rounds_used", 0) if result.get("ok") else 0
        max_rounds = result.get("max_rounds", 0) if result.get("ok") else 0

        if max_rounds == -1:
            # Bez limitu
            self._usage_text.setText(f"{rounds_used} rund dzisiaj")
            self._usage_bar.setMaximum(1)
            self._usage_bar.setValue(0)
            self._usage_bar.setVisible(False)
            self._usage_hint.setText("Twoj plan nie ma limitu dziennych rund")
        elif max_rounds > 0:
            remaining = max(0, max_rounds - rounds_used)
            self._usage_text.setText(f"{rounds_used} / {max_rounds}")
            self._usage_bar.setMaximum(max_rounds)
            self._usage_bar.setValue(rounds_used)
            self._usage_bar.setVisible(True)

            # Kolor progress bara w zaleznosci od zuzycia
            pct = rounds_used / max_rounds if max_rounds > 0 else 0
            if pct >= 0.9:
                bar_color = "#e63946"
            elif pct >= 0.7:
                bar_color = "#f4a261"
            else:
                bar_color = "#1b998b"
            self._usage_bar.setStyleSheet(
                f"QProgressBar {{ background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; }}"
                f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 5px; }}"
            )
            self._usage_hint.setText(f"Pozostalo {remaining} rund na dzisiaj")
        else:
            self._usage_text.setText("—")
            self._usage_bar.setVisible(False)
            self._usage_hint.setText("Nie mozna pobrac danych o zuzyciu")

    def _load_plans(self):
        """Pobiera i wyswietla dostepne plany."""
        result = get_plans()
        plans = result.get("plans", [])

        # Wyczysc stare karty
        while self._plans_row.count():
            item = self._plans_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for plan in plans:
            card = self._create_plan_card(plan)
            self._plans_row.addWidget(card)

        if not plans:
            no_plans = QLabel("Nie udalo sie pobrac planow")
            no_plans.setStyleSheet("color: #555;")
            self._plans_row.addWidget(no_plans)

    def _create_plan_card(self, plan: dict) -> QFrame:
        """Tworzy karte planu."""
        is_current = (self._subscription or {}).get("plan_name") == plan["name"]

        card = QFrame()
        card.setObjectName("subscriptionCard")
        if is_current:
            card.setStyleSheet(
                "QFrame#subscriptionCard { background-color: #16213e; border: 2px solid #1b998b; "
                "border-radius: 10px; padding: 16px; }"
            )
        else:
            card.setStyleSheet(
                "QFrame#subscriptionCard { background-color: #16213e; border: 1px solid #0f3460; "
                "border-radius: 10px; padding: 16px; }"
            )

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        # Badge "Aktualny" jesli to biezacy plan
        if is_current:
            badge = QLabel("AKTUALNY")
            badge.setStyleSheet(
                "background-color: #1b998b; color: white; font-size: 9px; font-weight: bold; "
                "padding: 2px 8px; border-radius: 8px; max-width: 70px;"
            )
            badge.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(badge)

        name = QLabel(plan["name"])
        name.setStyleSheet("color: #e0e0e0; font-size: 18px; font-weight: bold;")
        card_layout.addWidget(name)

        price = plan.get("price", "0.00")
        currency = plan.get("currency", "PLN")
        period = plan.get("billing_period", "monthly")

        if float(price) == 0:
            price_text = "Za darmo"
            price_style = "color: #1b998b; font-size: 20px; font-weight: bold;"
        else:
            price_text = f"{price} {currency}/mies."
            price_style = "color: #f4a261; font-size: 20px; font-weight: bold;"

        price_label = QLabel(price_text)
        price_label.setStyleSheet(price_style)
        card_layout.addWidget(price_label)

        desc = plan.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #0f3460; max-height: 1px;")
        card_layout.addWidget(sep)

        features = plan.get("features") or {}
        for key, val in features.items():
            if key == "max_rounds_per_day":
                txt = f"Rundy/dzien: {'bez limitu' if val == -1 else val}"
            elif key == "max_sessions":
                txt = f"Sesje: {'bez limitu' if val == -1 else val}"
            elif key == "priority_support" and val:
                txt = "Priorytetowe wsparcie"
            else:
                continue
            feat_label = QLabel(f"  {txt}")
            feat_label.setStyleSheet("color: #aaa; font-size: 11px;")
            card_layout.addWidget(feat_label)

        # Przycisk
        if is_current:
            btn = QPushButton("Aktualny plan")
            btn.setEnabled(False)
            btn.setStyleSheet(
                "QPushButton { background-color: #1b998b; color: white; font-size: 11px; "
                "padding: 6px 16px; border-radius: 6px; border: none; }"
                "QPushButton:disabled { background-color: #16413e; color: #1b998b; }"
            )
        elif float(price) > 0:
            btn = QPushButton("Kup Premium")
            btn.setEnabled(False)
            btn.setToolTip("Wkrotce dostepne")
            btn.setStyleSheet(
                "QPushButton { background-color: #f4a261; color: #1a1a2e; font-size: 11px; "
                "font-weight: bold; padding: 6px 16px; border-radius: 6px; border: none; }"
                "QPushButton:disabled { background-color: #3a2a1e; color: #665533; }"
            )
        else:
            btn = None

        if btn:
            card_layout.addWidget(btn)

        card_layout.addStretch()
        return card

    def _load_payments(self):
        """Pobiera i wyswietla historie platnosci."""
        result = get_payments(self._user_id)
        payments = result.get("payments", [])

        if not payments:
            self._payments_table.setVisible(False)
            self._no_payments_label.setVisible(True)
            return

        self._payments_table.setVisible(True)
        self._no_payments_label.setVisible(False)
        self._payments_table.setRowCount(len(payments))

        for i, p in enumerate(payments):
            date = (p.get("paid_at") or p.get("created_at", ""))[:10]
            amount = f"{p.get('amount', '0')} {p.get('currency', 'PLN')}"
            plan = p.get("plan_name") or "-"
            status = p.get("status", "-")

            self._payments_table.setItem(i, 0, QTableWidgetItem(date))
            self._payments_table.setItem(i, 1, QTableWidgetItem(amount))
            self._payments_table.setItem(i, 2, QTableWidgetItem(plan))
            self._payments_table.setItem(i, 3, QTableWidgetItem(status))

    def _refresh_data(self):
        """Odswieza dane subskrypcji z API."""
        result = get_subscription(self._user_id)
        if result.get("ok"):
            self._subscription = result.get("subscription") or {}
        self._update_plan_display()
        self._load_usage()
        self._load_plans()
        self._load_payments()

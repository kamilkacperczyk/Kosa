"""
Zakladka Subskrypcja — wyswietla aktualny plan, porownanie planow i historie platnosci.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
)
from PySide6.QtCore import Qt

from gui.db import get_subscription, get_payments, get_plans


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
        layout.setSpacing(16)
        layout.setContentsMargins(8, 8, 8, 8)

        # === AKTUALNY PLAN ===
        self._plan_card = QFrame()
        self._plan_card.setObjectName("subscriptionCard")
        card_layout = QVBoxLayout(self._plan_card)
        card_layout.setSpacing(8)

        card_header = QHBoxLayout()
        card_header.addWidget(QLabel("Twoj aktualny plan:"))
        card_header.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        refresh_btn = QPushButton("Odswiez")
        refresh_btn.setStyleSheet("font-size: 11px; padding: 4px 12px;")
        refresh_btn.clicked.connect(self._refresh_data)
        card_header.addWidget(refresh_btn)

        card_layout.addLayout(card_header)

        self._plan_name_label = QLabel()
        self._plan_name_label.setObjectName("planNameLabel")
        card_layout.addWidget(self._plan_name_label)

        self._plan_status_label = QLabel()
        self._plan_status_label.setStyleSheet("color: #888; font-size: 13px;")
        card_layout.addWidget(self._plan_status_label)

        self._plan_features_label = QLabel()
        self._plan_features_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self._plan_features_label.setWordWrap(True)
        card_layout.addWidget(self._plan_features_label)

        layout.addWidget(self._plan_card)

        # === POROWNANIE PLANOW ===
        plans_header = QLabel("Dostepne plany")
        plans_header.setStyleSheet("color: #53a8b6; font-size: 15px; font-weight: bold;")
        layout.addWidget(plans_header)

        self._plans_row = QHBoxLayout()
        self._plans_row.setSpacing(12)
        layout.addLayout(self._plans_row)

        # === HISTORIA PLATNOSCI ===
        payments_header = QLabel("Historia platnosci")
        payments_header.setStyleSheet("color: #53a8b6; font-size: 15px; font-weight: bold;")
        layout.addWidget(payments_header)

        self._payments_table = QTableWidget()
        self._payments_table.setColumnCount(4)
        self._payments_table.setHorizontalHeaderLabels(["Data", "Kwota", "Plan", "Status"])
        self._payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._payments_table.setMinimumHeight(120)
        self._payments_table.setMaximumHeight(200)
        layout.addWidget(self._payments_table)

        self._no_payments_label = QLabel("Brak historii platnosci")
        self._no_payments_label.setStyleSheet("color: #555; font-style: italic;")
        self._no_payments_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._no_payments_label)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Zaladuj dane
        self._update_plan_display()
        self._load_plans()
        self._load_payments()

    def _update_plan_display(self):
        """Aktualizuje wyswietlanie aktualnego planu."""
        sub = self._subscription
        if not sub or not sub.get("has_active"):
            self._plan_name_label.setText("Brak aktywnej subskrypcji")
            self._plan_name_label.setObjectName("planExpiredLabel")
            self._plan_name_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e63946;")
            self._plan_status_label.setText("Zarejestruj sie ponownie lub skontaktuj sie z administratorem")
            self._plan_features_label.setText("")
            return

        plan_name = sub.get("plan_name", "Nieznany")
        expires = sub.get("expires_at")

        self._plan_name_label.setText(plan_name)
        self._plan_name_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1b998b;")

        if expires:
            self._plan_status_label.setText(f"Aktywna do: {expires[:10]}")
        else:
            self._plan_status_label.setText("Aktywna - nigdy nie wygasa")

        features = sub.get("features") or {}
        features_text = []
        if "max_rounds_per_day" in features:
            val = features["max_rounds_per_day"]
            features_text.append(f"Rundy dziennie: {'bez limitu' if val == -1 else val}")
        if "max_sessions" in features:
            val = features["max_sessions"]
            features_text.append(f"Sesje: {'bez limitu' if val == -1 else val}")
        if features.get("priority_support"):
            features_text.append("Priorytetowe wsparcie")
        if features.get("full_access"):
            features_text.append("Pelny dostep (Admin)")

        self._plan_features_label.setText("  |  ".join(features_text) if features_text else "")

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
        card = QFrame()
        card.setObjectName("subscriptionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        name = QLabel(plan["name"])
        name.setStyleSheet("color: #53a8b6; font-size: 16px; font-weight: bold;")
        card_layout.addWidget(name)

        price = plan.get("price", "0.00")
        currency = plan.get("currency", "PLN")
        period = plan.get("billing_period", "monthly")
        price_label = QLabel(f"{price} {currency} / {'mies.' if period == 'monthly' else period}")
        price_label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
        card_layout.addWidget(price_label)

        desc = plan.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

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

        # Przycisk upgrade (na razie nieaktywny)
        is_current = (self._subscription or {}).get("plan_name") == plan["name"]
        if is_current:
            btn = QPushButton("Aktualny plan")
            btn.setEnabled(False)
            btn.setStyleSheet("font-size: 11px; padding: 4px 12px;")
        elif float(price) > 0:
            btn = QPushButton("Kup Premium")
            btn.setEnabled(False)
            btn.setToolTip("Wkrotce dostepne")
            btn.setStyleSheet("font-size: 11px; padding: 4px 12px;")
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
        self._load_plans()
        self._load_payments()

"""Tests de l'attente de la base : essais bornés, pauses, erreur explicite.

Aucun serveur n'est nécessaire : un faux moteur échoue le nombre de fois voulu,
puis répond grâce à SQLite en mémoire, et les pauses sont relevées au lieu
d'être attendues.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import ArgumentError, OperationalError

from src.bdd.attente import AttenteBase, BaseInjoignable


class MoteurIntermittent:
    """Moteur qui échoue un nombre donné de fois, comme une base qui démarre."""

    def __init__(self, echecs):
        self.echecs = echecs
        self.essais = 0
        self.sqlite = create_engine("sqlite://")
        self.url = self.sqlite.url

    def connect(self):
        self.essais += 1
        if self.essais <= self.echecs:
            raise OperationalError("SELECT 1", {}, Exception("base en démarrage"))
        return self.sqlite.connect()


class MoteurMalConfigure(MoteurIntermittent):
    """Moteur dont l'erreur ne vient pas de la base : la retenter est inutile."""

    def connect(self):
        self.essais += 1
        raise ArgumentError("adresse mal formée")


@pytest.fixture
def pauses(monkeypatch):
    """Remplace time.sleep : chaque pause est relevée au lieu d'être attendue."""
    relevees = []
    monkeypatch.setattr("src.bdd.attente.time.sleep", relevees.append)
    return relevees


def test_base_joignable_au_premier_essai_sans_aucune_pause(pauses):
    moteur = MoteurIntermittent(echecs=0)

    AttenteBase(moteur, tentatives=3, pause=2.0).attendre()

    assert moteur.essais == 1
    assert pauses == []


def test_base_joignable_apres_deux_echecs_une_pause_par_echec(pauses, caplog):
    # Le succès est journalisé en INFO, sous le niveau WARNING retenu par défaut.
    caplog.set_level("INFO")
    moteur = MoteurIntermittent(echecs=2)

    AttenteBase(moteur, tentatives=5, pause=2.0).attendre()

    assert moteur.essais == 3
    assert pauses == [2.0, 2.0]
    assert "essai 2 sur 5" in caplog.text
    assert "joignable, essai 3 sur 5" in caplog.text


def test_base_injoignable_erreur_au_dernier_essai_sans_pause_finale(pauses):
    moteur = MoteurIntermittent(echecs=10)

    with pytest.raises(BaseInjoignable, match="après 3 essais"):
        AttenteBase(moteur, tentatives=3, pause=2.0).attendre()

    assert moteur.essais == 3
    assert pauses == [2.0, 2.0]


def test_erreur_hors_connexion_remontee_sans_nouvel_essai(pauses):
    moteur = MoteurMalConfigure(echecs=0)

    with pytest.raises(ArgumentError):
        AttenteBase(moteur, tentatives=3, pause=2.0).attendre()

    assert moteur.essais == 1
    assert pauses == []


def test_mot_de_passe_masque_dans_l_adresse_du_journal():
    moteur = create_engine("postgresql+psycopg://api:secret@127.0.0.1:5433/p5")

    adresse = AttenteBase(moteur, tentatives=1, pause=0).adresse

    assert "secret" not in adresse
    assert adresse == "postgresql+psycopg://api:***@127.0.0.1:5433/p5"

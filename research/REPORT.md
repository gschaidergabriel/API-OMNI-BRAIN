# Teamlauf

{'design': 24, 'design_ok': 19, 'code': 11, 'code_ok': 1}
End-Score (Onboarding-Kriterien, 6 Reiter): 6.5
Offene Kritik:
- [Overview] Produktidentität unklar: Header zeigt API-OMNI-BRAIN, Sub-Headline OMNIPOOL. Ein Erstnutzer versteht in 5 Sekunden nicht, was das Produkt ist.
- [Overview] Mehrdeutiger primärer CTA: Der Button Scan and probe now oben rechts konkurriert mit den drei Schritt-Karten Scan Connect Watch. Die Hierarchie ist unklar, was als Naechstes zu tun ist.
- [Overview] Zu geringer Kontrast bei Sekundärtext: Hinweise wie Runs on this machine oder Metriken wie 1 ok sind zu hellgrau auf fast-schwarz und schlecht lesbar.
- [Overview] Informationsueberladung auf dem Overview: Hero, drei Schritt-Karten und vier Metrik-Karten gleichzeitig. Laien werden visuell erschlagen.
- [Keys & Providers] Der Hilfetext unter 'Add token' ('Key file: ... mode 600') hat zu geringen Kontrast und enthält technischen Jargon, der Laien abschreckt; Kontrast erhöhen und Text vereinfachen oder als optionalen Details-Link auslagern.
- [Keys & Providers] Es fehlt eine einzeilige Value-Proposition oder Kontexteinführung unter dem Header; ein Erstnutzer versteht in 5 Sekunden nicht, welchen Zweck die Seite insgesamt verfolgt.
- [Keys & Providers] In der Sektion 'New or third-party provider' ist nicht visuell erkennbar, welche Felder Pflicht (URL) und welche optional (Name) sind; Pflichtfelder klar kennzeichnen (z. B. mit Sternchen).
- [Keys & Providers] Die Helper-Texte und Sektionstitel nutzen unterschiedliche Graustufen ohne klare Hierarchie; Textstile und Kontraste konsolidieren für bessere Lesbarkeit und Hochwertigkeit.
- [Models] Der Titel 'API-OMNI-BRAIN' vermittelt keinen sofortigen Nutzen; ein erklärender Untertitel fehlt für die 5-Sekunden-Erfassung.
- [Models] Die Tabelle enthält zu viele Spalten mit technischen Headern (z. B. 'REASONING (SUCCESS PROBABILITY)'); das überfordert Laien und führt zu abgeschnittenen Inhalten ('LONG TE...').
- [Models] Status-Badges mischen inkonsistent Deutsch ('fehler', 'neu') und Englisch/Technik ('keine_Klasse', 'Available'); das wirkt unprofessionell und verwirrend.
- [Models] Zeilen mit nur '-' oder '0.00 / 1' füllen den Bildschirm ohne handlungsrelevante Information und mindern die wahrgenommene Qualität.
- [Connect] Zu viele Informationen auf einmal: Sechs vollständige Karten mit Code-Blöcken und Anleitungen überfordern Erstnutzer und verletzen das Prinzip 'wenige Elemente pro Blick'. Lösung: Karten standardmäßig einklappbar machen oder nur die Top-3-Integrationen anzeigen.
- [Connect] Redundante Anleitungen für Profis: Der Block 'Step by step' ist für alle Nutzer sichtbar und nimmt Platz weg, den Experten für schnelle Aktionen brauchen. Lösung: Anleitungen hinter einem 'i'-Icon oder Tooltip verbergen, sodass nur Titel, Buttons und Code-Block sofort sichtbar sind.
- [Connect] Unklare visuelle Hierarchie: Die Konfigurations-Buttons ('Copy', 'Show keys') stehen zwischen Text und Code-Block, was den Lesefluss unterbricht. Lösung: Buttons direkt über dem zugehörigen Code-Block gruppieren und visuell stärker als primäre Aktion hervorheben.
- [Connect] Geringer Kontrast bei Sekundärtext: Die Einleitung unter dem Logo und kleine Hilfetexte sind zu hellgrau auf dunklem Hintergrund und schwer lesbar. Lösung: Kontrast der Grautöne erhöhen, um Barrierefreiheit und Hochwertigkeit zu verbessern.
- [Settings] Inkonsistente Kartenstruktur: 'Security' und 'Advanced settings' enthalten nur Text, während 'Planner' Eingabefelder hat – das erschwert das Verständnis von Interaktivität.
- [Settings] Zu geringer Kontrast beim Beschreibungstext in den rechten Karten (hellgrau auf dunkelgrau), was die Lesbarkeit beeinträchtigt.
- [Settings] Unklare Hauptaktion: Der 'Save'-Button ist unten in der ersten Spalte versteckt, während globale Aktionen oben rechts stehen – die Hierarchie ist unklar.
- [Settings] Fehlende visuelle Gruppierung in der 'Planner'-Karte: Viele Eingabefelder sind ohne Abstände oder Sektionen gestapelt, was Erstnutzer überfordern kann.
- [Events] Ersetze rohe JSON-Logs und technische Strings (z. B. "demoai DEMOAI_KEY1") durch eine menschenlesbare Zusammenfassung oder füge einen Toggle für eine Expertenansicht hinzu, um Laien nicht zu überfordern.
- [Events] Klarheit bei Zeitstempeln: "2 h" ist mehrdeutig (vor 2 Stunden? Dauer?); verwende relatives Datum (z. B. "vor 2 Std.") oder absolutes Datum.
- [Events] Inkonsistente Severity-Signalisierung: Gelbe Warnsymbole erscheinen auch bei Meldungen mit "status ok"; Icons müssen dem tatsächlichen Dringlichkeitsgrad entsprechen.
- [Events] Fehlender Kontext: Der Bildschirm erklärt nicht, was "API-OMNI-BRAIN" ist oder welches Ziel der Nutzer mit den Events verfolgen soll; füge eine kurze Unterzeile oder Beschreibung hinzu.

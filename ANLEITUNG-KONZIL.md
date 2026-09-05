# Das Konzil — Anleitung ohne Technik

Für Entscheidungen, die teuer zurückzunehmen sind. Nicht für alles andere.

---

## Was das Ding ist

Stell dir vor, du legst eine Frage nicht einem Berater vor, sondern vier — jedem
einzeln, in einem eigenen Raum. Keiner weiß, was die anderen antworten.

Dann sammelst du die vier Antworten ein, **streichst die Namen weg** und gibst
jedem Berater den anonymen Stapel zurück: „Bewerte diese Antworten und bring sie
in eine Reihenfolge." Weil niemand weiß, wer was geschrieben hat, kann auch
niemand aus Höflichkeit oder Eitelkeit urteilen.

Zum Schluss liest ein fünfter alles — die Antworten und die Bewertungen — und
schreibt eine Zusammenfassung: eine klare Empfehlung, **und ausdrücklich die
Stellen, an denen die vier sich uneinig waren.**

### Der Dissens ist das Produkt

Das ist der Unterschied zu „einmal ChatGPT fragen". Ein einzelnes Modell gibt dir
eine plausible Antwort, und du weißt nicht, ob es die einzige plausible war. Vier
Modelle zeigen dir die Streuung. Wenn drei sagen „Preis erhöhen" und eines sagt
„das killt deinen Funnel", dann ist genau dieser eine Einwand die Information,
für die du bezahlt hast. Die Zusammenfassung ist nur die Verpackung.

Sind sich alle vier einig, heißt das zweierlei: entweder die Frage war leicht —
oder alle vier haben denselben blinden Fleck, weil sie mit ähnlichen Texten
trainiert wurden. **Einigkeit ist kein Beweis.**

### Was es kostet

| Modus | Modelle | Dauer | Kosten | Wofür |
|---|---|---|---|---|
| `quick` | 2 | ~30 Sek. | wenige Cent | schnelle Zweitmeinung |
| `decision` | 4 | 1–3 Min. | grob 0,30–1,00 € | echte Entscheidungen |
| `research` | 4 | 1–3 Min. | grob 0,30–1,00 € | offene Fragen, Abdeckung |

Die Spanne ist geschätzt. Der genaue Betrag steht nach jedem Lauf unter der
Antwort, zusammen mit Dauer und Token-Verbrauch.

---

## Die Eintrittskarte

Alle drei Prüfungen müssen bestanden sein. Fällt eine durch, beantworte die Frage
selbst oder frag ein einzelnes Modell.

### 1. Ist die Entscheidung teuer zurückzunehmen?

Kostet ein Fehler Tage, Geld oder Kundenvertrauen — oder zehn Minuten Nacharbeit?

- **Ja:** Preisstruktur öffentlich ändern. Ein Partnermodell zusagen. Ein
  Datenmodell festlegen.
- **Nein:** Eine Betreffzeile. Ein Post. Eine Formulierung auf der Landingpage.

### 2. Gibt es keinen billigen Faktencheck?

Kann ein Test, eine Zahl aus dem Sheet, ein Blick in den Code oder **ein Anruf
bei einem Kunden** die Frage in fünf Minuten klären? Dann ist das die bessere
Antwort — immer.

- **Ja:** „Welche Lizenzgebühr ist angemessen?" — dazu gibt es nichts zum
  Nachschlagen.
- **Nein:** „Warum bricht die Zahlung ab?" — steht im Log. „Kaufen Kanzleien
  das?" — ein Telefonat weiß es besser als vier Modelle.

### 3. Ist die Frage offen genug für echte Vielfalt?

Würden vier Berater hier tatsächlich verschiedene Wege einschlagen?

- **Ja:** „Wie positioniere ich das günstige Einzelprodukt neben dem Team-Paket,
  ohne zu kannibalisieren?"
- **Nein:** „Wie formuliere ich eine DSGVO-Hinweiszeile?" — da ist Vielfalt nur
  Rauschen.

---

## Die Nein-Liste

Dafür niemals das Konzil:

- **Alles, was ein Test klärt.** Ein Modell plus Logdatei ist schneller und
  richtiger.
- **Alles, was ein Kunde besser beantwortet.** Vier Modelle raten, ein Anruf
  weiß es. Das Konzil ist kein Marktforschungsersatz.
- **Texte und Formulierungen.** Billig zu ändern, also durchgefallen bei
  Prüfung 1.
- **Rechtsfragen.** Vier zuversichtliche Modelle sind hier gefährlicher als
  eines, weil Einigkeit wie Sicherheit aussieht.
- **Fragen, bei denen du die Antwort schon willst.** Du bekommst sie — und
  zahlst dafür.

---

## Bedienung

### Im Chat mit Claude Code — der Normalfall

```
/council Welche Lizenzgebühr ist für das White-Label-Modell angemessen?
```

Claude sucht die passenden Dateien selbst heraus, formuliert die Frage sauber und
fragt nach, wenn sie die Eintrittskarte nicht besteht.

### Im Terminal — wenn du weißt, was du willst

```bash
council ask "Solo-Produkt neben Team-Paket — Kannibalisierung?" \
  --file MARKETING-VERTRIEBSPLAN.md --adr

council profiles     # welche Modi gibt es
council log          # was habe ich schon gefragt
```

`--file` hängt ein Dokument an, `--diff` eine Code-Änderung, `--adr` legt das
Ergebnis als Entscheidungsprotokoll im aktuellen Projekt ab.

### Die Weboberfläche — zum Stöbern

Zeigt alle Einzelantworten und alle Bewertungen im Rohtext, in Reitern. Nimm sie,
wenn du *sehen* willst, wie unterschiedlich die vier gedacht haben. Für die
ersten Läufe der beste Weg zum Verständnis.

> **Wichtig:** Das Konzil sieht ausschließlich, was du ihm mitgibst. Kein
> Repo-Zugriff, kein Gedächtnis an frühere Läufe, keine Kenntnis deiner Zahlen.

---

## Wie eine Frage aussieht, die etwas bringt

Der Unterschied zwischen einem nützlichen und einem wertlosen Lauf liegt fast
vollständig in der Frage. Vier Modelle können eine schlechte Frage nicht
reparieren — sie geben dir vier gleich vage Antworten.

### Vorlage zum Kopieren

```
LAGE
<Wer du bist, was das Produkt ist, wer kauft.>

DIE ENTSCHEIDUNG
Option A: <…>
Option B: <…>
Option C: <…>
<Nenne die Optionen selbst. Sonst erfinden die Modelle welche, die an
deiner Lage vorbeigehen.>

SCHON AUSGESCHLOSSEN
<Was raus ist und warum. Ohne das schlagen dir alle vier genau das vor.>

ZAHLEN UND GRENZEN
<Preise, Mengen, Kapazität, Zeitfenster. Grobe Werte sind besser als keine.>

WAS "GUT" HIER HEISST
<Umsatz in sechs Monaten? Weniger Betreuungsaufwand? Planbarkeit?
Ohne Kriterium optimiert jedes Modell etwas anderes.>

FRAGE
Welche Option empfiehlst du — und was müsste wahr sein, damit die
Empfehlung kippt?
```

Der letzte Halbsatz ist der wertvollste. „Was müsste wahr sein, damit das kippt?"
zwingt zu Bedingungen statt zu Meinungen — und liefert gleich die
Frühindikatoren, auf die du achten musst.

---

## Das Ritual

Mit `--adr` landet ein Ergebnis als nummeriertes Dokument unter
`docs/decisions/` im jeweiligen Projekt — mit Datum, Frage, Empfehlung, Dissens
und Kosten.

Der Nutzen zeigt sich nicht beim ersten Lauf, sondern ein halbes Jahr später,
wenn jemand fragt, warum etwas so entschieden wurde. Dann liegt die Begründung
da, inklusive der Gegenargumente, die du damals verworfen hast.

**Drei Regeln, damit es nicht ausufert:**

1. **Protokoll nur für echte Weichenstellungen.** Faustregel: Wenn du es in einem
   halben Jahr nachschlagen würdest, schreib es weg.
2. **Trag deine Entscheidung nach.** Das Konzil empfiehlt, du entscheidest.
   Ergänze eine Zeile: was du gemacht hast und warum — gerade wenn du abweichst.
3. **Schau nach vier Wochen zurück.** `council log` zeigt alle Läufe. Wenn keiner
   etwas verändert hat, war es ein teures Hobby.

---

## Was du dem Ergebnis nicht glauben darfst

**Die Rangliste ist keine Wahrheitsmessung.** Sie sagt dir, welche Antwort die
anderen Modelle am *überzeugendsten geschrieben* fanden. Das korreliert mit
Gründlichkeit und Stil, nicht zuverlässig mit Richtigkeit. Ein selbstsicher
formulierter Irrtum gewinnt gegen eine vorsichtige, korrekte Antwort.

**Zwei bekannte Schieflagen sind noch drin.** Die Modelle bewerten derzeit auch
ihre eigene Antwort mit, und der Zusammenfasser sieht am Ende, welches Modell was
geschrieben hat. Beides zieht das Ergebnis leicht zu dem, der am
selbstbewusstesten auftritt. Beides ist als offener Punkt in `CLAUDE.md`
notiert. Solange gilt: Bei knappen Rangfolgen die Reihenfolge ignorieren und die
Einzelargumente lesen.

**Kein Gedächtnis, keine Quellen, keine Zahlen.** Jeder Lauf startet bei null.
Die Modelle recherchieren nichts und prüfen keine Fakten. Jede konkrete Zahl in
einer Antwort ist geraten, bis du sie nachgeprüft hast.

---

## Die ersten dreißig Tage

| Wann | Was | Warum |
|---|---|---|
| Tag 1 | Ein Lauf im `quick`-Modus, egal welche Frage | Nicht die Antwort zählt, sondern dass es läuft und was es kostet |
| Tag 2 | Die wichtigste offene Frage im `decision`-Modus, mit dem passenden Dokument als Anhang und `--adr` | Der ehrlichste erste Test |
| Woche 1 | Eine Frage bewusst als Gegenprobe zu einer bereits getroffenen Entscheidung | Misst, ob das Konzil widerspricht oder nur nickt |
| Woche 2–4 | Nur noch fragen, wenn alle drei Prüfungen bestanden sind. Höchstens ein Lauf pro Woche | Die Begrenzung zwingt dich, die Fragen aufzuheben, die es verdienen |
| Tag 30 | `council log` durchgehen, pro Lauf eine Zeile: Hat er eine Entscheidung verändert? | Null von fünf heißt abschalten. Eins von fünf heißt weitermachen — eine verhinderte Fehlentscheidung zahlt hundert Läufe |

---

## Anhang: eine fertig formulierte Frage

Ein vollständiges Beispiel nach der Vorlage oben. So sieht eine Frage aus, die
die Modelle nicht in Allgemeinplätze ausweichen lässt.

```
LAGE
Ich verkaufe KI-Weiterbildung an kleine und mittlere Unternehmen im
deutschen Mittelstand. Einstieg ist ein kostenloser Selbsttest, daraus
werden kostenpflichtige Checks und Team-Pakete für einen Kurs.
Ich bin Einzelunternehmer, jede Betreuungsstunde geht von meiner Zeit ab.

DIE ENTSCHEIDUNG
Beratungen, Kammern und Wirtschaftsförderungen sollen die
Assessment-Plattform unter eigener Marke betreiben können (White Label).
Der Kurs bleibt bei mir, lizenziert wird nur die Plattform.
Offen ist Höhe UND Modell der Lizenzgebühr:

Option A: Jahreslizenz, fester Betrag, unbegrenzte Assessments.
Option B: Grundgebühr plus Preis je durchgeführtem Assessment.
Option C: Reine Nutzungsabrechnung, Staffelpreis je Assessment.
Option D: Einmalige Einrichtungsgebühr plus kleine Jahresgebühr.

SCHON AUSGESCHLOSSEN
- Provisionsmodelle für Empfehlungen. Begründung: ein Produkt, ein
  öffentlicher Preis, keine Preiskonflikte.
- Der Lizenznehmer verkauft nicht meinen Kurs, sondern seine eigene
  Beratung mit meinem Werkzeug.

ZAHLEN UND GRENZEN
- Endkundenpreise: kostenpflichtiger Check 147 €, Solo-Kurs 49 €,
  Team-Pakete in drei Größen.
- Kapazität: Einzelunternehmer. Mehr als eine Handvoll Lizenznehmer
  kann ich nicht persönlich betreuen.
- Das Angebot ist noch nicht lieferbar, es gibt keine Referenzkunden
  und keine Erfahrungswerte.

WAS "GUT" HIER HEISST
Planbarer Umsatz, der ohne meine Zeit läuft, ohne dass die Lizenz mein
Direktgeschäft mit denselben Zielkunden untergräbt. Zweitrangig:
möglichst wenig Abrechnungs- und Supportaufwand.

FRAGE
Welches Modell und welche Größenordnung empfiehlst du für den Start,
und was müsste wahr sein, damit die Empfehlung kippt?
Nenne außerdem die zwei Fehler, die man bei der ersten White-Label-
Lizenz am häufigsten macht.
```

Aufruf dazu:

```bash
council ask "$(cat frage-white-label.txt)" --profile decision --adr
```

Oder im Chat: `/council` plus der Text — dort hängt Claude die relevanten
Projektunterlagen von selbst an.
